"""
Exp 3 — Throughput vs number of clients (K)
Cloud data (phase 1), all configs on one chart, K ∈ {4, 8, 16, 32, 64}
Broken y-axis with legend inside the figure at top right.
"""

import csv
import glob
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.ticker import FuncFormatter, MultipleLocator  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (
    FIGSIZE,
    GREEN,
    LIGHT_RED,
    NAVY,
    ORANGE,
    CC_LEVELS,
    M,
    grid_style,
    mean_ci,
)

DATA_DIR = "csv/cloud/exp3"
LINE_STYLE = {"linewidth": 2, "markersize": 7}

CONFIGS = [
    ("s", "uniform", NAVY,  "o", "Small / Uniform"),
    ("s", "zipf",    GREEN, "s", "Small / Zipfian"),
    ("l", "uniform", LIGHT_RED, "^", "Large / Uniform"),
    ("l", "zipf",    ORANGE, "D", "Large / Zipfian"),
]


def load_throughput_k(size, dist):
    means, ci_lo, ci_hi = [], [], []
    for label, k in zip(CC_LEVELS, M):
        data_dir = f"{DATA_DIR}/{label}/{size}/{dist}"
        csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
        csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
        if not csvs:
            means.append(0)
            ci_lo.append(0)
            ci_hi.append(0)
            continue
        throughputs = []
        for csv_path in csvs:
            with open(csv_path) as f:
                rows = list(csv.DictReader(f))
            if rows:
                last = rows[-1]
                t = float(last["txns"]) / float(last["time_s"])
                throughputs.append(t)
        m, lo, hi = mean_ci(throughputs)
        means.append(m)
        ci_lo.append(lo)
        ci_hi.append(hi)
    return means, ci_lo, ci_hi


def nice_step(max_val, target_bins=5):
    if max_val <= 0:
        return 1.0
    step = max_val / target_bins
    exp = 10 ** math.floor(math.log10(step))
    return round(step / exp) * exp


def add_line(ax, ks, means, ci_lo, ci_hi, color, marker, label):
    ax.plot(ks, means, color=color, marker=marker, label=label, **LINE_STYLE)
    ax.errorbar(
        ks, means,
        yerr=[
            [max(means[i] - ci_lo[i], 0) for i in range(len(ks))],
            [ci_hi[i] - means[i] for i in range(len(ks))],
        ],
        fmt="none", color=color, capsize=4, capthick=1.5,
    )


def add_break_marks(ax_top, ax_bot):
    d = 0.015
    kw = {"color": "k", "clip_on": False}
    ax_bot.plot((-d, +d), (1 - d, 1 + d), transform=ax_bot.transAxes, **kw)
    ax_bot.plot((-d, +d), (1 + d, 1 - d), transform=ax_bot.transAxes, **kw)
    ax_top.plot((-d, +d), (-d, +d), transform=ax_top.transAxes, **kw)
    ax_top.plot((-d, +d), (-d - d, -d + d), transform=ax_top.transAxes, **kw)


def main():
    ks = M[:len(CC_LEVELS)]

    data = {}
    for size, dist, color, marker, label in CONFIGS:
        means, ci_lo, ci_hi = load_throughput_k(size, dist)
        data[(size, dist)] = (means, ci_lo, ci_hi, color, marker, label)

    # Large dataset range (bottom panel)
    large_vals_all = []
    for dist in ["uniform", "zipf"]:
        large_vals_all.extend(data[("l", dist)][0])
    large_max = max(v for v in large_vals_all if v > 0)
    bottom_ceil = large_max * 1.2

    # Small dataset range (top panel)
    small_vals_all = []
    for dist in ["uniform", "zipf"]:
        small_vals_all.extend(data[("s", dist)][0])
    small_min = min(v for v in small_vals_all if v > 0)
    small_max = max(v for v in small_vals_all if v > 0)
    top_floor = small_min * 0.8
    top_ceil = small_max * 1.15

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, sharex=True,
        gridspec_kw={"height_ratios": [1, 1], "hspace": 0.06},
        figsize=(FIGSIZE[0] * 1.2, FIGSIZE[1] * 2),
    )

    for (size, dist), (means, ci_lo, ci_hi, color, marker, label) in data.items():
        add_line(ax_top, ks, means, ci_lo, ci_hi, color, marker, label)
        add_line(ax_bot, ks, means, ci_lo, ci_hi, color, marker, label)

    # Top panel
    ax_top.set_ylim(top_floor, top_ceil)
    ax_top.yaxis.set_major_locator(MultipleLocator(nice_step(top_ceil - top_floor)))
    ax_top.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax_top.set_title("Throughput vs K (cloud)", fontsize=13, fontweight="bold", pad=12)
    ax_top.grid(True, **grid_style)
    ax_top.spines["bottom"].set_visible(False)
    ax_top.tick_params(bottom=False)
    ax_top.legend(loc="upper right", fontsize=9, frameon=True)

    # Bottom panel
    ax_bot.set_ylim(0, bottom_ceil)
    ax_bot.yaxis.set_major_locator(MultipleLocator(nice_step(bottom_ceil)))
    ax_bot.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax_bot.grid(True, **grid_style)
    ax_bot.spines["top"].set_visible(False)
    ax_bot.tick_params(top=False)
    ax_bot.set_xlabel("Number of clients (K)", fontsize=11)
    ax_bot.set_xticks(ks)

    add_break_marks(ax_top, ax_bot)
    fig.text(0.04, 0.5, "Throughput [txns/s]", va="center", rotation="vertical", fontsize=11)

    fig.subplots_adjust(left=0.13, right=0.97, top=0.93, bottom=0.08)

    output = "charts/cloud/exp3/throughput-vs-clients.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Saved to {output}")
    plt.close(fig)


if __name__ == "__main__":
    main()
