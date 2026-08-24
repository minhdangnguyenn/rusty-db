"""
Exp 1 — Cache hit ratio over time
Small dataset: Uniform vs Zipfian access
"""

import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import matplotlib.ticker as ticker  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (
    FIGSIZE,
    LIGHT_RED,
    NAVY,
    grid_style,
    legend_pos,
    load_csv,
)


def extract(data):
    t = [row["time_s"] for row in data]
    val = [row["cache_hit_rate"] * 100 for row in data]
    lo = [row.get("cache_hit_rate_ci_lower", row["cache_hit_rate"]) * 100 for row in data]
    hi = [row.get("cache_hit_rate_ci_upper", row["cache_hit_rate"]) * 100 for row in data]
    return t, val, lo, hi


def main():
    cache_dir = PROJECT_ROOT / "csv" / "cloud" / "exp1" / "cache" / "s"

    uniform_data = load_csv(os.path.join(cache_dir, "uniform", "avg.csv"))
    zipf_data = load_csv(os.path.join(cache_dir, "zipf", "avg.csv"))

    t_u, v_u, lo_u, hi_u = extract(uniform_data)
    t_z, v_z, lo_z, hi_z = extract(zipf_data)

    fig, ax = plt.subplots(figsize=FIGSIZE)

    ax.plot(
        t_u, v_u,
        color=NAVY, linewidth=2, marker="o", markersize=4,
        label="Uniform",
    )
    ax.fill_between(t_u, lo_u, hi_u, color=NAVY, alpha=0.15, label="Uniform 95% CI")

    ax.plot(
        t_z, v_z,
        color=LIGHT_RED, linewidth=2, marker="s", markersize=4,
        label="Zipfian",
    )
    ax.fill_between(t_z, lo_z, hi_z, color=LIGHT_RED, alpha=0.15, label="Zipfian 95% CI")

    ax.set_xticks(list(range(0, 31)))
    ax.set_xlim([0, 31])
    ax.set_ylim([0, 105])
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Cache hit ratio [%]")
    ax.set_title(
        "Cache hit ratio — Small dataset: Uniform vs Zipfian access",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)

    output = "charts/cloud/exp1/compare/hitrate-s-uniform-zipf.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
