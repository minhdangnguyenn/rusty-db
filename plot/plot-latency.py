import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # noqa: E402
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    max_color,  # pyright: ignore[reportAttributeAccessIssue]
    p50_color,  # pyright: ignore[reportAttributeAccessIssue]
    p90_color,  # pyright: ignore[reportAttributeAccessIssue]
    p99_color,  # pyright: ignore[reportAttributeAccessIssue]
)

LATENCY_METRICS = [
    ("p50_ms", "-", p50_color),
    ("p90_ms", "-.", p90_color),
    ("p99_ms", "--", p99_color),
    ("max", ":", max_color),
]


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
        f"charts/{base}-latency.png"
        if len(files) == 1
        else "charts/comparison-latency.png"
    )


def guess_label(path):
    data = load_csv(path)
    if data and "experiment" in data[0]:
        return data[0]["experiment"]
    return os.path.basename(path)


def main():
    parser = argparse.ArgumentParser(description="Plot latency percentiles over time")
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
        vals = {m: [r[m] for r in data] for m, _, _ in LATENCY_METRICS}
        single = len(t) == 1
        if single:
            t = [0, t[0]]
            for m in vals:
                vals[m] = [vals[m][0], vals[m][0]]
        kwargs = {"markevery": [-1]} if single else {}
        for metric, ls, c in LATENCY_METRICS:
            ax.plot(
                t,
                vals[metric],
                linestyle=ls,
                color=c,
                marker="o",
                label=f"{label} {metric[:3]}",
                **kwargs,
            )

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Latency [ms]")
    ax.set_title("Latency over time")
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
#   python3 plot/plot-latency.py csv/no-cache-read-s-uniform-3.csv
#
# Plot with custom label:
#   python3 plot/plot-latency.py csv/no-cache-read-s-uniform-3.csv --labels "my-label"
#
# Compare multiple runs:
#   python3 plot/plot-latency.py csv/a.csv csv/b.csv --labels "A" "B"
#
# Custom output path:
#   python3 plot/plot-latency.py csv/data.csv -o charts/my-chart.png
