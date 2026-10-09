"""Descriptive statistics for time series."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps


def describe(series: pd.Series) -> dict[str, float]:
    """Return descriptive statistics as a plain dictionary (JSON-serialisable)."""
    values = series.dropna().to_numpy(dtype=float)
    n = int(values.size)
    result: dict[str, float] = {
        "count": n,
        "missing": int(series.isna().sum()),
    }
    if n == 0:
        return result
    result.update(
        {
            "mean": float(np.mean(values)),
            "std": float(np.std(values, ddof=1)) if n > 1 else 0.0,
            "min": float(np.min(values)),
            "q25": float(np.percentile(values, 25)),
            "median": float(np.median(values)),
            "q75": float(np.percentile(values, 75)),
            "max": float(np.max(values)),
        }
    )
    if n > 2 and np.std(values) > 0:
        result["skewness"] = float(sps.skew(values))
        result["kurtosis"] = float(sps.kurtosis(values))
    return result


def autocorrelation(series: pd.Series, lag: int = 1) -> float:
    """Pearson autocorrelation of the series with itself shifted by ``lag`` steps."""
    if lag < 1:
        raise ValueError("lag must be a positive integer")
    values = series.dropna()
    if len(values) <= lag + 1:
        raise ValueError("series is too short for the requested lag")
    return float(values.autocorr(lag=lag))
