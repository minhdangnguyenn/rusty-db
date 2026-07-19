import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plot.config import (
    FIGSIZE,
    GREEN,
    LIGHT_RED,
    NAVY,
    ORANGE,
    compute_ci_from_dir,
    grid_style,
    legend_pos,
)

CONFIGS = [
    ("Cache, Uniform", NAVY, "o", "csv/cloud/exp1/cache/l/uniform"),
    ("Cache, Zipfian", GREEN, "^", "csv/cloud/exp1/cache/l/zipf"),
    ("No cache, Uniform", LIGHT_RED, "s", "csv/cloud/exp1/no-cache/l/uniform"),
    ("No cache, Zipfian", ORANGE, "D", "csv/cloud/exp1/no-cache/l/zipf"),
]


def main():
    fig, ax = plt.subplots(figsize=FIGSIZE)

    all_vals = []
    for label, color, marker, path in CONFIGS:
        t, means, cis = compute_ci_from_dir(path)
        if not t:
            continue
        ax.plot(t, means, color=color, linewidth=2, marker=marker, label=label)
        ax.fill_between(
            t,
            [a - b for a, b in zip(means, cis)],
            [a + b for a, b in zip(means, cis)],
            color=color,
            alpha=0.15,
        )
        for m, c in zip(means, cis):
            all_vals.extend([m - c, m + c])

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim(left=0, right=end_tick + 1)

    if all_vals:
        ax.set_ylim(bottom=0, top=max(all_vals) * 1.1)

    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title(
        "Throughput comparison across cache and access patterns (large dataset)"
    )
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    out_path = "charts/cloud/exp1/throughput-all-large.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
