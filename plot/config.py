import csv
import glob
import math
import os
from typing import TypeAlias, cast

GREEN = "#4CAF50"
ORANGE = "#FF9800"
PURPLE = "#9C27B0"
NAVY = "#2196F3"
LIGHT_RED = "#F44336"
RED = "#e41a1c"
BLUE = "#377eb8"

legend_pos = {"loc": "upper left", "bbox_to_anchor": (1.02, 1)}

grid_style = {"linestyle": "--", "alpha": 0.3}

FIGSIZE = (12, 5)

# minimum bottom of latency y-axis [ms]; values below are clamped when drawn
Y_FLOOR_MS = 0.1

# t-distribution table for 95% ci with small samples
# key = sample size n, value = t-critical with df = n - 1
# n=5 runs -> df=4 -> t=2.776 (wider than z=1.96 for small samples)
T_TABLE = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}
CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]
M = [4, 8, 16, 32, 64]

CSVValue: TypeAlias = float | str
CSVRow: TypeAlias = dict[str, CSVValue]


def load_csv(path: str) -> list[CSVRow]:
    rows: list[CSVRow] = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed: CSVRow = {}
            for k, v in row.items():
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
    return rows


def t_critical(n) -> float:
    return T_TABLE.get(n, 1.96)


def mean_ci(vals: list[float]):
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return mean, mean, mean
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    std = math.sqrt(var)
    half = t_critical(n) * std / math.sqrt(n)
    return mean, mean - half, mean + half


def log_ci(vals: list[float]):
    # Compute the mean and 95% CI on a log scale, then back-transform. This
    # keeps the interval strictly positive, which matters for latency data
    # with heavy tails (e.g. p99) where the arithmetic CI can go negative.
    logs = [math.log10(v) for v in vals]
    n = len(logs)
    mean_log = sum(logs) / n
    mean = 10**mean_log
    if n < 2:
        return mean, mean, mean
    var = sum((x - mean_log) ** 2 for x in logs) / (n - 1)
    std = math.sqrt(var)
    half = t_critical(n) * std / math.sqrt(n)
    return mean, 10 ** (mean_log - half), 10 ** (mean_log + half)


def compute_ci_from_dir(
    data_dir: str,
) -> tuple[list[int], list[float], list[float]]:
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]

    runs = [load_csv(f) for f in csvs]

    if not runs:
        return [], [], []

    grid: dict[int, list[float]] = {}

    for run in runs:
        for row in run:
            t = round(float(row["time_s"]))
            throughput = float(row["throughput"])
            grid.setdefault(t, []).append(throughput)

    times: list[int] = []
    means: list[float] = []
    cis: list[float] = []

    for t in sorted(grid):
        vals = grid[t]

        if len(vals) < 2:
            continue

        mean = sum(vals) / len(vals)

        std = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5

        ci = t_critical(len(vals)) * std / (len(vals) ** 0.5)

        times.append(t)
        means.append(mean)
        cis.append(ci)

    return times, means, cis


def data_dir_for(label: str, size: str, dist: str):
    """old function to get data directory for a given label, size, and distribution
    this function was used in phase 1
    """
    if label == "c16":
        return f"csv/cloud/exp1/cache/{size}/{dist}"
    return f"csv/cloud/exp3/{label}/{size}/{dist}"
