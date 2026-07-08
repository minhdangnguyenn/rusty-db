import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    exp2_color,  # pyright: ignore[reportAttributeAccessIssue]
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
    parser = argparse.ArgumentParser(
        description="Compare throughput of two averaged CSVs"
    )
    parser.add_argument("csv1", help="first avg CSV")
    parser.add_argument("csv2", help="second avg CSV")
    parser.add_argument("--label1", default="FIFO")
    parser.add_argument("--label2", default="LRU")
    parser.add_argument("--color1", default=exp1_color)
    parser.add_argument("--color2", default=exp2_color)
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    r1 = load_csv(args.csv1)
    r2 = load_csv(args.csv2)

    t1 = [row["time_s"] for row in r1]
    tp1 = [row["throughput"] for row in r1]
    t2 = [row["time_s"] for row in r2]
    tp2 = [row["throughput"] for row in r2]

    fig, ax = plt.subplots(figsize=figsize_single)

    ax.plot(t1, tp1, color=args.color1, linewidth=2, label=args.label1)
    ax.plot(t2, tp2, color=args.color2, linewidth=2, label=args.label2)

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    label_text = f"{args.label1}-{args.label2}"
    fig.text(
        0.5,
        0.01,
        label_text,
        ha="center",
        fontsize=8,
        fontstyle="italic",
        color="gray",
    )

    output = args.output or f"charts/compare-throughput-{label_text}.png"
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
