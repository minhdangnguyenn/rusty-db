import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # noqa: E402  # pyright: ignore[reportAttributeAccessIssue]
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


def guess_output(files):
    os.makedirs("charts", exist_ok=True)
    base = os.path.splitext(os.path.basename(files[0]))[0]
    if base.endswith("-summary"):
        base = base[: -len("-summary")]
    return (
        f"charts/{base}-throughput.png"
        if len(files) == 1
        else "charts/comparison-throughput.png"
    )


def guess_label(path):
    data = load_csv(path)
    if data and "experiment" in data[0]:
        return data[0]["experiment"]
    return os.path.basename(path)


def main():
    parser = argparse.ArgumentParser(description="Plot throughput over time")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--labels", nargs="+")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    labels = args.labels if args.labels else [guess_label(f) for f in args.files]
    output = args.output if args.output else guess_output(args.files)

    if len(labels) != len(args.files):
        parser.error("number of --labels must match number of files")

    fig, ax = plt.subplots(figsize=figsize_single)
    for path, label in zip(args.files, labels):
        data = load_csv(path)
        t = [r["time_s"] for r in data]
        tps = [r["rate_tps"] for r in data]
        single = len(t) == 1
        if single:
            val = tps[0]
            t, tps = [0, t[0]], [val, val]
        ax.plot(t, tps, marker="o", markevery=[-1] if single else None, label=label)

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput over time")
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()

#
# Examples
# --------
# Plot a single data CSV with auto-derived label:
#   python3 plot/plot-throughput.py csv/no-cache-read-s-uniform-3.csv
#
# Plot with custom label:
#   python3 plot/plot-throughput.py csv/no-cache-read-s-uniform-3.csv --labels "my-label"
#
# Compare multiple runs:
#   python3 plot/plot-throughput.py csv/a.csv csv/b.csv --labels "A" "B"
#
# Custom output path:
#   python3 plot/plot-throughput.py csv/data.csv -o charts/my-chart.png
