# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [1.0.0] — 2026-10-09

### Added
- CSV loading with validation (`load_csv`).
- Gap filling: time-weighted interpolation, forward/backward fill, drop.
- Outlier detection: IQR and z-score.
- Deseasonalisation by monthly or day-of-year climatology.
- Resampling to any pandas frequency.
- Descriptive statistics and autocorrelation.
- Linear trend (OLS) and Mann–Kendall test; moving average.
- Plotting of series, trend and outliers.
- Command-line interface with JSON report.
- CI (lint, test matrix, build) and release workflows on GitHub Actions.
