import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
    compute_ci_from_dir,  # pyright: ignore[reportAttributeAccessIssue]
    data_dir_for,  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
)

CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]
colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]
markers = ["o", "s", "^", "D", "v"]

combos = [
    ("l", "uniform"),
    ("l", "zipf"),
    ("s", "uniform"),
    ("s", "zipf"),
]

for size, dist in combos:
    levels = [(label, data_dir_for(label, size, dist)) for label in CC_LEVELS]

    fig, ax = plt.subplots(figsize=figsize_single)
    all_times = []

    for (label, data_dir), color, marker in zip(levels, colors, markers):
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
            marker=marker,
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

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
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
