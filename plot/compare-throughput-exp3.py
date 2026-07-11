import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
)


def compute_ci_from_dir(data_dir):
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [
        f
        for f in csvs
        if "summary" not in os.path.basename(f) and "avg" not in os.path.basename(f)
    ]
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


colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]

combos = [
    ("l", "uniform"),
    ("l", "zipf"),
    ("s", "uniform"),
    ("s", "zipf"),
]

for size, dist in combos:
    levels = [
        ("c4", f"csv/cloud/exp3/c4/{size}/{dist}"),
        ("c8", f"csv/cloud/exp3/c8/{size}/{dist}"),
        ("c16", f"csv/cloud/exp1/cache/{dist}/{size}"),
        ("c32", f"csv/cloud/exp3/c32/{size}/{dist}"),
        ("c64", f"csv/cloud/exp3/c64/{size}/{dist}"),
    ]

    fig, ax = plt.subplots(figsize=figsize_single)
    all_times = []

    for (label, data_dir), color in zip(levels, colors):
        if not os.path.isdir(data_dir):
            print(f"  Warning: directory not found: {data_dir}")
            continue
        times, means, cis = compute_ci_from_dir(data_dir)
        if not times:
            print(f"  Warning: no data for {label} at {data_dir}")
            continue
        all_times.extend(times)
        markevery = [i for i, t in enumerate(times) if t % 3 == 0]
        ax.plot(
            times,
            means,
            color=color,
            linewidth=2,
            marker="o",
            markevery=markevery,
            label=label,
        )
        ax.fill_between(
            times,
            [m - c for m, c in zip(means, cis)],
            [m + c for m, c in zip(means, cis)],
            color=color,
            alpha=0.2,
            label=f"{label} 95% CI",
        )

    if not all_times:
        print(f"  No data for {size}/{dist}, skipping.")
        continue

    max_t = math.ceil(max(all_times))
    n_ticks = 10
    step = max(1, max_t // n_ticks)
    ticks = list(range(0, max_t + 1, step))
    if ticks[-1] != max_t:
        ticks[-1] = max_t
        if len(ticks) >= 2 and max_t - ticks[-2] < 1.0:
            ticks.pop(-2)

    ax.set_xticks(ticks)
    ax.set_xlim([0, max_t + 1])
    ax.set_ylim(bottom=0)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title(f"Throughput comparison (exp3, {size}, {dist})")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    output = f"charts/cloud/exp3/{size}/{dist}/compare-throughput-ci.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved to {output}")
    plt.close(fig)
