import argparse
import csv
import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportAttributeAccessIssue, reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
)


def load_csv(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
    return rows


def align_metric(runs, metric="throughput"):
    grid = {}
    for run in runs:
        for row in run:
            t = round(row["time_s"])
            grid.setdefault(t, []).append(row[metric])
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

    parser = argparse.ArgumentParser(description="confidence interval of experiments")

    parser.add_argument(
        "dir",
        nargs="?",
        help="path to directory of experiment CSV file",
        default="csv/cloud/exp1/cache/l/uniform",
    )

    args = parser.parse_args()
    data_dir = args.dir

    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]
    print(f"Found {len(csvs)} CSV files")

    runs = [load_csv(f) for f in csvs]
    times, means, cis = align_metric(runs, "throughput")

    fig, ax = plt.subplots(figsize=figsize_single)

    ax.plot([], [], color="gray", alpha=0.3, linewidth=0.8, label="Individual runs")
    for run in runs:
        t = [round(r["time_s"]) for r in run]
        vals = [r["throughput"] for r in run]
        dedup = {}
        for tt, vv in zip(t, vals):
            dedup[tt] = vv
        t = sorted(dedup.keys())
        vals = [dedup[tt] for tt in t]
        # ax.plot(t, vals, color="gray", alpha=0.3, linewidth=0.8)

    ax.plot(times, means, color=exp1_color, linewidth=2, label="Mean")
    ax.fill_between(
        times,
        [m - c for m, c in zip(means, cis)],
        [m + c for m, c in zip(means, cis)],
        color=exp1_color,
        alpha=0.2,
        label="95% confidence interval",
    )

    end_tick = math.ceil(max(times))
    n_ticks = 10
    step = max(1, end_tick // n_ticks)
    ticks = list(range(0, end_tick + 1, step))
    if ticks[-1] != max(times):
        ticks[-1] = max(times)
        if len(ticks) >= 2 and max(times) - ticks[-2] < 1.0:
            ticks.pop(-2)
    ax.set_xticks(ticks)
    ax.set_xlim([0, end_tick + 1])
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput with 95% confidence interval")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    rel = os.path.relpath(data_dir, "csv")
    output = f"charts/{rel}/ci-throughput.png"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    plt.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved to {output}")


if __name__ == "__main__":
    main()
