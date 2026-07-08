import argparse
import csv
import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
)


def load_csv(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
    return rows


def compute_ci_from_dir(data_dir):
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]
    runs = [load_csv(f) for f in csvs]
    if not runs:
        return [], [], []
    grid = {}
    for run in runs:
        for row in run:
            t = round(row["time_s"])
            grid.setdefault(t, []).append(row["throughput"])

    times, means, cis = [], [], []
    for t in sorted(grid.keys()):
        vals = grid[t]
        if len(vals) < 2:
            continue
        mean = sum(vals) / len(vals)
        std = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        ci = 1.96 * std / (len(vals) ** 0.5)
        times.append(t)
        means.append(mean)
        cis.append(ci)
    return times, means, cis


def main():
    parser = argparse.ArgumentParser(
        description="Compare throughput of FIFO and LRU experiments"
    )
    parser.add_argument("dir1", help="directory of FIFO")
    parser.add_argument("dir2", help="directory of LRU")
    parser.add_argument("--label1", default="FIFO")
    parser.add_argument("--label2", default="LRU")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    fifo_color = "#4CAF50"  # green
    lru_color = "#9C27B0"  # purple

    t1, m1, c1 = compute_ci_from_dir(args.dir1)
    t2, m2, c2 = compute_ci_from_dir(args.dir2)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(15, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    fig.subplots_adjust(hspace=0.08)

    ax1.plot(t1, m1, color=fifo_color, linewidth=2, label="FIFO")
    ax1.fill_between(
        t1,
        [a - b for a, b in zip(m1, c1)],
        [a + b for a, b in zip(m1, c1)],
        color=fifo_color,
        alpha=0.2,
        label="FIFO 95% CI",
    )

    ax2.plot(t2, m2, color=lru_color, linewidth=2, label="LRU")
    ax2.fill_between(
        t2,
        [a - b for a, b in zip(m2, c2)],
        [a + b for a, b in zip(m2, c2)],
        color=lru_color,
        alpha=0.2,
        label="LRU 95% CI",
    )

    for ax in [ax1, ax2]:
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.grid(True, **grid_style)

    ax2.set_xlabel("Time [s]")
    fig.supylabel("Throughput [txns/s]")

    d = 0.5
    kwargs = dict(
        marker=[(-1, -d), (1, d)],
        markersize=12,
        linestyle="none",
        color="k",
        mec="k",
        mew=1,
        clip_on=False,
    )
    ax1.plot([0, 1], [0, 0], transform=ax1.transAxes, **kwargs)
    ax2.plot([0, 1], [1, 1], transform=ax2.transAxes, **kwargs)

    ax1.spines.bottom.set_visible(False)
    ax2.spines.top.set_visible(False)
    ax1.tick_params(labeltop=False)
    ax2.xaxis.tick_bottom()

    handles = [
        plt.Line2D([], [], color=fifo_color, linewidth=2, label="FIFO"),
        plt.Line2D([], [], color=lru_color, linewidth=2, label="LRU"),
    ]
    fig.legend(handles=handles, **legend_pos)
    fig.suptitle("FIFO vs LRU Throughput Comparison", fontsize=14)
    plt.tight_layout(rect=[0, 0, 0.85, 0.95])

    output = args.output or "charts/compare-throughput-fifo-vs-lru.png"
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
