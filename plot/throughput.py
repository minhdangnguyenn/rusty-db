import argparse
import csv
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
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


def main():
    parser = argparse.ArgumentParser(description="Plot throughput over time")
    parser.add_argument("csv", help="path to CSV file")
    parser.add_argument("--label", default=None, help="legend label")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    label = args.label if args.label else os.path.basename(args.csv)

    data = load_csv(args.csv)
    t = [r["time_s"] for r in data]
    tps = [r["throughput"] for r in data]

    single = len(t) == 1
    if single:
        val = tps[0]
        t, tps = [0, t[0]], [val, val]

    fig, ax = plt.subplots(figsize=figsize_single)
    x_max = max(t)
    markers = list(range(0, len(t), max(1, len(t) // 10)))
    if markers[-1] != len(t) - 1:
        markers.append(len(t) - 1)
    # y_max = max(tps)
    ax.plot(t, tps, marker="o", markevery=[-1] if single else markers, label=label)

    end_tick = math.ceil(x_max)
    n_ticks = 10
    step = max(1, end_tick // n_ticks)
    ticks = list(range(0, end_tick + 1, step))
    if ticks[-1] != x_max:
        ticks[-1] = x_max
        if len(ticks) >= 2 and x_max - ticks[-2] < 1.0:
            ticks.pop(-2)
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    ax.ticklabel_format(style="plain", axis="y")
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput over time")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    output = (
        args.output
        or f"charts/{os.path.splitext(os.path.basename(args.csv))[0]}-throughput.png"
    )
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
