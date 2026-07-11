import argparse
import math
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
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
)


def main():
    parser = argparse.ArgumentParser(
        description="Compare miss ratio overtime of two averaged CSVs"
    )
    parser.add_argument("csv1", help="first avg CSV")
    parser.add_argument("csv2", help="second avg CSV")
    parser.add_argument("--label1", default="FIFO")
    parser.add_argument("--label2", default="LRU")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    r1 = load_csv(args.csv1)
    r2 = load_csv(args.csv2)

    t1 = [row["time_s"] for row in r1]
    tp1 = [(1 - row["cache_hit_rate"]) * 100 for row in r1]
    lo1 = [
        (1 - row.get("cache_hit_rate_ci_upper", row["cache_hit_rate"])) * 100
        for row in r1
    ]
    hi1 = [
        (1 - row.get("cache_hit_rate_ci_lower", row["cache_hit_rate"])) * 100
        for row in r1
    ]

    t2 = [row["time_s"] for row in r2]
    tp2 = [(1 - row["cache_hit_rate"]) * 100 for row in r2]
    lo2 = [
        (1 - row.get("cache_hit_rate_ci_upper", row["cache_hit_rate"])) * 100
        for row in r2
    ]
    hi2 = [
        (1 - row.get("cache_hit_rate_ci_lower", row["cache_hit_rate"])) * 100
        for row in r2
    ]

    _, ax = plt.subplots(figsize=figsize_single)

    ax.plot(
        t1, tp1, color=exp1_color, linewidth=2, marker="o", label=f"{args.label1} mean"
    )
    ax.fill_between(
        t1,
        lo1,
        hi1,
        color=exp1_color,
        alpha=0.2,
        label=f"{args.label1} 95% CI",
    )
    ax.plot(
        t2, tp2, color=exp2_color, linewidth=2, marker="o", label=f"{args.label2} mean"
    )
    ax.fill_between(
        t2,
        lo2,
        hi2,
        color=exp2_color,
        alpha=0.2,
        label=f"{args.label2} 95% CI",
    )

    all_t = sorted(set(t1 + t2))
    end_tick = math.ceil(max(all_t))
    n_ticks = 10
    step = max(1, end_tick // n_ticks)
    ticks = list(range(0, end_tick + 1, step))
    if ticks[-1] != end_tick:
        ticks[-1] = end_tick
        if len(ticks) >= 2 and end_tick - ticks[-2] < 1.0:
            ticks.pop(-2)
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    ax.set_ylim([0, 100])
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Miss ratio [%]")
    ax.set_title("Miss ratio")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    label_text = f"{args.label1}-{args.label2}"
    output = args.output or f"charts/miss-ratio-{label_text}.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
