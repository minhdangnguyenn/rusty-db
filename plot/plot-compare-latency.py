import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import numpy as np  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
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


def guess_label(path):
    data = load_csv(path)
    if data and "experiment" in data[0]:
        return data[0]["experiment"]
    return os.path.basename(path)


def main():
    parser = argparse.ArgumentParser(
        description="Compare latency percentiles of two experiments"
    )
    parser.add_argument("files", nargs=2)
    args = parser.parse_args()

    labels = [guess_label(f) for f in args.files]
    summaries = [load_csv(f)[-1] for f in args.files]

    categories = ["p50", "p90", "p99", "max"]
    keys = ["p50_ms", "p90_ms", "p99_ms", "max"]

    a_data = [summaries[0][k] for k in keys]
    b_data = [summaries[1][k] for k in keys]
    diff = [a - b for a, b in zip(a_data, b_data)]
    colors = ["#2a7d4f" if v < 0 else "#b94040" for v in diff]

    x = np.arange(len(categories))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=figsize_single, gridspec_kw={"height_ratios": [2, 1]}, sharex=True
    )
    fig.subplots_adjust(hspace=0.08)

    # top: grouped bars
    ax1.bar(x - width / 2, a_data, width, label=labels[0], color=exp1_color, zorder=2)
    ax1.bar(x + width / 2, b_data, width, label=labels[1], color=exp2_color, zorder=2)
    ax1.set_ylabel("Latency (ms)")
    ax1.legend(**legend_pos)
    ax1.grid(axis="y", **grid_style)
    ax1.set_axisbelow(True)

    # bottom: difference bars
    ax2.bar(x, diff, width * 1.5, color=colors, zorder=2)
    ax2.axhline(0, color="gray", linewidth=0.8)
    ax2.set_ylabel("cache - no cache (ms)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.grid(axis="y", **grid_style)
    ax2.set_axisbelow(True)

    basename1 = os.path.splitext(os.path.basename(args.files[0]))[0]
    basename2 = os.path.splitext(os.path.basename(args.files[1]))[0]
    fig.text(
        0.5,
        0.01,
        f"Comparison: {basename1} vs {basename2}",
        ha="center",
        fontsize=8,
        fontstyle="italic",
        color="gray",
    )

    plt.tight_layout()
    os.makedirs("charts", exist_ok=True)
    plt.savefig(
        f"charts/comparison-latency-{basename1}-{basename2}.png",
        dpi=300,
        bbox_inches="tight",
    )


if __name__ == "__main__":
    main()
