"""Trend estimation: linear regression, moving average and the Mann–Kendall test."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats as sps


@dataclass(frozen=True)
class TrendResult:
    """Result of a linear trend fit.

    ``slope`` is expressed in value units per day for a DatetimeIndex and per
    step otherwise; ``slope_per_year`` is provided for convenience.
    """

    slope: float
    slope_per_year: float
    intercept: float
    r_squared: float
    p_value: float

    @property
    def significant(self) -> bool:
        """True when the slope differs from zero at the 5% level."""
        return self.p_value < 0.05

    def to_dict(self) -> dict[str, float | bool]:
        return {**asdict(self), "significant": self.significant}


def _time_axis(series: pd.Series) -> np.ndarray:
    if isinstance(series.index, pd.DatetimeIndex):
        delta = series.index - series.index[0]
        return delta.total_seconds().to_numpy() / 86_400.0
    return np.arange(len(series), dtype=float)


def linear_trend(series: pd.Series) -> TrendResult:
    """Fit an ordinary least-squares line ``value = slope * t + intercept``."""
    values = series.dropna()
    if len(values) < 3:
        raise ValueError("at least 3 observations are required to fit a trend")
    t = _time_axis(values)
    fit = sps.linregress(t, values.to_numpy(dtype=float))
    return TrendResult(
        slope=float(fit.slope),
        slope_per_year=float(fit.slope * 365.25),
        intercept=float(fit.intercept),
        r_squared=float(fit.rvalue**2),
        p_value=float(fit.pvalue),
    )


def moving_average(series: pd.Series, window: int = 7, center: bool = True) -> pd.Series:
    """Simple moving average; the window shrinks at the edges instead of producing NaN."""
    if window < 1:
        raise ValueError("window must be >= 1")
    return series.rolling(window=window, center=center, min_periods=1).mean()


def mann_kendall(series: pd.Series, alpha: float = 0.05) -> dict[str, float | str]:
    """Non-parametric Mann–Kendall trend test (via Kendall's tau against time).

    Returns ``tau``, ``p_value`` and ``trend`` — one of ``"increasing"``,
    ``"decreasing"`` or ``"no trend"``.
    """
    values = series.dropna()
    if len(values) < 4:
        raise ValueError("at least 4 observations are required for the Mann–Kendall test")
    tau, p_value = sps.kendalltau(np.arange(len(values)), values.to_numpy(dtype=float))
    if np.isnan(tau):
        tau, p_value = 0.0, 1.0
    if p_value < alpha:
        trend = "increasing" if tau > 0 else "decreasing"
    else:
        trend = "no trend"
    return {"tau": float(tau), "p_value": float(p_value), "trend": trend}
