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

# t-distribution table for 95% ci with small samples
# key = degrees of freedom (n - 1), value = t-critical
# n=5 runs -> df=4 -> t=3.182 (wider than z=1.96 for small samples)
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


def mean_ci(vals) -> tuple[float, float, float]:
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return mean, mean, mean
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    std = math.sqrt(var)
    half = t_critical(n) * std / math.sqrt(n)
    return mean, mean - half, mean + half


def data_dir_for(label, size, dist) -> str:
    if label == "c16":
        return f"csv/cloud/exp1/cache/{dist}/{size}"
    return f"csv/cloud/exp3/{label}/{size}/{dist}"


if __name__ == "__main__":
    # experiment combos: (size, distribution)
    EXPS = [("l", "uniform"), ("l", "zipf"), ("s", "uniform"), ("s", "zipf")]
    # concurrency levels to evaluate
    CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]
    # workers per level
    M = [4, 8, 16, 32, 64]

    for size, dist in EXPS:
        all_S = []
        tps_means = []
        tps_lowers = []
        tps_uppers = []

        for i, label in enumerate(CC_LEVELS):
            data_dir = data_dir_for(label, size, dist)
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
            tps = [throughput_per_run(r) for r in runs]

            # proposal: S = m / throughput, µ = 1 / S
            S_vals = [M[i] / tp for tp in tps]
            all_S.extend(S_vals)

            m, lo, hi = mean_ci(tps)
            tps_means.append(m)
            tps_lowers.append(lo)
            tps_uppers.append(hi)

        # µ = 1 / S̅ where S̅ is the mean service time across all runs
        S_mean = sum(all_S) / len(all_S)
        mu = 1.0 / S_mean

        n = len(M)

        # measured avg response time via little's law: r = m / throughput (ms)
        rt_means = [M[i] / tps_means[i] * 1000 for i in range(n)]
        rt_lowers = [M[i] / tps_uppers[i] * 1000 for i in range(n)]
        rt_uppers = [M[i] / tps_lowers[i] * 1000 for i in range(n)]

        # m/m/m ideal: response time = 1/µ = S̅ (service time, no queue)
        rt_ideal = S_mean * 1000  # convert to ms

        fig, ax = plt.subplots(figsize=figsize_single)

        # measured points
        ax.plot(
            M,
            rt_means,
            color="#e41a1c",
            linewidth=1.5,
            marker="o",
            markersize=8,
            label="Measured (Little's law: m / throughput)",
        )
        # ci error bars
        ax.errorbar(
            M,
            rt_means,
            yerr=[
                [rt_means[i] - rt_lowers[i] for i in range(n)],
                [rt_uppers[i] - rt_means[i] for i in range(n)],
            ],
            fmt="none",
            color="#e41a1c",
            capsize=4,
            capthick=1.5,
        )

        # ideal horizontal line at service time
        ax.axhline(
            y=rt_ideal,
            linestyle="--",
            color="#377eb8",
            linewidth=2,
            label=f"S̅ = {rt_ideal:.1f} ms  (M/M/m ideal, R = 1/μ)",
        )

        ax.set_xlabel("Number of workers (m)")
        ax.set_ylabel("Average response time [ms]")
        ax.set_title(f"M/M/m average response time (exp3, {size}, {dist})")
        ax.set_xticks(M)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        out_dir = f"charts/cloud/exp3/{size}/{dist}"
        os.makedirs(out_dir, exist_ok=True)
        out_path = f"{out_dir}/mmm-response-time.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)
