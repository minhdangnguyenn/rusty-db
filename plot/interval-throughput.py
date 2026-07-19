import argparse
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportAttributeAccessIssue, reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from plot.config import (
    FIGSIZE,
    NAVY,
    compute_ci_from_dir,
    grid_style,
    legend_pos,
)


def main():
    parser = argparse.ArgumentParser(description="confidence interval of experiments")
    parser.add_argument(
        "dir",
        nargs="?",
        help="path to directory of experiment CSV file",
        default="csv/cloud/exp1/cache/l/uniform",
    )

    args = parser.parse_args()
    data_dir = args.dir

    times, means, cis = compute_ci_from_dir(data_dir)

    fig, ax = plt.subplots(figsize=FIGSIZE)

    ax.plot(times, means, color=NAVY, linewidth=2, marker="s", label="Mean")
    ax.fill_between(
        times,
        [m - c for m, c in zip(means, cis)],
        [m + c for m, c in zip(means, cis)],
        color=NAVY,
        alpha=0.2,
        label="95% confidence interval",
    )

    end_tick = 30
    ticks = list(range(0, end_tick + 1))
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    y_max = max([a + b for a, b in zip(means, cis)]) if means else 1
    ax.set_ylim([0, y_max])
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput with 95% confidence interval")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    rel = os.path.relpath(data_dir, "csv")
    output = f"charts/{rel}/ci-throughput.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output)
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
