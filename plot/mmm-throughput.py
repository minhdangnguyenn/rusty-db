import csv
import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
)

T_TABLE = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}


def t_critical(n):
    return T_TABLE.get(n, 1.96)


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


def throughput_per_run(data):
    last = data[-1]
    return last["txns"] / last["time_s"]


def mean_ci(vals):
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return mean, mean, mean
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    std = math.sqrt(var)
    half = t_critical(n) * std / math.sqrt(n)
    return mean, mean - half, mean + half


COMBOS = [("l", "uniform"), ("l", "zipf"), ("s", "uniform"), ("s", "zipf")]
LEVELS = ["c4", "c8", "c16", "c32", "c64"]
M = [4, 8, 16, 32, 64]


def data_dir_for(label, size, dist):
    if label == "c16":
        return f"csv/cloud/exp1/cache/{dist}/{size}"
    return f"csv/cloud/exp3/{label}/{size}/{dist}"


for size, dist in COMBOS:
    all_S = []
    means = []
    ci_lowers = []
    ci_uppers = []

    for i, label in enumerate(LEVELS):
        data_dir = data_dir_for(label, size, dist)
        csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
        csvs = [
            f
            for f in csvs
            if "summary" not in os.path.basename(f) and "avg" not in os.path.basename(f)
        ]
        if not csvs:
            print(f"Warning: no CSVs in {data_dir}")
            continue

        runs = [load_csv(f) for f in csvs]
        tps = [throughput_per_run(r) for r in runs]

        # Proposal:
        # S = m / throughput  (average service time per query)
        # µ = 1 / S
        S_vals = [M[i] / tp for tp in tps]
        all_S.extend(S_vals)

        m, lo, hi = mean_ci(tps)
        means.append(m)
        ci_lowers.append(lo)
        ci_uppers.append(hi)

    # µ = 1 / S̅  where S̅ is mean service time across all runs & levels
    S_mean = sum(all_S) / len(all_S)
    mu = 1.0 / S_mean

    n = len(M)
    fig, ax = plt.subplots(figsize=figsize_single)

    ax.plot(
        M,
        means,
        color="#e41a1c",
        linewidth=1.5,
        marker="o",
        markersize=8,
        label="Measured ± 95% CI",
    )
    ax.errorbar(
        M,
        means,
        yerr=[
            [means[i] - ci_lowers[i] for i in range(n)],
            [ci_uppers[i] - means[i] for i in range(n)],
        ],
        fmt="none",
        color="#e41a1c",
        capsize=4,
        capthick=1.5,
    )

    ax.plot(
        [0, max(M) * 1.05],
        [0, mu * max(M) * 1.05],
        linestyle="--",
        color="#377eb8",
        linewidth=2,
        label=f"μ = 1 / S̅ = {mu:.1f} (M/M/m, throughput = μ · m)",
    )

    ax.set_xlabel("Number of workers (m)")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title(f"M/M/m model fit (exp3, {size}, {dist})")
    ax.set_xticks(M)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)
    plt.tight_layout()

    out_dir = f"charts/cloud/exp3/{size}/{dist}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/mmm-throughput.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved to {out_path}")
    plt.close(fig)
