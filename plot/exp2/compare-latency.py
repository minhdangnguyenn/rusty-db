import argparse
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import matplotlib.ticker as ticker  # pyright: ignore[reportMissingImports]
import numpy as np  # pyright: ignore[reportMissingImports]
from matplotlib.path import Path as MatPath  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (
    LIGHT_RED,
    NAVY,
    grid_style,
    legend_pos,
    load_csv,
)


def main():
    parser = argparse.ArgumentParser(
        description="Compare latency percentiles of two averaged CSVs"
    )
    parser.add_argument("csv1", help="first avg CSV", type=str)
    parser.add_argument("csv2", help="second avg CSV", type=str)
    parser.add_argument("--label1", default="FIFO", type=str)
    parser.add_argument("--label2", default="LRU", type=str)
    parser.add_argument("-o", "--output", default=None, type=str)

    args = parser.parse_args()

    csv1 = load_csv(args.csv1)
    csv2 = load_csv(args.csv2)

    last1 = csv1[-1]
    last2 = csv2[-1]

    categories = ["p50", "p90", "p99", "max"]
    keys = ["p50_ms", "p90_ms", "p99_ms", "max"]

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    data1 = [last1[k] for k in keys]
    data2 = [last2[k] for k in keys]

    low1 = [max(0.0, last1.get(f"{k}_ci_lower", last1[k])) for k in keys]
    high1 = [last1.get(f"{k}_ci_upper", last1[k]) for k in keys]

    low2 = [max(0.0, last2.get(f"{k}_ci_lower", last2[k])) for k in keys]
    high2 = [last2.get(f"{k}_ci_upper", last2[k]) for k in keys]

    # Deviation from center
    err1_low = np.array(data1) - np.array(low1)
    err1_high = np.array(high1) - np.array(data1)

    err2_low = np.array(data2) - np.array(low2)
    err2_high = np.array(high2) - np.array(data2)

    # ------------------------------------------------------------------
    # Figure
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5.5))

    ax.set_yscale("log")

    x = np.arange(len(categories))

    # Move the two algorithms slightly apart
    offset = 0.10
    x1 = x - offset
    x2 = x + offset

    # ------------------------------------------------------------------
    # Rectangle marker
    # ------------------------------------------------------------------
    rect_marker = MatPath(
        [
            (-2.5, -1.1),
            (2.5, -1.1),
            (2.5, 1.1),
            (-2.5, 1.1),
            (-2.5, -1.1),
        ]
    )

    # ------------------------------------------------------------------
    # Plot FIFO
    # ------------------------------------------------------------------
    scale = 1.3
    for i, (x_pos, value, err_low, err_high) in enumerate(
        zip(x1, data1, err1_low, err1_high)
    ):
        ax.errorbar(
            x_pos,
            value,
            yerr=[[err_low * scale], [err_high * scale]],
            fmt="none",
            ecolor=NAVY,
            elinewidth=2.5,
            capsize=7,
            capthick=2.5,
            zorder=1,
        )

        ax.plot(
            x_pos,
            value,
            marker=rect_marker,
            ms=19,
            color="white",
            markeredgecolor=NAVY,
            markeredgewidth=1.5,
            zorder=3,
        )

        ax.text(
            x_pos,
            value,
            f"{value:.1f}",
            ha="center",
            va="center",
            fontsize=8,
            color="black",
            zorder=4,
        )

    # ------------------------------------------------------------------
    # Plot LRU
    # ------------------------------------------------------------------
    for i, (x_pos, value, err_low, err_high) in enumerate(
        zip(x2, data2, err2_low, err2_high)
    ):
        ax.errorbar(
            x_pos,
            value,
            yerr=[[err_low], [err_high]],
            fmt="none",
            ecolor=LIGHT_RED,
            elinewidth=2.5,
            capsize=7,
            capthick=2.5,
            zorder=1,
        )

        ax.plot(
            x_pos,
            value,
            marker=rect_marker,
            ms=13,
            color="white",
            markeredgecolor=LIGHT_RED,
            markeredgewidth=1.5,
            zorder=3,
        )

        ax.text(
            x_pos,
            value,
            f"{value:.1f}",
            ha="center",
            va="center",
            fontsize=8,
            color="black",
            zorder=4,
        )

    # ------------------------------------------------------------------
    # Axis
    # ------------------------------------------------------------------
    all_values = (
        list(data1) + list(data2) + list(low1) + list(low2) + list(high1) + list(high2)
    )

    positive_values = [v for v in all_values if v > 0]

    ymin = min(positive_values)
    ymax = max(positive_values)

    bottom = 10 ** math.floor(math.log10(ymin))
    top = 10 ** math.ceil(math.log10(ymax))

    # Add some headroom
    ax.set_ylim(bottom=bottom, top=top * 1.5)

    # Show 10, 100, 1000 instead of 10^1, 10^2, ...
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, pos: f"{v:g}"))

    # Remove minor ticks
    ax.minorticks_off()

    ax.set_ylabel("Latency [ms]")
    ax.set_xlabel("Percentiles")

    ax.set_xticks(x)
    ax.set_xticklabels(categories)

    ax.set_title("Latency comparison with 95% confidence interval (CI)")

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------
    ax.plot(
        [],
        [],
        marker=rect_marker,
        ms=13,
        color="white",
        markeredgecolor=NAVY,
        markeredgewidth=1.5,
        label=args.label1,
    )

    ax.plot(
        [],
        [],
        marker=rect_marker,
        ms=13,
        color="white",
        markeredgecolor=LIGHT_RED,
        markeredgewidth=1.5,
        label=args.label2,
    )

    ax.legend(**legend_pos)

    ax.grid(True, axis="y", **grid_style)
    ax.set_axisbelow(True)

    plt.tight_layout()

    label_text = f"{args.label1}-{args.label2}"
    output = args.output or f"charts/compare-latency-{label_text}.png"

    os.makedirs(os.path.dirname(output), exist_ok=True)

    plt.savefig(
        output,
        dpi=300,
        bbox_inches="tight",
    )

    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
