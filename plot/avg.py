import argparse
import csv
import glob
import os

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
        description="Average multiple experiment runs into one CSV"
    )
    parser.add_argument("dir", help="directory containing experiment runs")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    data_dir = args.dir
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in os.path.basename(f)]

    if not csvs:
        print("No CSV files found")
        return

    print(f"Found {len(csvs)} CSV files")

    runs = [load_csv(f) for f in csvs]
    n_runs = len(runs)

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
            if len(vals) == n_runs:
                row[col] = round(sum(vals) / len(vals), 3)
            else:
                row[col] = round(sum(vals) / len(vals), 3) if vals else 0.0
        out_rows.append(row)

    # Determine output path
    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(data_dir, "avg.csv")

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["time_s"] + NUMERIC_COLS)
        writer.writeheader()
        for row in out_rows:
            formatted = {"time_s": row["time_s"]}
            for col in NUMERIC_COLS:
                formatted[col] = f"{row[col]:.3f}"
            writer.writerow(formatted)

    print(f"Saved {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
