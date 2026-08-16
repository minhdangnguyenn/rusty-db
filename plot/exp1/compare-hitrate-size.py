import argparse
import os
from pathlib import Path
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

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

def main():
    parser = argparse.ArgumentParser(
        description="Compare cache hit/miss ratio between two configs"
    )
    parser.add_argument("dir1", help="directory with avg.csv (first config)")
    parser.add_argument("dir2", help="directory with avg.csv (second config)")
    parser.add_argument("--metric", choices=["hit", "miss"], default="hit")
    parser.add_argument("--label1", default="Small")
    parser.add_argument("--label2", default="Large")
    parser.add_argument("--color1", default=NAVY)
    parser.add_argument("--color2", default=LIGHT_RED)
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    d1 = load_csv(os.path.join(args.dir1, "avg.csv"))
    d2 = load_csv(os.path.join(args.dir2, "avg.csv"))

    def extract(data):
        t = [row["time_s"] for row in data]
        if args.metric == "miss":
            val = [(1 - row["cache_hit_rate"]) * 100 for row in data]
            lo = [
                (1 - row.get("cache_hit_rate_ci_upper", row["cache_hit_rate"])) * 100
                for row in data
            ]
            hi = [
                (1 - row.get("cache_hit_rate_ci_lower", row["cache_hit_rate"])) * 100
                for row in data
            ]
        else:
            val = [row["cache_hit_rate"] * 100 for row in data]
            lo = [
                row.get("cache_hit_rate_ci_lower", row["cache_hit_rate"]) * 100
                for row in data
            ]
            hi = [
                row.get("cache_hit_rate_ci_upper", row["cache_hit_rate"]) * 100
                for row in data
            ]
        return t, val, lo, hi

    t1, v1, lo1, hi1 = extract(d1)
    t2, v2, lo2, hi2 = extract(d2)

    _, ax = plt.subplots(figsize=FIGSIZE)

    ax.plot(
        t1, v1, color=args.color1, linewidth=2, marker="o", label=f"{args.label1} mean"
    )
    ax.fill_between(
        t1, lo1, hi1, color=args.color1, alpha=0.2, label=f"{args.label1} 95% CI"
    )
    ax.plot(
        t2, v2, color=args.color2, linewidth=2, marker="s", label=f"{args.label2} mean"
    )
    ax.fill_between(
        t2, lo2, hi2, color=args.color2, alpha=0.2, label=f"{args.label2} 95% CI"
    )

    ax.set_xticks(list(range(0, 31)))
    ax.set_xlim([0, 31])  # pyright: ignore[reportArgumentType]
    ax.set_ylim([0, 100])  # pyright: ignore[reportArgumentType]
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Miss ratio [%]" if args.metric == "miss" else "Hit ratio [%]")
    ax.set_title(
        f"{'Miss' if args.metric == 'miss' else 'Hit'} ratio: {args.label1} vs {args.label2}"
    )
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    output = args.output or f"charts/{args.label1}-{args.label2}-{args.metric}.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output)
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
