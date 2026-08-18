import argparse
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from plot.config import (
    FIGSIZE,
    NAVY,
    LIGHT_RED,
    grid_style,
    legend_pos,
    load_csv,
)


def main():
    parser = argparse.ArgumentParser(description="Plot cache hit/miss rate over time")
    parser.add_argument("csv", help="path to CSV file")
    parser.add_argument("--label", default=None, help="legend label")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    data = load_csv(args.csv)
    t = [r["time_s"] for r in data]
    hit_rate = [r["cache_hit_rate"] * 100 for r in data]
    miss_rate = [100 - float(r["cache_hit_rate"]) * 100 for r in data]

    single = len(t) == 1
    if single:
        t, hit_rate = [0, t[0]], [hit_rate[0], hit_rate[0]]
        t, miss_rate = [0, t[0]], [miss_rate[0], miss_rate[0]]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    x_max = max(t)
    markers = list(range(len(t)))

    ax.plot(
        t,
        hit_rate,
        marker="o",
        markevery=[-1] if single else markers,
        label="Hit ratio",
        color=NAVY,
    )
    ax.plot(
        t,
        miss_rate,
        marker="s",
        markevery=[-1] if single else markers,
        label="Miss ratio",
        color=LIGHT_RED,
        linestyle="--",
    )

    end_tick = math.ceil(x_max)
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick])
    ax.set_ylim([0, 100])

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Rate [%]")
    ax.set_title("Cache hit / miss rate over time")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    output = (
        args.output
        or f"charts/{os.path.splitext(os.path.basename(args.csv))[0]}-cache-hit-rate.png"
    )
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output)


if __name__ == "__main__":
    main()
