import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
    CC_LEVELS,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    mean_ci,  # pyright: ignore[reportAttributeAccessIssue]
)

NUMERIC_COLS = ["throughput", "txns"]

# CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]


def data_dir_for(label, size, dist):
    if label == "c16":
        return f"csv/cloud/exp1/cache/{size}/{dist}"
    return f"csv/cloud/exp3/{label}/{size}/{dist}"


if __name__ == "__main__":
    for size in ["l", "s"]:
        for dist in ["uniform", "zipf"]:
            grid = {}

            for label in CC_LEVELS:
                data_dir = data_dir_for(label, size, dist)

                if not os.path.isdir(data_dir):
                    print(f"  Warning: directory not found: {data_dir}")
                    continue

                csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
                csvs = [
                    f
                    for f in csvs
                    if "summary" not in os.path.basename(f)
                    and "avg" not in os.path.basename(f)
                ]
                if not csvs:
                    print(f"  Warning: no CSVs in {data_dir}")
                    continue

                runs = [load_csv(f) for f in csvs]
                for run in runs:
                    for row in run:
                        t = round(row["time_s"])
                        if t not in grid:
                            grid[t] = {}
                        for col in NUMERIC_COLS:
                            grid[t].setdefault(f"{col}_{label}", []).append(row[col])

            if not grid:
                print(f"No data for {size}/{dist}, skipping.")
                continue

            fieldnames = ["time_s"]
            for col in NUMERIC_COLS:
                for label in CC_LEVELS:
                    fieldnames.append(f"{col}_{label}")
                    fieldnames.append(f"{col}_{label}_ci_lower")
                    fieldnames.append(f"{col}_{label}_ci_upper")

            out_rows = []
            for t in sorted(grid.keys()):
                row = {"time_s": t}
                for col in NUMERIC_COLS:
                    for label in CC_LEVELS:
                        key = f"{col}_{label}"
                        vals = grid[t].get(key, [])
                        if len(vals) < 1:
                            row[key] = 0.0
                            row[f"{key}_ci_lower"] = 0.0
                            row[f"{key}_ci_upper"] = 0.0
                        else:
                            m, lo, hi = mean_ci(vals)
                            row[key] = round(m, 3)
                            row[f"{key}_ci_lower"] = round(lo, 3)
                            row[f"{key}_ci_upper"] = round(hi, 3)
                out_rows.append(row)

            out_dir = f"csv/cloud/exp3/{size}/{dist}"
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "avg-exp3.csv")

            with open(out_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in out_rows:
                    formatted = {"time_s": r["time_s"]}
                    for col in fieldnames[1:]:
                        formatted[col] = f"{r[col]:.3f}"
                    writer.writerow(formatted)

            print(f"Saved {len(out_rows)} rows to {out_path}")
