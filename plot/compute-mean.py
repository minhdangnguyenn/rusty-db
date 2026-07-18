import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from config import load_csv, mean_ci  # pyright: ignore[reportAttributeAccessIssue]

NUMERIC_COLS = [
    "progress",
    "txns",
    "throughput",
    "p50_ms",
    "p90_ms",
    "p99_ms",
    "max",
    "cache_hits",
    "cache_misses",
    "cache_hit_rate",
]
CI_COLS = [f"{col}_ci_lower" for col in NUMERIC_COLS] + [
    f"{col}_ci_upper" for col in NUMERIC_COLS
]


def main():
    parser = argparse.ArgumentParser(
        description="Average multiple experiment runs into one CSV"
    )
    parser.add_argument("dir", help="directory containing experiment runs")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    data_dir = args.dir
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [
        f
        for f in csvs
        if "summary" not in f and "avg" not in f
    ]

    if not csvs:
        print("No CSV files found")
        return

    print(f"Found {len(csvs)} CSV files")

    runs = [load_csv(f) for f in csvs]

    grid = {}
    for run in runs:
        for row in run:
            t = round(row["time_s"])
            if t not in grid:
                grid[t] = {col: [] for col in NUMERIC_COLS}
            for col in NUMERIC_COLS:
                grid[t][col].append(row[col])

    out_rows = []
    for t in sorted(grid.keys()):
        row = {"time_s": t}
        for col in NUMERIC_COLS:
            vals = grid[t][col]
            if len(vals) < 1:
                row[col] = 0.0
                row[f"{col}_ci_lower"] = 0.0
                row[f"{col}_ci_upper"] = 0.0
            else:
                m, lo, hi = mean_ci(vals)
                row[col] = round(m, 3)
                row[f"{col}_ci_lower"] = round(lo, 3)
                row[f"{col}_ci_upper"] = round(hi, 3)
        out_rows.append(row)

    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(data_dir, "avg.csv")

    fieldnames = ["time_s"] + NUMERIC_COLS + CI_COLS
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in out_rows:
            formatted = {"time_s": row["time_s"]}
            for col in NUMERIC_COLS + CI_COLS:
                formatted[col] = f"{row[col]:.3f}"
            writer.writerow(formatted)

    print(f"Saved {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
