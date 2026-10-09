"""Shared test helpers: deterministic synthetic series."""

import numpy as np
import pandas as pd


def make_series(n: int = 365, slope_per_day: float = 0.01, noise: float = 0.5, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    t = np.arange(n, dtype=float)
    values = 10.0 + slope_per_day * t + rng.normal(0, noise, n)
    return pd.Series(values, index=idx, name="value")
