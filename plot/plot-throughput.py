import argparse
import csv
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
    # y_max = max(tps)
    ax.plot(t, tps, marker="o", markevery=[-1] if single else None, label=label)

    ax.set_xticks(range(0, int(max(t)) + 2))
    ax.set_xlim([1, x_max])

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
