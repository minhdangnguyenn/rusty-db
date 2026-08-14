import argparse
import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
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
        [(-0.75, -0.15), (0.75, -0.15), (0.75, 0.15), (-0.75, 0.15), (-0.75, -0.15)]
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

    for label, m, lo_, up, color in zip(labels, means, err_low, err_up, colors):
        ax.errorbar(
            label,
            m,
            yerr=[[lo_], [up]],
            fmt="",
            marker=rect_marker,
            ms=12,
            markeredgewidth=1.5,
            capsize=8,
            capthick=2.5,
            elinewidth=2.5,
            color=color,
        )
        ax.annotate(
            f"{m:.1f}",
            (label, m),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
        )

    ax.set_ylabel("Latency [ms]")
    ax.set_xlabel("Percentiles")
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
