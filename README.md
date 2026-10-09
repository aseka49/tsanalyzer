# tsanalyzer

[![CI](https://github.com/aseka49/tsanalyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/aseka49/tsanalyzer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)

A small, tested Python toolkit for exploratory analysis of **scientific time series**
(meteorological, environmental, sensor or experimental measurements). It turns a raw CSV
file into a cleaned series, a JSON report of statistics and trends, and a publication-ready figure.

## Features

| Step | Function | Methods |
|---|---|---|
| Load | `load_csv` | Any date/value columns, custom separator, duplicate timestamps averaged |
| Fill gaps | `fill_missing` | Time-weighted linear interpolation, forward/backward fill, drop |
| Outliers | `remove_outliers` | Tukey IQR fences, z-score |
| Resample | `resample` | Any pandas frequency (`W`, `MS`, `YS`…) with mean/sum/min/max/median |
| Statistics | `describe`, `autocorrelation` | Mean, std, quartiles, skewness, kurtosis, lag-k autocorrelation |
| Trend | `linear_trend`, `mann_kendall`, `moving_average` | OLS slope with R² and p-value, non-parametric Mann–Kendall test |
| Plot | `plot_series` | Observations, moving average, trend line, highlighted outliers |

## Installation

```bash
git clone https://github.com/aseka49/tsanalyzer.git
cd tsanalyzer
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick start

### Command line

```bash
tsanalyzer examples/temperature.csv --value-col temp_c \
    --window 30 \
    --plot out/anomalies.png --report out/report.json
```

Key options: `--fill {linear,ffill,bfill,drop}`, `--outliers {iqr,zscore,none}`,
`--threshold`, `--resample W`, `--window N`.
Run `tsanalyzer --help` for the full list.

### Python API

```python
from tsanalyzer import load_csv, fill_missing, remove_outliers, linear_trend, mann_kendall

s = load_csv("examples/temperature.csv", value_col="temp_c")
s = fill_missing(s, "linear")
s, outliers = remove_outliers(s, "iqr")

print(linear_trend(s).slope_per_year)  # °C per year
print(mann_kendall(s)["trend"])
```

## Development

```bash
pytest                      # run the test suite 
pytest --cov                # with coverage (CI requires ≥ 85 %)
ruff check . && ruff format --check .
```

Continuous integration (`.github/workflows/ci.yml`) runs linting, the test suite on Python 3.11–3.14
(plus Windows and macOS), a CLI smoke test and a package build on every push and pull request.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branching and commit conventions.

## Project structure

```
src/tsanalyzer/     package source (io, cleaning, stats, trend, plotting, cli)
tests/              unit and CLI tests
examples/           sample dataset
docs/               figures and example reports
.github/            CI/CD workflows, issue and PR templates
```

## Citation

If you use this tool in academic work, please cite it using the metadata in [CITATION.cff](CITATION.cff).

## License

Released under the [MIT License](LICENSE).
