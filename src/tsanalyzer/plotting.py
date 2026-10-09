"""Visualisation of a time series with its trend and outliers."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: works on CI servers without a display
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from tsanalyzer.trend import TrendResult, _time_axis  # noqa: E402


def plot_series(
    series: pd.Series,
    path: str | Path,
    *,
    moving_avg: pd.Series | None = None,
    trend: TrendResult | None = None,
    outliers: pd.Series | None = None,
    title: str | None = None,
    ylabel: str | None = None,
) -> Path:
    """Save a publication-ready PNG/SVG/PDF figure and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(series.index, series.to_numpy(), lw=0.8, color="#9AA5B1", label="Observations")
    if moving_avg is not None:
        ax.plot(moving_avg.index, moving_avg.to_numpy(), lw=1.8, color="#1F3A5F", label="Moving average")
    if trend is not None:
        t = _time_axis(series)
        ax.plot(
            series.index,
            trend.intercept + trend.slope * t,
            lw=1.6,
            ls="--",
            color="#C8553D",
            label=f"Linear trend ({trend.slope_per_year:+.3f}/yr)",
        )
    if outliers is not None and not outliers.empty:
        ax.scatter(outliers.index, outliers.to_numpy(), s=18, color="#C8553D", zorder=3, label="Outliers")

    ax.set_title(title or (series.name or "Time series"))
    ax.set_ylabel(ylabel or (series.name or "value"))
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
