"""
This file is having error, it should be adjusted
"""

import glob
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (
    CC_LEVELS,
    FIGSIZE,
    GREEN,
    RED,
    M,
    data_dir_for,
    grid_style,
    legend_pos,
    load_csv,
    mean_ci,
)

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
    """Estimate service rate from K=1 no-cache runs."""

    # Actual structure:
    # csv/cloud/exp3-no-cache/c1/l/uniform/
    # csv/cloud/exp3-no-cache/c1/l/zipf/
    # csv/cloud/exp3-no-cache/c1/s/uniform/
    # csv/cloud/exp3-no-cache/c1/s/zipf/

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

    mean_service_time = sum(1.0 / t for t in throughputs) / len(throughputs)

    return 1.0 / mean_service_time


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_measured(size, dist):
    """Load measured cached throughput with 95% CI."""

    means = []
    ci_lo = []
    ci_hi = []

    for label in CC_LEVELS:
        data_dir = data_dir_for(
            label,
            size,
            dist,
        )

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
    """Load measured no-cache throughput for c4..c64."""

    means = []

    for label in NOCACHE_LEVELS:
        # Actual structure:
        # csv/p2/exp3-nocache/c4/l/uniform/
        # csv/p2/exp3-nocache/c8/l/uniform/
        # ...

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

        m, _, _ = mean_ci(throughputs)
        means.append(m)

    return means


def response_times(means, ci_lo, ci_hi, mu):
    """Compute cached measured and M/M/m response times."""

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


def response_times_no_cache(no_cache_means):
    """Compute measured no-cache response times."""

    ks = M[: len(no_cache_means)]

    rt_no_cache = [k / tp * 1000.0 for k, tp in zip(ks, no_cache_means)]

    return ks, rt_no_cache


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def nice_step(max_val, target_bins=10):
    if max_val <= 0:
        return 1.0

    step = max_val / target_bins
    exp = 10 ** math.floor(math.log10(step))

    return round(step / exp) * exp


def add_measured(ax, ks, rt_meas, rt_lo, rt_hi):
    ax.plot(
        ks,
        rt_meas,
        color=RED,
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
        color=RED,
        capsize=4,
        capthick=1.5,
    )


def add_predicted(ax, ks, rt_mmm):
    ax.plot(
        ks,
        rt_mmm,
        color=GREEN,
        marker="s",
        label="M/M/m",
        **LINE_STYLE,
    )


def add_no_cache(ax, ks, rt_no_cache):
    ax.plot(
        ks,
        rt_no_cache,
        color="black",
        marker="^",
        label="No cache",
        **LINE_STYLE,
    )


def add_break_marks(ax_top, ax_bot):
    d = 0.015
    kw = {
        "color": "k",
        "clip_on": False,
    }

    ax_bot.plot(
        (-d, +d),
        (1 - d, 1 + d),
        transform=ax_bot.transAxes,
        **kw,
    )

    ax_bot.plot(
        (-d, +d),
        (1 + d, 1 - d),
        transform=ax_bot.transAxes,
        **kw,
    )

    ax_top.plot(
        (-d, +d),
        (-d, +d),
        transform=ax_top.transAxes,
        **kw,
    )

    ax_top.plot(
        (-d, +d),
        (-d - d, -d + d),
        transform=ax_top.transAxes,
        **kw,
    )


def find_break(all_vals):
    """Find the largest ratio gap in sorted values."""

    best_ratio = 0
    gap_idx = 0

    for i in range(1, len(all_vals)):
        if all_vals[i - 1] > 0:
            ratio = all_vals[i] / all_vals[i - 1]

            if ratio > best_ratio:
                best_ratio = ratio
                gap_idx = i

    return (
        all_vals[gap_idx - 1] * 1.15,
        all_vals[gap_idx] * 0.85,
    )


def format_axes(
    ax,
    ks,
    valid_vals,
    title="M/M/m response time",
):
    ax.set_title(title)
    ax.set_xlabel("Concurrency level (K = m)")
    ax.set_xticks(ks)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    ax.yaxis.set_major_locator(MultipleLocator(nice_step(max(valid_vals))))

    ax.ticklabel_format(
        axis="y",
        style="plain",
        useOffset=False,
    )

    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)


def plot_single(
    ks,
    rt_meas,
    rt_lo,
    rt_hi,
    rt_mmm,
    rt_no_cache,
    valid_vals,
):
    fig, ax = plt.subplots(figsize=FIGSIZE)

    add_measured(
        ax,
        ks,
        rt_meas,
        rt_lo,
        rt_hi,
    )

    add_predicted(
        ax,
        ks,
        rt_mmm,
    )

    add_no_cache(
        ax,
        ks,
        rt_no_cache,
    )

    format_axes(
        ax,
        ks,
        valid_vals,
    )

    ax.set_ylabel("Response time [ms]")

    plt.tight_layout()

    return fig


def plot_broken(
    ks,
    rt_meas,
    rt_lo,
    rt_hi,
    rt_mmm,
    rt_no_cache,
    break_low,
    break_high,
    y_max,
    finite_lower,
):
    fig, (ax_top, ax_bot) = plt.subplots(
        2,
        1,
        sharex=True,
        gridspec_kw={
            "height_ratios": [1, 1],
            "hspace": 0.1,
        },
        figsize=(
            FIGSIZE[0],
            FIGSIZE[1] * 2,
        ),
    )

    # ---------------------------------------------------------------
    # Bottom
    # ---------------------------------------------------------------

    add_measured(
        ax_bot,
        ks,
        rt_meas,
        rt_lo,
        rt_hi,
    )

    add_predicted(
        ax_bot,
        ks,
        rt_mmm,
    )

    add_no_cache(
        ax_bot,
        ks,
        rt_no_cache,
    )

    ax_bot.set_ylim(
        0,
        break_low,
    )

    valid_bot = [v for v in finite_lower if v <= break_low]

    if valid_bot:
        ax_bot.yaxis.set_major_locator(MultipleLocator(nice_step(max(valid_bot))))

    ax_bot.ticklabel_format(
        axis="y",
        style="plain",
        useOffset=False,
    )

    ax_bot.grid(True, **grid_style)
    ax_bot.spines["top"].set_visible(False)
    ax_bot.tick_params(top=False)

    ax_bot.set_xlabel("Concurrency level (K = m)")
    ax_bot.set_xticks(ks)
    ax_bot.legend(**legend_pos)

    # ---------------------------------------------------------------
    # Top
    # ---------------------------------------------------------------

    add_measured(
        ax_top,
        ks,
        rt_meas,
        rt_lo,
        rt_hi,
    )

    add_predicted(
        ax_top,
        ks,
        rt_mmm,
    )

    add_no_cache(
        ax_top,
        ks,
        rt_no_cache,
    )

    ax_top.set_ylim(
        break_high,
        y_max,
    )

    ax_top.yaxis.set_major_locator(MultipleLocator(nice_step(y_max - break_high)))

    ax_top.set_title("M/M/m response time")

    ax_top.ticklabel_format(
        axis="y",
        style="plain",
        useOffset=False,
    )

    ax_top.grid(True, **grid_style)
    ax_top.spines["bottom"].set_visible(False)
    ax_top.tick_params(bottom=False)

    ax_top.legend(**legend_pos)

    # ---------------------------------------------------------------

    add_break_marks(
        ax_top,
        ax_bot,
    )

    fig.subplots_adjust(
        left=0.12,
        right=0.85,
        top=0.93,
        bottom=0.15,
    )

    fig.text(
        0.05,
        0.5,
        "Response time [ms]",
        va="center",
        rotation="vertical",
        fontsize=11,
    )

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

        no_cache_means = load_no_cache(
            size,
            dist,
        )

        if len(no_cache_means) != len(means):
            print(
                f"Warning: different number of points "
                f"for {size}/{dist}: "
                f"cached={len(means)}, "
                f"no-cache={len(no_cache_means)}",
                file=sys.stderr,
            )
            continue

        # ---------------------------------------------------------------
        # Estimate mu from K=1 no-cache
        # ---------------------------------------------------------------

        mu = estimate_mu(
            size,
            dist,
        )

        if mu is None:
            print(
                f"Error: no c1 data for {size}/{dist}, skipping",
                file=sys.stderr,
            )
            continue

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

        _, rt_no_cache = response_times_no_cache(no_cache_means)

        # ---------------------------------------------------------------
        # Determine axis range
        # ---------------------------------------------------------------

        finite_meas = [v for v in rt_meas if math.isfinite(v)]

        finite_mmm = [v for v in rt_mmm if math.isfinite(v)]

        finite_no_cache = [v for v in rt_no_cache if math.isfinite(v)]

        all_vals = sorted(set(finite_meas + finite_mmm + finite_no_cache))

        if not all_vals:
            continue

        max_meas = max(finite_meas) if finite_meas else 0

        max_mmm = max(finite_mmm) if finite_mmm else 0

        max_no_cache = max(finite_no_cache) if finite_no_cache else 0

        # ---------------------------------------------------------------
        # Broken-axis decision
        #
        # Normally response time measured and predicted should be
        # reasonably close. Include no-cache in the range as well.
        # ---------------------------------------------------------------

        max_upper = max(
            max_meas,
            max_no_cache,
        )

        max_lower = max_mmm

        if max_upper > 0 and max_lower > 0 and max_upper > 5 * max_lower:
            break_low, break_high = find_break(all_vals)

            fig = plot_broken(
                ks,
                rt_meas,
                rt_lo,
                rt_hi,
                rt_mmm,
                rt_no_cache,
                break_low,
                break_high,
                max_upper * 1.1,
                finite_mmm + finite_meas + finite_no_cache,
            )

        else:
            fig = plot_single(
                ks,
                rt_meas,
                rt_lo,
                rt_hi,
                rt_mmm,
                rt_no_cache,
                all_vals,
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
