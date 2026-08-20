import glob
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import LogFormatterMathtext, LogLocator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (
    BLUE,
    CC_LEVELS,
    FIGSIZE,
    GREEN,
    RED,
    M,
    grid_style,
    legend_pos,
    load_csv,
    mean_ci,
)

MEASURED_DIR = "csv/p2/exp3"


def data_dir_for(label: str, size: str, dist: str):
    return f"{MEASURED_DIR}/{label}/{size}/{dist}"


FACT = [math.factorial(n) for n in range(65)]

NOCACHE_DIR = "csv/p2/exp3-no-cache"
NOCACHE_LEVELS = ["c4", "c8", "c16", "c32", "c64"]

OUT_DIR = "charts/p2/modelling/"

LINE_STYLE = {"linewidth": 1.5, "markersize": 8}


# ---------------------------------------------------------------------------
# M/M/m model helpers
# ---------------------------------------------------------------------------


def response_time_mmm(m, lam, mu):
    """Mean response time for a closed M/M/m queue."""
    p = min(lam / (m * mu), 0.9999)
    mp = m * p
    p0 = 1.0 / (
        1 + sum(mp**n / FACT[n] for n in range(1, m)) + mp**m / (FACT[m] * (1 - p))
    )
    q = mp**m / (FACT[m] * (1 - p)) * p0
    return (1.0 / mu) * (1.0 + q / (m * (1 - p)))


def closed_throughput(m, mu):
    """Fixed-point throughput for closed M/M/m via bisection."""
    lo, hi = 0.0, m * mu * 0.99999

    for _ in range(200):
        mid = (lo + hi) / 2.0
        er = response_time_mmm(m, mid, mu)

        if er == float("inf") or mid > m / er:
            hi = mid
        else:
            lo = mid

    return (lo + hi) / 2.0


def estimate_mu(size, dist):
    """Estimate mu and its 95% CI from K=1 no-cache runs.

    Returns (mu, mu_ci_lo, mu_ci_hi).
    """
    data_dir = f"{NOCACHE_DIR}/c1/{size}/{dist}"

    csvs = sorted(
        glob.glob(
            os.path.join(data_dir, "**/*.csv"),
            recursive=True,
        )
    )
    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]

    if not csvs:
        return None

    runs = [load_csv(f) for f in csvs]

    throughputs = [float(r[-1]["txns"]) / float(r[-1]["time_s"]) for r in runs]

    service_times = [1.0 / t for t in throughputs]
    mean_st = sum(service_times) / len(service_times)

    mu = 1.0 / mean_st

    if len(service_times) >= 2:
        var_st = sum((s - mean_st) ** 2 for s in service_times) / (
            len(service_times) - 1
        )
        std_st = math.sqrt(var_st)
        n = len(service_times)
        t_crit = 2.776 if n == 5 else (3.182 if n == 4 else 1.96)
        half_st = t_crit * std_st / math.sqrt(n)

        mu_lo = 1.0 / (mean_st + half_st)
        mu_hi = 1.0 / (mean_st - half_st)
    else:
        mu_lo = mu_hi = mu

    return mu, mu_lo, mu_hi


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_measured(size, dist):
    """Load measured cached throughput with 95% CI."""
    means, ci_lo, ci_hi = [], [], []

    for label in CC_LEVELS:
        data_dir = data_dir_for(label, size, dist)

        csvs = sorted(
            glob.glob(
                os.path.join(data_dir, "**/*.csv"),
                recursive=True,
            )
        )

        csvs = [f for f in csvs if "summary" not in f and "avg" not in f]

        if not csvs:
            continue

        runs = [load_csv(f) for f in csvs]

        throughputs = [float(r[-1]["txns"]) / float(r[-1]["time_s"]) for r in runs]

        m, lo, hi = mean_ci(throughputs)

        means.append(m)
        ci_lo.append(lo)
        ci_hi.append(hi)

    return means, ci_lo, ci_hi


def load_no_cache(size, dist):
    """Load measured no-cache throughput with 95% CI for c4..c64."""
    means, ci_lo, ci_hi = [], [], []

    for label in NOCACHE_LEVELS:
        data_dir = f"{NOCACHE_DIR}/{label}/{size}/{dist}"

        csvs = sorted(
            glob.glob(
                os.path.join(data_dir, "**/*.csv"),
                recursive=True,
            )
        )

        csvs = [f for f in csvs if "summary" not in f and "avg" not in f]

        if not csvs:
            print(
                f"Warning: no no-cache data: {data_dir}",
                file=sys.stderr,
            )
            continue

        runs = [load_csv(f) for f in csvs]

        throughputs = [float(r[-1]["txns"]) / float(r[-1]["time_s"]) for r in runs]

        m, lo, hi = mean_ci(throughputs)

        means.append(m)
        ci_lo.append(lo)
        ci_hi.append(hi)

    return means, ci_lo, ci_hi


def response_times(means, ci_lo, ci_hi, mu):
    """Compute cached measured and M/M/m response times (ms)."""
    n = len(means)
    ks = M[:n]

    def ms(k, tp):
        return k / tp * 1000.0

    rt_meas = [ms(ks[i], means[i]) for i in range(n)]

    rt_lo = [ms(ks[i], ci_hi[i]) for i in range(n)]

    rt_hi = [ms(ks[i], ci_lo[i]) for i in range(n)]

    rt_mmm = [
        ms(
            ks[i],
            closed_throughput(ks[i], mu),
        )
        for i in range(n)
    ]

    return (
        ks,
        rt_meas,
        rt_lo,
        rt_hi,
        rt_mmm,
    )


def response_times_mmm_ci(ks, mu_lo, mu_hi):
    """Compute M/M/m response time CI bounds (ms)."""
    rt_ci_lo = [
        ks[i] / closed_throughput(ks[i], mu_hi) * 1000.0 for i in range(len(ks))
    ]
    rt_ci_hi = [
        ks[i] / closed_throughput(ks[i], mu_lo) * 1000.0 for i in range(len(ks))
    ]
    return rt_ci_lo, rt_ci_hi


def response_times_no_cache(no_cache_means, no_cache_ci_lo, no_cache_ci_hi):
    """Compute measured no-cache response times with CI (ms)."""
    ks = M[: len(no_cache_means)]

    rt_no_cache = [k / tp * 1000.0 for k, tp in zip(ks, no_cache_means)]
    rt_nc_ci_lo = [k / tp_hi * 1000.0 for k, tp_hi in zip(ks, no_cache_ci_hi)]
    rt_nc_ci_hi = [k / tp_lo * 1000.0 for k, tp_lo in zip(ks, no_cache_ci_lo)]

    return ks, rt_no_cache, rt_nc_ci_lo, rt_nc_ci_hi


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def add_measured(ax, ks, rt_meas, rt_lo, rt_hi):
    ax.plot(
        ks,
        rt_meas,
        color=BLUE,
        marker="o",
        label="Measured",
        **LINE_STYLE,
    )

    ax.errorbar(
        ks,
        rt_meas,
        yerr=[
            [rt_meas[i] - rt_lo[i] for i in range(len(ks))],
            [rt_hi[i] - rt_meas[i] for i in range(len(ks))],
        ],
        fmt="none",
        color=BLUE,
        capsize=4,
        capthick=1.5,
    )


def add_predicted(ax, ks, rt_mmm, rt_ci_lo=None, rt_ci_hi=None):
    ax.plot(
        ks,
        rt_mmm,
        color=GREEN,
        marker="s",
        label="M/M/m",
        **LINE_STYLE,
    )

    if rt_ci_lo is not None and rt_ci_hi is not None:
        ax.errorbar(
            ks,
            rt_mmm,
            yerr=[
                [rt_mmm[i] - rt_ci_lo[i] for i in range(len(ks))],
                [rt_ci_hi[i] - rt_mmm[i] for i in range(len(ks))],
            ],
            fmt="none",
            color=GREEN,
            capsize=4,
            capthick=1.5,
        )


def add_no_cache(ax, ks, rt_no_cache, rt_nc_ci_lo=None, rt_nc_ci_hi=None):
    ax.plot(
        ks,
        rt_no_cache,
        color=RED,
        marker="^",
        label="No cache",
        **LINE_STYLE,
    )

    if rt_nc_ci_lo is not None and rt_nc_ci_hi is not None:
        ax.errorbar(
            ks,
            rt_no_cache,
            yerr=[
                [rt_no_cache[i] - rt_nc_ci_lo[i] for i in range(len(ks))],
                [rt_nc_ci_hi[i] - rt_no_cache[i] for i in range(len(ks))],
            ],
            fmt="none",
            color=RED,
            capsize=4,
            capthick=1.5,
        )


def format_axes(ax, ks, title="M/M/m response time"):
    ax.set_title(title)
    ax.set_xlabel("Concurrency level (K = m)")
    ax.set_xticks(ks)
    ax.set_xlim(left=0)
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10))
    ax.set_ylabel("Response time [ms]")
    ax.legend(**legend_pos)
    ax.grid(True, which="both", **grid_style)


def plot_single(
    ks,
    rt_meas,
    rt_lo,
    rt_hi,
    rt_mmm,
    rt_mmm_ci_lo,
    rt_mmm_ci_hi,
    rt_no_cache,
    rt_nc_ci_lo,
    rt_nc_ci_hi,
):
    fig, ax = plt.subplots(figsize=FIGSIZE)

    add_measured(ax, ks, rt_meas, rt_lo, rt_hi)
    add_predicted(ax, ks, rt_mmm, rt_mmm_ci_lo, rt_mmm_ci_hi)
    add_no_cache(ax, ks, rt_no_cache, rt_nc_ci_lo, rt_nc_ci_hi)

    format_axes(ax, ks)

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    for size, dist in [
        ("l", "uniform"),
        ("l", "zipf"),
        ("s", "uniform"),
        ("s", "zipf"),
    ]:
        # ---------------------------------------------------------------
        # Cached measurements
        # ---------------------------------------------------------------

        means, ci_lo, ci_hi = load_measured(
            size,
            dist,
        )

        if not means:
            continue

        # ---------------------------------------------------------------
        # No-cache measurements
        # ---------------------------------------------------------------

        no_cache_means, no_cache_ci_lo, no_cache_ci_hi = load_no_cache(
            size,
            dist,
        )

        if len(no_cache_means) != len(means):
            print(
                f"Warning: different number of points "
                f"for {size}/{dist}: "
                f"cached={len(means)}, no-cache={len(no_cache_means)}",
                file=sys.stderr,
            )
            continue

        # ---------------------------------------------------------------
        # Estimate mu from K=1 no-cache
        # ---------------------------------------------------------------

        mu_result = estimate_mu(
            size,
            dist,
        )

        if mu_result is None:
            print(
                f"Error: no c1 data for {size}/{dist}, skipping",
                file=sys.stderr,
            )
            continue

        mu, mu_lo, mu_hi = mu_result

        print(f"({size}/{dist}) = {mu:.2f} req/s (from K=1 no-cache data)")

        # ---------------------------------------------------------------
        # Response times
        # ---------------------------------------------------------------

        (
            ks,
            rt_meas,
            rt_lo,
            rt_hi,
            rt_mmm,
        ) = response_times(
            means,
            ci_lo,
            ci_hi,
            mu,
        )

        rt_mmm_ci_lo, rt_mmm_ci_hi = response_times_mmm_ci(ks, mu_lo, mu_hi)

        _, rt_no_cache, rt_nc_ci_lo, rt_nc_ci_hi = response_times_no_cache(
            no_cache_means, no_cache_ci_lo, no_cache_ci_hi
        )

        fig = plot_single(
            ks,
            rt_meas,
            rt_lo,
            rt_hi,
            rt_mmm,
            rt_mmm_ci_lo,
            rt_mmm_ci_hi,
            rt_no_cache,
            rt_nc_ci_lo,
            rt_nc_ci_hi,
        )

        # ---------------------------------------------------------------
        # Save
        # ---------------------------------------------------------------

        os.makedirs(
            OUT_DIR,
            exist_ok=True,
        )

        out_path = f"{OUT_DIR}mmm-responsetime-{size}-{dist}.png"

        plt.savefig(
            out_path,
            dpi=300,
        )

        print(f"Saved to {out_path}")

        plt.close(fig)


if __name__ == "__main__":
    main()
