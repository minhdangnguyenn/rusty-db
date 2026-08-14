import argparse
import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import matplotlib.ticker as ticker  # pyright: ignore[reportMissingImports]
from matplotlib.path import Path  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from plot.config import (
    FIGSIZE,
    GREEN,
    LIGHT_RED,
    ORANGE,
    PURPLE,
    grid_style,
    load_csv,
    log_ci,
)


def main():
    parser = argparse.ArgumentParser(
        description="Latency confidence interval as bar chart"
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default="csv/cloud/exp1/cache/l/uniform",
        help="path to directory of experiment CSV files",
    )
    args = parser.parse_args()
    data_dir = args.dir

    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]
    print(f"Found {len(csvs)} CSV files")

    runs = [load_csv(f) for f in csvs]
    last_rows = [run[-1] for run in runs]

    metrics = ["p50_ms", "p90_ms", "p99_ms", "max"]
    labels = ["p50", "p90", "p99", "max"]
    colors = [GREEN, ORANGE, LIGHT_RED, PURPLE]

    rect_marker = Path(
        [(-0.9, -0.3), (0.9, -0.3), (0.9, 0.3), (-0.9, 0.3), (-0.9, -0.3)]
    )

    means, err_low, err_up = [], [], []
    for metric in metrics:
        vals = [row[metric] for row in last_rows]
        m, lo, hi = log_ci(vals)
        means.append(m)
        err_low.append(m - lo)
        err_up.append(hi - m)

    _, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_yscale("log")
    top = 10 ** math.ceil(math.log10(max(m + u for m, u in zip(means, err_up))))
    bot = 10 ** math.floor(math.log10(min(m - l for m, l in zip(means, err_low))))
    ax.set_ylim(bottom=bot, top=top)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, pos: f"{v:g}"))
    ax.minorticks_off()

    for i, (label, m, lo_, up, color) in enumerate(
        zip(labels, means, err_low, err_up, colors)
    ):
        x = float(i)
        ax.errorbar(
            x,
            m,
            yerr=[[lo_], [up]],
            fmt="none",
            ecolor=color,
            elinewidth=2.5,
            capsize=8,
            capthick=2.5,
            zorder=1,
        )
        ax.plot(
            [x],
            [m],
            marker=rect_marker,
            ms=24,
            color="white",
            markeredgecolor=color,
            markeredgewidth=1.5,
            zorder=3,
        )
        ax.text(
            x,
            m,
            f"{m:.1f}",
            ha="center",
            va="center",
            fontsize=8,
            color="black",
            zorder=4,
        )

    ax.set_ylabel("Latency [ms]")
    ax.set_xlabel("Percentiles")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_title("Latency percentiles with 95% CI")
    ax.grid(True, axis="y", **grid_style)
    plt.tight_layout()

    rel = os.path.relpath(data_dir, "csv")
    output = f"charts/{rel}/ci-latency.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
