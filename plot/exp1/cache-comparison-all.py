import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    FIGSIZE,  # pyright: ignore[reportAttributeAccessIssue]
    compute_ci_from_dir,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
)

CONFIGS = [
    ("Cache, Uniform", "#2196F3", "o", "csv/cloud/exp1/cache/l/uniform"),
    ("Cache, Zipfian", "#4CAF50", "^", "csv/cloud/exp1/cache/l/zipf"),
    ("No cache, Uniform", "#F44336", "s", "csv/cloud/exp1/no-cache/l/uniform"),
    ("No cache, Zipfian", "#FF9800", "D", "csv/cloud/exp1/no-cache/l/zipf"),
]


def main():
    fig, ax = plt.subplots(figsize=FIGSIZE)

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

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim(left=0, right=end_tick + 1)

    # auto y-limit with padding
    all_vals = []
    for _, _, _, path in CONFIGS:
        _, means, cis = compute_ci_from_dir(path)
        for m, c in zip(means, cis):
            all_vals.extend([m - c, m + c])
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
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
