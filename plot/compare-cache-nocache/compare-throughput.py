import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

# from matplotlib.ticker import MaxNLocator  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
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
            continue
        mean = sum(vals) / len(vals)
        std = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
        ci = 1.96 * std / (len(vals) ** 0.5)
        means.append(mean)
        cis.append(ci)
    return times, means, cis


def main():
    parser = argparse.ArgumentParser(
        description="Compare throughput of two experiments (CI)"
    )
    parser.add_argument("dir1", help="directory of experiment 1 (cache)")
    parser.add_argument("dir2", help="directory of experiment 2 (no-cache)")
    parser.add_argument("--label1", default="Cache")
    parser.add_argument("--label2", default="No cache")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    t1, m1, c1 = compute_ci_from_dir(args.dir1)
    t2, m2, c2 = compute_ci_from_dir(args.dir2)

    fig, ax = plt.subplots(figsize=figsize_single)
    max_t = 0
    if t1:
        max_t = max(max_t, max(t1))
        ax.plot(t1, m1, color=exp1_color, linewidth=2, label=args.label1)
        ax.fill_between(
            t1,
            [a - b for a, b in zip(m1, c1)],
            [a + b for a, b in zip(m1, c1)],
            color=exp1_color,
            alpha=0.2,
            label=f"{args.label1} 95% CI",
        )
    if t2:
        max_t = max(max_t, max(t2))
        ax.plot(t2, m2, color=exp2_color, linewidth=2, label=args.label2)
        ax.fill_between(
            t2,
            [a - b for a, b in zip(m2, c2)],
            [a + b for a, b in zip(m2, c2)],
            color=exp2_color,
            alpha=0.2,
            label=f"{args.label2} 95% CI",
        )

    n_ticks = 10
    step = max(1, int(max_t / n_ticks))
    ticks = list(range(0, int(max_t) + 1, step))
    if ticks[-1] != int(max_t):
        ticks.append(int(max_t))
    ax.set_xticks(ticks)
    ax.set_xlim(left=0, right=max_t + 1)
    # all_vals = []
    # if m1:
    #     all_vals.extend(m1)
    # if m2:
    #     all_vals.extend(m2)
    # if all_vals:
    #     loc = MaxNLocator(nbins=5)
    #     yticks = loc.tick_values(0, max(all_vals))
    #     step = yticks[1] - yticks[0] if len(yticks) > 1 else 1
    #     top = yticks[-1] + step
    # # else:
    #     top = None

    ax.set_ylim(bottom=0)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput comparison")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    label_text = f"{args.label1}-{args.label2}"
    fig.text(
        0.5,
        0.01,
        label_text,
        ha="center",
        fontsize=8,
        fontstyle="italic",
        color="gray",
    )

    output = args.output or f"charts/compare-throughput-{label_text}.png"
    os.makedirs("charts", exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
