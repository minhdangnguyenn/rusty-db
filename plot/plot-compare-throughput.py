import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
    exp1_color,  # pyright: ignore[reportAttributeAccessIssue]
    exp2_color,  # pyright: ignore[reportAttributeAccessIssue]
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


def main():
    parser = argparse.ArgumentParser(
        description="Compare throughput of two experiments"
    )
    parser.add_argument("files", nargs=2)
    args = parser.parse_args()

    fig, ax = plt.subplots(figsize=figsize_single)
    colors = [exp1_color, exp2_color]
    max_t = 0
    labels = []

    for path, c in zip(args.files, colors):
        data = load_csv(path)

        if "time_s" in data[0]:
            t = [r["time_s"] for r in data]
            tps = [r["throughput"] for r in data]
        else:
            v = data[-1]["throughput"]
            t = [0, data[-1]["total_time_s"]]
            tps = [v, v]

        max_t = max(max_t, max(t))

        if "experiment" in data[0]:
            label = data[0]["experiment"]
        else:
            label = os.path.splitext(os.path.basename(path))[0]
        labels.append(label)

        ax.plot(t, tps, marker="o", color=c, label=label)

    n_ticks = 10
    step = max(1, int(max_t / n_ticks))
    ticks = list(range(0, int(max_t) + 1, step))
    if ticks[-1] != int(max_t):
        ticks.append(int(max_t))
    ax.set_xticks(ticks)
    ax.set_xlim(left=0, right=max_t + 1)
    ax.set_ylim(bottom=0)

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput comparison")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    def short_name(path):
        name = os.path.splitext(os.path.basename(path))[0]
        name = name.removesuffix("-summary")
        parts = name.split("-")
        if parts[0] == "no":
            return f"no-cache-{parts[-1]}"
        return f"{parts[0]}-{parts[-1]}"

    label_text = f"{short_name(args.files[0])}-{short_name(args.files[1])}"
    fig.text(
        0.5,
        0.01,
        label_text,
        ha="center",
        fontsize=8,
        fontstyle="italic",
        color="gray",
    )

    os.makedirs("charts", exist_ok=True)
    plt.savefig(
        f"charts/compare-throughput-{label_text}.png", dpi=300, bbox_inches="tight"
    )


if __name__ == "__main__":
    main()
