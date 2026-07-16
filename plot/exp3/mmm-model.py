import argparse
import glob
import math
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    GREEN,  # pyright: ignore[reportAttributeAccessIssue]
    RED,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    mean_ci,  # pyright: ignore[reportAttributeAccessIssue]
)

CC_LEVELS_PLOT = ["c4", "c8", "c16", "c32", "c64"]
M_PLOT = [4, 8, 16, 32, 64]
FIGSIZE = (14, 5)

# precompute n! for n = 0..64 used in p0 formula
FACT = [math.factorial(n) for n in range(65)]


def data_dir_for_nocache(label, size, dist):
    return f"csv/cloud/exp3-nocache/{dist}/{label}/{size}"


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
    """μ = 1/E[s] where E[s] is mean response time at K=1 (no queueing)."""
    data_dir = data_dir_for_nocache("c1", size, dist)
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [
        f
        for f in csvs
        if "summary" not in os.path.basename(f) and "avg" not in os.path.basename(f)
    ]
    if not csvs:
        return None
    runs = [load_csv(f) for f in csvs]
    tps = [throughput_per_run(r) for r in runs]
    e_s_vals = [1 / tp for tp in tps]
    e_s = sum(e_s_vals) / len(e_s_vals)
    return 1.0 / e_s


def mmm_response_time(m, lam, mu):
    # ρ = λ / (m·μ)
    # I set clamp here (k = 16 l zipf saturated)
    p = min(lam / (m * mu), 0.9999)

    # p0 = 1 / [ Σ (mρ)ⁿ/n! + (mρ)ᵐ / (m!·(1-ρ)) ]
    mp = m * p
    sum_terms = sum(mp**n / FACT[n] for n in range(m))
    extra = mp**m / (FACT[m] * (1 - p))
    p_0 = 1.0 / (sum_terms + extra)

    # q = P(queueing) = (mρ)ᵐ / (m!·(1-ρ)) · p0
    q = mp**m / (FACT[m] * (1 - p)) * p_0

    # E[r] = 1/μ · (1 + q / (m·(1-ρ)))
    return 1.0 / mu * (1.0 + q / (m * (1 - p)))


def closed_throughput(m, mu):
    """self-consistent throughput for closed M/M/m: λ = m / E[r](λ)"""
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
    parser = argparse.ArgumentParser(description="M/M/m model plot")
    parser.add_argument(
        "--mode", choices=["throughput", "response-time"], default="response-time"
    )
    args = parser.parse_args()

    for size, dist in [
        ("l", "uniform"),
        ("l", "zipf"),
        ("s", "uniform"),
        ("s", "zipf"),
    ]:
        means = []
        ci_lowers = []
        ci_uppers = []

        for label in CC_LEVELS_PLOT:
            data_dir = data_dir_for_nocache(label, size, dist)
            csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
            csvs = [
                f
                for f in csvs
                if "summary" not in os.path.basename(f)
                and "avg" not in os.path.basename(f)
            ]
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
        M_used = M_PLOT[:n]

        mu = estimate_mu(size, dist)
        if mu is None:
            print(
                f"Warning: no c1 data for {size}/{dist}, falling back to heuristic",
                file=sys.stderr,
            )
            mu = max(means[i] / M_used[i] for i in range(n)) / 0.95
        else:
            print(f"μ ({size}/{dist}) = {mu:.2f} req/s (from K=1 no-cache data)")

        if args.mode == "response-time":
            rt_meas = [M_used[i] / means[i] * 1000 for i in range(n)]
            rt_lower = [M_used[i] / ci_uppers[i] * 1000 for i in range(n)]
            rt_upper = [M_used[i] / ci_lowers[i] * 1000 for i in range(n)]

            rt_mmm = [
                mmm_response_time(M_used[i], means[i], mu) * 1000 for i in range(n)
            ]

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

            # y-axis ticks at nice intervals
            valid = [v for v in rt_meas + rt_mmm if math.isfinite(v)]
            if valid:
                step = nice_step(max(valid))
                ax.yaxis.set_major_locator(MultipleLocator(step))
        else:
            mmm_pred = [closed_throughput(M_used[i], mu) for i in range(n)]

            fig, ax = plt.subplots(figsize=FIGSIZE)

            ax.plot(
                M_used,
                means,
                color=RED,
                linewidth=1.5,
                marker="o",
                markersize=8,
                label="Measured ± 95% CI",
            )
            ax.errorbar(
                M_used,
                means,
                yerr=[
                    [means[i] - ci_lowers[i] for i in range(n)],
                    [ci_uppers[i] - means[i] for i in range(n)],
                ],
                fmt="none",
                color=RED,
                capsize=4,
                capthick=1.5,
            )

            ax.plot(
                M_used,
                mmm_pred,
                color=GREEN,
                linewidth=1.5,
                marker="s",
                markersize=8,
                label="M/M/m predicted",
            )

            ax.set_ylabel("Throughput [txns/s]")
            ax.set_title("M/M/m throughput")

            # y-axis ticks at nice intervals
            valid = [v for v in means + mmm_pred if math.isfinite(v)]
            if valid:
                step = nice_step(max(valid))
                ax.yaxis.set_major_locator(MultipleLocator(step))

        ax.set_xlabel("Concurrency level (K = m)")
        ax.set_xticks(M_used)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

        # always show plain numbers (no scientific notation, no offset)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        os.makedirs(
            os.path.dirname(f"charts/cloud/exp3-nocache/{size}/{dist}/"), exist_ok=True
        )
        suffix = "response-time" if args.mode == "response-time" else "throughput"
        out_path = f"charts/cloud/exp3-nocache/{size}/{dist}/mmm-{suffix}.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
