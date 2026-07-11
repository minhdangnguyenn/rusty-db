import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from config import figsize_single, grid_style


def main():
    parser = argparse.ArgumentParser(description="Plot throughput of a single run")
    parser.add_argument("csv", help="path to single run CSV")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--color", default="#2196F3")
    parser.add_argument("--marker", default="s")
    args = parser.parse_args()

    rows = []
    with open(args.csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: float(v) for k, v in row.items()})

    t = [row["time_s"] for row in rows]
    tp = [row["throughput"] for row in rows]

    fig, ax = plt.subplots(figsize=figsize_single)
    ax.plot(t, tp, color=args.color, linewidth=2, marker=args.marker, label="Throughput")
    ax.fill_between(t, tp, color=args.color, alpha=0.1)

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    y_max = max(tp) * 1.1 if tp else 1
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
        output = f"charts/single/{base}-throughput.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
