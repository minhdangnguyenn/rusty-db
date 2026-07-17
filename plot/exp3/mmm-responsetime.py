import glob
import math
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    CC_LEVELS,  # pyright: ignore[reportAttributeAccessIssue]
    FIGSIZE,  # pyright: ignore[reportAttributeAccessIssue]
    GREEN,  # pyright: ignore[reportAttributeAccessIssue]
    RED,  # pyright: ignore[reportAttributeAccessIssue]
    M,  # pyright: ignore[reportAttributeAccessIssue]
    data_dir_for,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    mean_ci,  # pyright: ignore[reportAttributeAccessIssue]
)

FACT = [math.factorial(n) for n in range(65)]


def data_dir_nocache(label, size, dist):
    return f"csv/cloud/exp3-nocache/{dist}/{label}/{size}"


# get the power of 10
# 10, 20, 30, ...
def nice_step(max_val, target_bins=10):
    if max_val <= 0:
        return 1.0
    step = max_val / target_bins
    exp = 10 ** math.floor(math.log10(step))
    return round(step / exp) * exp


def throughput_per_run(data):
    last = data[-1]
    return last["txns"] / last["time_s"]


def estimate_mu(size, dist):
    data_dir = data_dir_nocache("c1", size, dist)
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
    if not csvs:
        return None
    runs = [load_csv(f) for f in csvs]
    tps = [throughput_per_run(r) for r in runs]
    e_s_vals = [1 / tp for tp in tps]
    e_s = sum(e_s_vals) / len(e_s_vals)
    return 1.0 / e_s


def mmm_response_time(m, lam, mu):
    p = min(lam / (m * mu), 0.9999)

    mp = m * p
    p_0 = 1.0 / (
        1 + sum(mp**n / FACT[n] for n in range(1, m)) + mp**m / (FACT[m] * (1 - p))
    )

    q = mp**m / (FACT[m] * (1 - p)) * p_0

    return (1.0 / mu) * (1.0 + q / (m * (1 - p)))


def closed_throughput(m, mu):
    lo, hi = 0.0, m * mu * 0.99999
    for _ in range(200):
        mid = (lo + hi) / 2.0
        Er = mmm_response_time(m, mid, mu)
        if Er == float("inf") or mid > m / Er:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def main():
    for size, dist in [
        ("l", "uniform"),
        ("l", "zipf"),
        ("s", "uniform"),
        ("s", "zipf"),
    ]:
        means = []
        ci_lowers = []
        ci_uppers = []

        for label in CC_LEVELS:
            data_dir = data_dir_for(label, size, dist)
            csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
            csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
            if not csvs:
                continue

            runs = [load_csv(f) for f in csvs]
            tps = [throughput_per_run(r) for r in runs]

            m_val, lo, hi = mean_ci(tps)
            means.append(m_val)
            ci_lowers.append(lo)
            ci_uppers.append(hi)

        if len(means) < 1:
            continue

        n = len(means)
        M_used = M[:n]

        mu = estimate_mu(size, dist)
        if mu is None:
            print(
                f"Warning: no c1 data for {size}/{dist}, falling back to heuristic",
                file=sys.stderr,
            )
            mu = max(means[i] / M_used[i] for i in range(n)) / 0.95
        else:
            print(f"({size}/{dist}) = {mu:.2f} req/s (from K=1 no-cache data)")

        # Measured response time: E[r] = K / λ
        rt_meas = [M_used[i] / means[i] * 1000 for i in range(n)]
        rt_lower = [M_used[i] / ci_uppers[i] * 1000 for i in range(n)]
        rt_upper = [M_used[i] / ci_lowers[i] * 1000 for i in range(n)]

        # Predicted response time from closed M/M/m:
        # E[r] = K / λ_predicted  (Little's law)
        rt_mmm = [M_used[i] / closed_throughput(M_used[i], mu) * 1000 for i in range(n)]

        fig, ax = plt.subplots(figsize=FIGSIZE)

        ax.plot(
            M_used,
            rt_meas,
            color=RED,
            linewidth=1.5,
            marker="o",
            markersize=8,
            label="Measured",
        )
        ax.errorbar(
            M_used,
            rt_meas,
            yerr=[
                [rt_meas[i] - rt_lower[i] for i in range(n)],
                [rt_upper[i] - rt_meas[i] for i in range(n)],
            ],
            fmt="none",
            color=RED,
            capsize=4,
            capthick=1.5,
        )

        ax.plot(
            M_used,
            rt_mmm,
            color=GREEN,
            linewidth=1.5,
            marker="s",
            markersize=8,
            label="M/M/m predicted",
        )

        ax.set_ylabel("Average response time [ms]")
        ax.set_title("M/M/m response time")

        valid = [v for v in rt_meas + rt_mmm if math.isfinite(v)]
        if valid:
            step = nice_step(max(valid))
            ax.yaxis.set_major_locator(MultipleLocator(step))

        ax.set_xlabel("Concurrency level (K = m)")
        ax.set_xticks(M_used)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        os.makedirs("charts/cloud/exp3/", exist_ok=True)
        out_path = f"charts/cloud/exp3/mmm-responsetime-{size}-{dist}.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
