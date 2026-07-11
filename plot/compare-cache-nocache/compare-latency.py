import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import numpy as np  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    exp2_color,  # pyright: ignore[reportAttributeAccessIssue]
    # figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
)


def compute_latency_ci_from_dir(data_dir):
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]
    runs = [load_csv(f) for f in csvs]
    if not runs:
        return {}, {}
    last_rows = [run[-1] for run in runs]
    metrics = {"p50_ms": "p50", "p90_ms": "p90", "p99_ms": "p99", "max": "max"}
    means, cis = {}, {}
    for key in metrics:
        vals = [row[key] for row in last_rows]
        n = len(vals)
        mean = sum(vals) / n
        std = (sum((v - mean) ** 2 for v in vals) / (n - 1)) ** 0.5
        ci = 1.96 * std / (n**0.5)
        means[key] = mean
        cis[key] = ci
    return means, cis


def main():
    parser = argparse.ArgumentParser(
        description="Compare latency percentiles of two experiments (CI)"
    )
    parser.add_argument("dir1", help="directory of experiment 1 (cache)")
    parser.add_argument("dir2", help="directory of experiment 2 (no-cache)")
    parser.add_argument("--label1", default="Cache")
    parser.add_argument("--label2", default="No cache")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    m1, c1 = compute_latency_ci_from_dir(args.dir1)
    m2, c2 = compute_latency_ci_from_dir(args.dir2)

    categories = ["p50", "p90", "p99", "max"]
    keys = ["p50_ms", "p90_ms", "p99_ms", "max"]

    a_data = [m1[k] for k in keys]
    a_err = [c1[k] for k in keys]
    b_data = [m2[k] for k in keys]
    b_err = [c2[k] for k in keys]
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

    output = args.output or f"charts/compare-latency-{label_text}.png"
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
