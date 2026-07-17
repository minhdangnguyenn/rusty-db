import argparse
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    FIGSIZE,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
)


def main():
    parser = argparse.ArgumentParser(description="Plot throughput over time")
    parser.add_argument("csv", help="path to CSV file")
    parser.add_argument("--label", default=None, help="legend label")
    parser.add_argument("--color", default="#2196F3")
    parser.add_argument("--marker", default="s")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    label = args.label if args.label else os.path.basename(args.csv)

    data = load_csv(args.csv)
    t = [r["time_s"] for r in data]
    tps = [r["throughput"] for r in data]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(t, tps, color=args.color, linewidth=2, marker=args.marker, label=label)
    ax.fill_between(t, tps, color=args.color, alpha=0.1)

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    y_max = max(tps) * 1.1 if tps else 1
    ax.set_ylim([0, y_max])
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput")
    ax.grid(True, **grid_style)
    plt.tight_layout()

    if args.output:
        output = args.output
    else:
        base = os.path.splitext(os.path.basename(args.csv))[0]
        output = f"charts/{base}-throughput.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
