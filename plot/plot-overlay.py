#!/usr/bin/env python3
"""
Overlay two experiments on the same chart with dual y-axes.
File 1 -> left axis, File 2 -> right axis.

Usage:
  python3 plot/plot-overlay.py csv/no-cache-...csv csv/cache-...csv --labels "no-cache" "cache"
"""

import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # noqa: E402
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    exp2_color,  # pyright: ignore[reportAttributeAccessIssue]
    figsize_overlay,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos_overlay,  # pyright: ignore[reportAttributeAccessIssue]
    max_color,  # pyright: ignore[reportAttributeAccessIssue]
    p50_color,  # pyright: ignore[reportAttributeAccessIssue]
    p90_color,  # pyright: ignore[reportAttributeAccessIssue]
    p99_color,  # pyright: ignore[reportAttributeAccessIssue]
)

LATENCY_METRICS = [
    ("p50_ms", "-", p50_color),
    ("p90_ms", "-.", p90_color),
    ("p99_ms", "--", p99_color),
    ("max", ":", max_color),
]


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


def flatten_single(data):
    t = [r["time_s"] for r in data]
    rest = {k: [r[k] for r in data] for k in data[0] if k != "time_s"}
    if len(t) == 1:
        t = [0.0, t[0]]
        for k in rest:
            rest[k] = [rest[k][0], rest[k][0]]
    return t, rest, len(t) == 2 and t[0] == 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Overlay two experiments with dual y-axes"
    )
    parser.add_argument("files", nargs=2)
    parser.add_argument("--labels", nargs=2)
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    labels = args.labels or [guess_label(f) for f in args.files]
    os.makedirs("charts", exist_ok=True)

    data_left = load_csv(args.files[0])
    data_right = load_csv(args.files[1])
    t_left, vl, single_left = flatten_single(data_left)
    t_right, vr, single_right = flatten_single(data_right)
    me_left = [-1] if single_left else None
    me_right = [-1] if single_right else None

    # throughput
    fig, ax1 = plt.subplots(figsize=figsize_overlay)
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel(f"Throughput [txns/s]  ({labels[0]})", color=exp1_color)
    ax1.plot(
        t_left,
        vl["throughput"],
        marker="o",
        markevery=me_left,
        color=exp1_color,
        label=labels[0],
    )
    ax1.tick_params(axis="y", labelcolor=exp1_color)

    ax2 = ax1.twinx()
    ax2.set_ylabel(f"Throughput [txns/s]  ({labels[1]})", color=exp2_color)
    ax2.plot(
        t_right,
        vr["throughput"],
        marker="o",
        markevery=me_right,
        color=exp2_color,
        label=labels[1],
    )
    ax2.tick_params(axis="y", labelcolor=exp2_color)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, **legend_pos_overlay)

    ax1.set_title("Throughput overlay")
    ax1.grid(True, **grid_style)
    fig.subplots_adjust(right=0.75)
    p = args.output or "charts/overlay-throughput.png"
    plt.savefig(p, dpi=300, bbox_inches="tight")
    print(f"saved to {p}")

    # latency
    fig, ax1 = plt.subplots(figsize=figsize_overlay)
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel(f"Latency [ms]  ({labels[0]})", color=exp1_color)
    for metric, ls, c in LATENCY_METRICS:
        ax1.plot(
            t_left,
            vl[metric],
            linestyle=ls,
            marker="o",
            markevery=me_left,
            color=c,
            linewidth=2,
            label=f"{labels[0]} {metric[:3]}",
        )
    ax1.tick_params(axis="y", labelcolor=exp1_color)

    ax2 = ax1.twinx()
    ax2.set_ylabel(f"Latency [ms]  ({labels[1]})", color=exp2_color)
    for metric, ls, c in LATENCY_METRICS:
        ax2.plot(
            t_right,
            vr[metric],
            linestyle=ls,
            marker="o",
            markevery=me_right,
            color=c,
            linewidth=1,
            alpha=0.5,
            label=f"{labels[1]} {metric[:3]}",
        )
    ax2.tick_params(axis="y", labelcolor=exp2_color)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, **legend_pos_overlay)

    ax1.set_title("Latency overlay")
    ax1.grid(True, **grid_style)
    fig.subplots_adjust(right=0.75)
    p2 = args.output or "charts/overlay-latency.png"
    plt.savefig(p2, dpi=300, bbox_inches="tight")
    print(f"saved to {p2}")


if __name__ == "__main__":
    main()

#
# Examples
# --------
# Overlay two experiments with dual y-axes:
#   python3 plot/plot-overlay.py csv/no-cache.csv csv/cache.csv --labels "no-cache" "cache"
#
# Custom output path:
#   python3 plot/plot-overlay.py csv/a.csv csv/b.csv --labels A B -o charts/my-overlay.png
