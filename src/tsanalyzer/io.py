"""Loading time series from CSV files."""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd


class DataFormatError(ValueError):
    """Raised when an input file does not have the expected structure."""


def load_csv(
    path: str | Path,
    time_col: str = "date",
    value_col: str = "value",
    sep: str = ",",
) -> pd.Series:
    """Read a CSV file and return a numeric series indexed by time.

    The result is sorted by time, duplicate timestamps are averaged and
    non-numeric values are converted to ``NaN`` so that they can be handled
    later by :func:`tsanalyzer.cleaning.fill_missing`.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        DataFormatError: if a required column is missing or no timestamp can be parsed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path, sep=sep)
    missing = [c for c in (time_col, value_col) if c not in df.columns]
    if missing:
        raise DataFormatError(f"Missing column(s) {missing}; available columns: {list(df.columns)}")

    with warnings.catch_warnings():
        # mixed or unusual date formats fall back to dateutil; unparseable values become NaT
        warnings.simplefilter("ignore", UserWarning)
        times = pd.to_datetime(df[time_col], errors="coerce")
    if times.isna().all():
        raise DataFormatError(f"Column '{time_col}' contains no valid timestamps")

    values = pd.to_numeric(df[value_col], errors="coerce")
    series = pd.Series(values.to_numpy(), index=times, name=value_col)
    series = series[series.index.notna()]
    series = series.groupby(level=0).mean().sort_index()
    series.index.name = time_col
    return series
