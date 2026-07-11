import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    exp2_color,  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
)


def compute_ci_from_dir(data_dir):
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]
    runs = [load_csv(f) for f in csvs]
    if not runs:
        return [], [], []
    grid = {}
    for run in runs:
        for row in run:
            t = round(row["time_s"])
            grid.setdefault(t, []).append(row["throughput"])
    times = sorted(grid.keys())
    means, cis = [], []
    for t in times:
        vals = grid[t]
        if len(vals) < 2:
            means.append(vals[0])
            cis.append(0.0)
            continue
        mean = sum(vals) / len(vals)
        std = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        ci = 1.96 * std / (len(vals) ** 0.5)
        means.append(mean)
        cis.append(ci)
    return times, means, cis


def main():
    parser = argparse.ArgumentParser(
        description="Compare throughput of two experiments (stacked subplots, own y-scale)"
    )
    parser.add_argument("dir1", help="directory of experiment 1")
    parser.add_argument("dir2", help="directory of experiment 2")
    parser.add_argument("--label1", default="Exp 1")
    parser.add_argument("--label2", default="Exp 2")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    t1, m1, c1 = compute_ci_from_dir(args.dir1)
    t2, m2, c2 = compute_ci_from_dir(args.dir2)

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(figsize_single[0], figsize_single[1] * 1.6),
        gridspec_kw={"height_ratios": [1, 1]},
        sharex=True,
    )
    fig.subplots_adjust(hspace=0.08)

    max_t = 0
    if t1:
        max_t = max(max_t, max(t1))
        ax1.plot(t1, m1, color=exp1_color, linewidth=2, label=args.label1)
        ax1.fill_between(
            t1,
            [a - b for a, b in zip(m1, c1)],
            [a + b for a, b in zip(m1, c1)],
            color=exp1_color,
            alpha=0.2,
            label=f"{args.label1} 95% CI",
        )
    ax1.set_ylabel("Throughput [txns/s]")
    ax1.set_title(args.label1, fontsize=11)
    ax1.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax1.set_ylim(bottom=0)
    ax1.legend(**legend_pos)
    ax1.grid(True, **grid_style)

    if t2:
        max_t = max(max_t, max(t2))
        ax2.plot(t2, m2, color=exp2_color, linewidth=2, label=args.label2)
        ax2.fill_between(
            t2,
            [a - b for a, b in zip(m2, c2)],
            [a + b for a, b in zip(m2, c2)],
            color=exp2_color,
            alpha=0.2,
            label=f"{args.label2} 95% CI",
        )
    ax2.set_xlabel("Time [s]")
    ax2.set_ylabel("Throughput [txns/s]")
    ax2.set_title(args.label2, fontsize=11)
    ax2.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax2.set_ylim(bottom=0)
    ax2.legend(**legend_pos)
    ax2.grid(True, **grid_style)

    if max_t > 0:
        n_ticks = 10
        end_tick = int(max_t) + 1
        step = max(1, end_tick // n_ticks)
        ticks = list(range(0, end_tick + 1, step))
        if ticks[-1] != end_tick:
            ticks[-1] = end_tick
        ax2.set_xticks(ticks)
        ax2.set_xlim(left=0, right=end_tick + 1)

    plt.tight_layout()

    label_text = f"{args.label1}-{args.label2}"
    fig.text(
        0.5,
        0.005,
        label_text,
        ha="center",
        fontsize=8,
        fontstyle="italic",
        color="gray",
    )

    output = args.output or f"charts/compare-throughput-s-{label_text}.png"
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
