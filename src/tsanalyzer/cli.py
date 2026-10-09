"""Command-line interface: ``tsanalyzer data.csv --value-col temp_c --plot out.png``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tsanalyzer import __version__
from tsanalyzer.cleaning import fill_missing, remove_outliers, resample
from tsanalyzer.io import DataFormatError, load_csv
from tsanalyzer.stats import autocorrelation, describe
from tsanalyzer.trend import linear_trend, mann_kendall, moving_average


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tsanalyzer",
        description="Clean a time series from a CSV file, compute statistics and trends.",
    )
    p.add_argument("csv", type=Path, help="input CSV file")
    p.add_argument("--time-col", default="date", help="timestamp column (default: date)")
    p.add_argument("--value-col", default="value", help="value column (default: value)")
    p.add_argument("--fill", default="linear", choices=["linear", "ffill", "bfill", "drop"])
    p.add_argument("--outliers", default="iqr", choices=["iqr", "zscore", "none"])
    p.add_argument("--threshold", type=float, default=None, help="outlier threshold (k or z)")
    p.add_argument("--resample", default=None, help="pandas frequency, e.g. W or MS")
    p.add_argument("--window", type=int, default=7, help="moving-average window (default: 7)")
    p.add_argument("--plot", type=Path, default=None, help="save a figure to this path")
    p.add_argument("--report", type=Path, default=None, help="save a JSON report to this path")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def run(args: argparse.Namespace) -> dict:
    series = load_csv(args.csv, time_col=args.time_col, value_col=args.value_col)
    raw_missing = int(series.isna().sum())
    series = fill_missing(series, method=args.fill)
    if args.resample:
        series = resample(series, args.resample)

    outliers = series.iloc[0:0]
    if args.outliers != "none":
        series, outliers = remove_outliers(series, method=args.outliers, threshold=args.threshold)
    n_outliers = len(outliers)

    trend = linear_trend(series)
    report = {
        "input": str(args.csv),
        "filled_missing": raw_missing,
        "outliers_removed": int(n_outliers),
        "statistics": describe(series),
        "lag1_autocorrelation": autocorrelation(series, lag=1),
        "linear_trend": trend.to_dict(),
        "mann_kendall": mann_kendall(series),
    }

    if args.plot:
        from tsanalyzer.plotting import plot_series

        plot_series(
            series,
            args.plot,
            moving_avg=moving_average(series, args.window),
            trend=trend,
            outliers=outliers,
        )
        report["plot"] = str(args.plot)
    return report


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
    except (FileNotFoundError, DataFormatError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
