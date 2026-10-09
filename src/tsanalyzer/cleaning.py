"""Data cleaning: gap filling, outlier removal and resampling."""

from __future__ import annotations

import numpy as np
import pandas as pd

_FILL_METHODS = ("linear", "ffill", "bfill", "drop")
_OUTLIER_METHODS = ("iqr", "zscore")


def fill_missing(series: pd.Series, method: str = "linear") -> pd.Series:
    """Fill ``NaN`` values.

    Args:
        series: input series.
        method: ``"linear"`` (time-weighted interpolation), ``"ffill"``, ``"bfill"``
            or ``"drop"`` (remove missing points).
    """
    if method not in _FILL_METHODS:
        raise ValueError(f"Unknown fill method '{method}'. Use one of {_FILL_METHODS}")
    if method == "drop":
        return series.dropna()
    if method == "ffill":
        return series.ffill()
    if method == "bfill":
        return series.bfill()
    if isinstance(series.index, pd.DatetimeIndex):
        return series.interpolate(method="time", limit_direction="both")
    return series.interpolate(method="linear", limit_direction="both")


def remove_outliers(
    series: pd.Series, method: str = "iqr", threshold: float | None = None
) -> tuple[pd.Series, pd.Series]:
    """Detect and remove outliers.

    Args:
        series: input series without ``NaN`` values.
        method: ``"iqr"`` (Tukey fences, default k = 1.5) or ``"zscore"``
            (default |z| > 3).
        threshold: overrides the default k or z threshold.

    Returns:
        A tuple ``(clean, outliers)`` — the series without outliers and the
        removed points.
    """
    if method not in _OUTLIER_METHODS:
        raise ValueError(f"Unknown outlier method '{method}'. Use one of {_OUTLIER_METHODS}")
    values = series.dropna()
    if values.empty:
        return series.copy(), series.iloc[0:0]

    if method == "iqr":
        k = 1.5 if threshold is None else threshold
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        mask = (series < q1 - k * iqr) | (series > q3 + k * iqr)
    else:
        z_max = 3.0 if threshold is None else threshold
        std = values.std(ddof=0)
        if std == 0:
            mask = pd.Series(False, index=series.index)
        else:
            mask = ((series - values.mean()) / std).abs() > z_max

    return series[~mask], series[mask]


def resample(series: pd.Series, rule: str = "D", how: str = "mean") -> pd.Series:
    """Aggregate a time-indexed series to a regular frequency (e.g. ``"D"``, ``"W"``, ``"MS"``)."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("resample() requires a DatetimeIndex")
    if how not in ("mean", "sum", "min", "max", "median"):
        raise ValueError(f"Unsupported aggregation '{how}'")
    return getattr(series.resample(rule), how)()


def deseasonalize(series: pd.Series, period: str = "month") -> pd.Series:
    """Return anomalies: each value minus the long-term mean of its season.

    The climatology is the average over all years for the same calendar
    ``"month"`` or ``"dayofyear"``. Removing it exposes long-term trends that
    a strong seasonal cycle would otherwise hide.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("deseasonalize() requires a DatetimeIndex")
    if period not in ("month", "dayofyear"):
        raise ValueError("period must be 'month' or 'dayofyear'")
    key = getattr(series.index, period)
    climatology = series.groupby(key).transform("mean")
    return (series - climatology).rename(f"{series.name or 'value'}_anomaly")
