import csv
import math

p50_color = "#4CAF50"
p90_color = "#FF9800"
p99_color = "#F44336"
max_color = "#9C27B0"

exp1_color = "#2196F3"
exp2_color = "#FF5722"

legend_pos = {"loc": "upper left", "bbox_to_anchor": (1.02, 1)}

grid_style = {"linestyle": "--", "alpha": 0.3}

figsize_single = (12, 5)

# t-distribution table for 95% ci with small samples
# key = degrees of freedom (n - 1), value = t-critical
# n=5 runs -> df=4 -> t=3.182 (wider than z=1.96 for small samples)
T_TABLE = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}


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
