import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import numpy as np  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # noqa: E402
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    max_color,  # pyright: ignore[reportAttributeAccessIssue]
    p50_color,  # pyright: ignore[reportAttributeAccessIssue]
    p90_color,  # pyright: ignore[reportAttributeAccessIssue]
    p99_color,  # pyright: ignore[reportAttributeAccessIssue]
)


def load_summary(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return rows[-1]


def guess_label(path):
    data = load_summary(path)
    if "experiment" in data:
        return data["experiment"]
    return os.path.basename(path)


def main():
    parser = argparse.ArgumentParser(description="Bar-chart comparison of experiments")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--labels", nargs="+")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    labels = args.labels if args.labels else [guess_label(f) for f in args.files]
    if len(labels) != len(args.files):
        parser.error("number of --labels must match number of files")

    os.makedirs("charts", exist_ok=True)

    summaries = [load_summary(f) for f in args.files]

    throughputs = [float(s["throughput"]) for s in summaries]
    p50 = [float(s["p50_ms"]) for s in summaries]
    p90 = [float(s["p90_ms"]) for s in summaries]
    p99 = [float(s["p99_ms"]) for s in summaries]
    maxv = [float(s["max"]) for s in summaries]

    x = np.arange(len(labels))

    # Throughput chart
    fig, ax = plt.subplots(figsize=figsize_single)
    colors = plt.cm.tab10(np.linspace(0, 1, len(labels)))
    bars = ax.bar(x, throughputs, 0.5, color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput comparison")

    def fmt(v):
        return f"{v / 1e3:.0f}K" if v >= 1e3 else f"{v:.0f}"

    ax.bar_label(bars, labels=[fmt(v) for v in throughputs], padding=3)
    ax.margins(y=0.15)
    ax.grid(True, axis="y", **grid_style)
    plt.tight_layout()
    throughput_out = args.output or "charts/comparison-throughput.png"
    plt.savefig(throughput_out, dpi=300, bbox_inches="tight")
    print(f"saved to {throughput_out}")

    # Latency chart
    fig, ax = plt.subplots(figsize=figsize_single)
    bar_width = 0.2
    offsets = np.arange(len(labels))
    ax.bar(offsets - 1.5 * bar_width, p50, bar_width, label="p50", color=p50_color)
    ax.bar(offsets - 0.5 * bar_width, p90, bar_width, label="p90", color=p90_color)
    ax.bar(offsets + 0.5 * bar_width, p99, bar_width, label="p99", color=p99_color)
    ax.bar(offsets + 1.5 * bar_width, maxv, bar_width, label="max", color=max_color)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Latency [ms]")
    ax.set_title("Latency comparison")
    ax.legend(**legend_pos)
    ax.grid(True, axis="y", **grid_style)
    plt.tight_layout()
    latency_out = "charts/comparison-latency.png"
    plt.savefig(latency_out, dpi=300, bbox_inches="tight")
    print(f"saved to {latency_out}")


if __name__ == "__main__":
    main()

#
# Examples
# --------
# Compare two experiments (requires summary CSV files):
#   python3 plot/plot-compare.py csv/a-summary.csv csv/b-summary.csv --labels "A" "B"
#
# Compare three or more:
#   python3 plot/plot-compare.py csv/a-summary.csv csv/b-summary.csv csv/c-summary.csv --labels A B C
#
# Custom output path (only affects throughput chart):
#   python3 plot/plot-compare.py csv/a-summary.csv csv/b-summary.csv -o charts/my-compare.png
