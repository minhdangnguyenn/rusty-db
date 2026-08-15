import argparse
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from plot.config import (  # noqa: E402
    FIGSIZE,
    GREEN,
    LIGHT_RED,
    ORANGE,
    PURPLE,
    grid_style,
    load_csv,
)


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
    colors = [GREEN, ORANGE, LIGHT_RED, PURPLE]

    _, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.bar(categories, values, color=colors)
    ax.bar_label(bars, fmt="%.1f", padding=2)
    ax.margins(y=0.15)

    ax.ticklabel_format(style="plain", axis="y")
    ax.set_ylabel("Latency [ms]")
    ax.set_xlabel("Percentiles")
    ax.set_title("Latency percentiles")
    ax.grid(True, axis="y", **grid_style)

    plt.tight_layout()

    output = (
        args.output
        or f"charts/{os.path.splitext(os.path.basename(args.csv))[0]}-latency.png"
    )
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output)


if __name__ == "__main__":
    main()
