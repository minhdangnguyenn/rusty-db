import argparse
import glob
import math
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    CC_LEVELS,  # pyright: ignore[reportAttributeAccessIssue]
    GREEN,  # pyright: ignore[reportAttributeAccessIssue]
    RED,  # pyright: ignore[reportAttributeAccessIssue]
    M,  # pyright: ignore[reportAttributeAccessIssue]
    data_dir_for,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    mean_ci,  # pyright: ignore[reportAttributeAccessIssue]
)

FIGSIZE = (14, 5)

# precompute n! for n = 0..64 used in p0 formula
FACT = [math.factorial(n) for n in range(65)]


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
    """μ = 1/E[s] where E[s] is mean response time at K=4 (least queueing).

    At K=4 with negligible queueing, observed response time E[r] ≈ E[s],
    so μ = 1 / E[s] ≈ 1 / E[r].
    E[r] = K / λ = 4 / throughput (Little's law).
    """
    data_dir = data_dir_for("c4", size, dist)
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
    k = 4
    e_s_vals = [k / tp for tp in tps]
    e_s = sum(e_s_vals) / len(e_s_vals)
    return 1.0 / e_s


def mm_m_response_time(m, lam, mu):
    # ρ = λ / (m·μ)
    p = lam / (m * mu)
    if p >= 0.9999:
        return float("inf")

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
        r = mm_m_response_time(m, mid, mu)
        if r == float("inf") or mid > m / r:
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

        for label in CC_LEVELS:
            data_dir = data_dir_for(label, size, dist)
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

        n = len(M)

        mu = estimate_mu(size, dist)
        if mu is None:
            print(
                f"Warning: no no-cache data for {size}/{dist}, "
                f"falling back to heuristic",
                file=sys.stderr,
            )
            mu = max(means[i] / M[i] for i in range(n)) / 0.95
        else:
            print(f"μ ({size}/{dist}) = {mu:.2f} req/s (from K=4 cache data)")

        if args.mode == "response-time":
            mmm_pred = [closed_throughput(M[i], mu) for i in range(n)]
            rt_meas = [M[i] / means[i] * 1000 for i in range(n)]
            rt_lower = [M[i] / ci_uppers[i] * 1000 for i in range(n)]
            rt_upper = [M[i] / ci_lowers[i] * 1000 for i in range(n)]

            rt_mmm = [M[i] / mmm_pred[i] * 1000 for i in range(n)]

            fig, ax = plt.subplots(figsize=FIGSIZE)

            ax.plot(
                M,
                rt_meas,
                color=RED,
                linewidth=1.5,
                marker="o",
                markersize=8,
                label="Measured",
            )
            ax.errorbar(
                M,
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
                M,
                rt_mmm,
                color=GREEN,
                linewidth=1.5,
                marker="s",
                markersize=8,
                label="M/M/m predicted",
            )

            ax.set_ylabel("Average response time [ms]")
            ax.set_title(f"M/M/m response time ({size}, {dist})")

            # y-axis ticks at nice intervals
            valid = [v for v in rt_meas + rt_mmm if not math.isnan(v)]
            if valid:
                step = nice_step(max(valid))
                ax.yaxis.set_major_locator(MultipleLocator(step))
        else:
            mmm_pred = [closed_throughput(M[i], mu) for i in range(n)]

            fig, ax = plt.subplots(figsize=FIGSIZE)

            ax.plot(
                M,
                means,
                color=RED,
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
                color=RED,
                capsize=4,
                capthick=1.5,
            )

            ax.plot(
                M,
                mmm_pred,
                color=GREEN,
                linewidth=1.5,
                marker="s",
                markersize=8,
                label="M/M/m predicted",
            )

            ax.set_ylabel("Throughput [txns/s]")
            ax.set_title(f"M/M/m throughput ({size}, {dist})")

            # y-axis ticks at nice intervals
            valid = [v for v in means + mmm_pred if not math.isnan(v)]
            if valid:
                step = nice_step(max(valid))
                ax.yaxis.set_major_locator(MultipleLocator(step))

        ax.set_xlabel("Number of workers (m)")
        ax.set_xticks(M)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

        # always show plain numbers (no scientific notation, no offset)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        os.makedirs(os.path.dirname(f"charts/cloud/exp3/{size}/{dist}/"), exist_ok=True)
        suffix = "response-time" if args.mode == "response-time" else "throughput"
        out_path = f"charts/cloud/exp3/{size}/{dist}/mmm-{suffix}.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
