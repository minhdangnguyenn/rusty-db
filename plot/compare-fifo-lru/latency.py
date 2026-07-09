import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import numpy as np  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    exp2_color,  # pyright: ignore[reportAttributeAccessIssue]
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
    parser = argparse.ArgumentParser(description="Compare latency of two averaged CSVs")
    parser.add_argument("csv1", help="first avg CSV")
    parser.add_argument("csv2", help="second avg CSV")
    parser.add_argument("--label1", default="FIFO")
    parser.add_argument("--label2", default="LRU")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    csv1 = load_csv(args.csv1)
    csv2 = load_csv(args.csv2)

    last1 = csv1[-1]
    last2 = csv2[-1]

    categories = ["p50", "p90", "p99", "max"]
    keys = ["p50_ms", "p90_ms", "p99_ms", "max"]

    a_data = [last1[k] for k in keys]
    a_err = [last1[k] - last1.get(f"{k}_ci_lower", last1[k]) for k in keys]
    b_data = [last2[k] for k in keys]
    b_err = [last2[k] - last2.get(f"{k}_ci_lower", last2[k]) for k in keys]
    diff = [a - b for a, b in zip(a_data, b_data)]
    diff_colors = ["#2a7d4f" if v < 0 else "#b94040" for v in diff]

    x = np.arange(len(categories))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8, 6), gridspec_kw={"height_ratios": [2, 1]}, sharex=True
    )
    fig.subplots_adjust(hspace=0.08)

    ax1.bar(
        x - width / 2,
        a_data,
        width,
        yerr=a_err,
        capsize=3,
        label=args.label1,
        color=exp1_color,
        zorder=2,
    )
    ax1.bar(
        x + width / 2,
        b_data,
        width,
        yerr=b_err,
        capsize=3,
        label=args.label2,
        color=exp2_color,
        zorder=2,
    )
    ax1.set_ylabel("Latency (ms)")
    ax1.legend(**legend_pos)
    ax1.grid(axis="y", **grid_style)
    ax1.set_axisbelow(True)

    ax2.bar(x, diff, width * 1.5, color=diff_colors, zorder=2)
    ax2.axhline(0, color="gray", linewidth=0.8)
    ax2.set_ylabel(f"{args.label1} - {args.label2} (ms)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.set_xlabel("Percentiles")
    ax2.grid(axis="y", **grid_style)
    ax2.set_axisbelow(True)

    label_text = f"{args.label1}-{args.label2}"
    fig.text(
        0.5,
        0.01,
        f"Comparison: {label_text}",
        ha="center",
        fontsize=8,
        fontstyle="italic",
        color="gray",
    )

    label_text = f"{args.label1}-{args.label2}"
    output = args.output or f"charts/compare-latency-{label_text}.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
