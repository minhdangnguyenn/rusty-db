import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # noqa: E402
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    max_color,  # pyright: ignore[reportAttributeAccessIssue]
    p50_color,  # pyright: ignore[reportAttributeAccessIssue]
    p90_color,  # pyright: ignore[reportAttributeAccessIssue]
    p99_color,  # pyright: ignore[reportAttributeAccessIssue]
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
        description="Plot latency percentiles as bar chart"
    )
    parser.add_argument("csv", help="path to CSV file")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    data = load_csv(args.csv)
    summary = data[-1]

    categories = ["p50", "p90", "p99", "max"]
    values = [summary["p50_ms"], summary["p90_ms"], summary["p99_ms"], summary["max"]]
    colors = [p50_color, p90_color, p99_color, max_color]

    fig, ax = plt.subplots(figsize=figsize_single)
    bars = ax.bar(categories, values, color=colors)
    ax.bar_label(bars, fmt="%.1f", padding=2)
    ax.margins(y=0.15)

    ax.set_ylabel("Latency [ms]")
    ax.set_title("Latency percentiles")
    ax.grid(True, axis="y", **grid_style)

    plt.tight_layout()

    output = (
        args.output
        or f"charts/{os.path.splitext(os.path.basename(args.csv))[0]}-latency.png"
    )
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
