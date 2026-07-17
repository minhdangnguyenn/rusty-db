import csv
import glob
import math
import os

GREEN = "#4CAF50"
ORANGE = "#FF9800"
p99_color = "#F44336"
PURPLE = "#9C27B0"

exp1_color = "#2196F3"
exp2_color = "#F44336"
RED = "#e41a1c"
BLUE = "#377eb8"

legend_pos = {"loc": "upper left", "bbox_to_anchor": (1.02, 1)}

grid_style = {"linestyle": "--", "alpha": 0.3}

FIGSIZE = (12, 5)

# t-distribution table for 95% ci with small samples
# key = degrees of freedom (n - 1), value = t-critical
# n=5 runs -> df=4 -> t=3.182 (wider than z=1.96 for small samples)
T_TABLE = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}
CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]
M = [4, 8, 16, 32, 64]


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


def t_critical(n):
    return T_TABLE.get(n, 1.96)


def mean_ci(vals):
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return mean, mean, mean
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    std = math.sqrt(var)
    half = t_critical(n) * std / math.sqrt(n)
    return mean, mean - half, mean + half


def compute_ci_from_dir(data_dir):
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
    runs = [load_csv(f) for f in csvs]
    if not runs:
        return [], [], []
    grid = {}
    for run in runs:
        for row in run:
            t = round(row["time_s"])
            grid.setdefault(t, []).append(row["throughput"])
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


def data_dir_for(label, size, dist):
    if label == "c16":
        return f"csv/cloud/exp1/cache/{size}/{dist}"
    return f"csv/cloud/exp3/{label}/{size}/{dist}"
