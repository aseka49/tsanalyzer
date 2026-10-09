"""tsanalyzer — a small toolkit for exploratory analysis of scientific time series.

Typical workflow::

    from tsanalyzer import load_csv, fill_missing, remove_outliers, describe, linear_trend

    series = load_csv("examples/temperature.csv", time_col="date", value_col="temp_c")
    series = fill_missing(series, method="linear")
    clean, outliers = remove_outliers(series, method="iqr")
    print(describe(clean))
    print(linear_trend(clean))
"""

from tsanalyzer.cleaning import deseasonalize, fill_missing, remove_outliers, resample
from tsanalyzer.io import load_csv
from tsanalyzer.stats import autocorrelation, describe
from tsanalyzer.trend import TrendResult, linear_trend, mann_kendall, moving_average

__all__ = [
    "TrendResult",
    "autocorrelation",
    "deseasonalize",
    "describe",
    "fill_missing",
    "linear_trend",
    "load_csv",
    "mann_kendall",
    "moving_average",
    "remove_outliers",
    "resample",
]

__version__ = "1.0.0"
