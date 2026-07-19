import argparse
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plot.config import (
    FIGSIZE,
    NAVY,
    LIGHT_RED,
    grid_style,
    legend_pos,
    load_csv,
)


def main():
    parser = argparse.ArgumentParser(
        description="Compare throughput of two averaged CSVs"
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
    tp1 = [row["throughput"] for row in r1]
    lo1 = [row.get("throughput_ci_lower", row["throughput"]) for row in r1]
    hi1 = [row.get("throughput_ci_upper", row["throughput"]) for row in r1]

    t2 = [row["time_s"] for row in r2]
    tp2 = [row["throughput"] for row in r2]
    lo2 = [row.get("throughput_ci_lower", row["throughput"]) for row in r2]
    hi2 = [row.get("throughput_ci_upper", row["throughput"]) for row in r2]

    fig, ax = plt.subplots(figsize=FIGSIZE)

    ax.plot(
        t1, tp1, color=LIGHT_RED, linewidth=2, marker="s", label=f"{args.label1} mean"
    )
    ax.fill_between(
        t1,
        lo1,
        hi1,
        color=LIGHT_RED,
        alpha=0.2,
        label=f"{args.label1} 95% CI",
    )
    ax.plot(
        t2, tp2, color=NAVY, linewidth=2, marker="^", label=f"{args.label2} mean"
    )
    ax.fill_between(
        t2,
        lo2,
        hi2,
        color=NAVY,
        alpha=0.2,
        label=f"{args.label2} 95% CI",
    )

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    all_vals = tp1 + tp2 + lo1 + lo2 + hi1 + hi2
    y_max = max(all_vals) if all_vals else 1
    ax.set_ylim([0, y_max])
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput comparison with 95% confidence interval (CI)")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    label_text = f"{args.label1}-{args.label2}"
    output = args.output or f"charts/compare-throughput-{label_text}.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output)


if __name__ == "__main__":
    main()
