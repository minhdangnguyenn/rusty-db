import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    FIGSIZE,  # pyright: ignore[reportAttributeAccessIssue]
    GREEN,  # pyright: ignore[reportAttributeAccessIssue]
    ORANGE,  # pyright: ignore[reportAttributeAccessIssue]
    PURPLE,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    p99_color,  # pyright: ignore[reportAttributeAccessIssue]
)


def compute_ci(vals):
    n = len(vals)
    mean = sum(vals) / n
    std = (sum((v - mean) ** 2 for v in vals) / (n - 1)) ** 0.5
    ci = 1.96 * std / (n**0.5)
    return mean, ci


def main():
    parser = argparse.ArgumentParser(
        description="Latency confidence interval as bar chart"
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default="csv/cloud/exp1/cache/l/uniform",
        help="path to directory of experiment CSV files",
    )
    args = parser.parse_args()
    data_dir = args.dir

    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]
    print(f"Found {len(csvs)} CSV files")

    runs = [load_csv(f) for f in csvs]
    last_rows = [run[-1] for run in runs]

    metrics = ["p50_ms", "p90_ms", "p99_ms", "max"]
    labels = ["p50", "p90", "p99", "max"]
    colors = [GREEN, ORANGE, p99_color, PURPLE]

    means, cis = [], []
    for metric in metrics:
        vals = [row[metric] for row in last_rows]
        mean, ci = compute_ci(vals)
        means.append(mean)
        cis.append(ci)

    _, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(
        labels, means, color=colors, yerr=cis, capsize=5, error_kw={"linewidth": 1.5}
    )
    ax.bar_label(bars, fmt="%.1f", padding=2)
    ax.margins(y=0.15)

    ax.set_ylabel("Latency [ms]")
    ax.set_xlabel("Percentiles")
    ax.set_title("Latency percentiles with 95% CI")
    ax.grid(True, axis="y", **grid_style)
    plt.tight_layout()

    rel = os.path.relpath(data_dir, "csv")
    output = f"charts/{rel}/ci-latency.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
