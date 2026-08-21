import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.ticker import (  # pyright: ignore[reportMissingImports]
    FuncFormatter,
    MultipleLocator,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from plot.config import (
    BLUE,
    FIGSIZE,
    GREEN,
    RED,
    grid_style,
    legend_pos,
    load_csv,
    mean_ci,
)

FACT = [math.factorial(n) for n in range(65)]

NOCACHE_DIR = "csv/p2/exp3-no-cache"
OUT_DIR = "charts/p2/modelling/"

LEVELS = ["c4", "c8", "c16", "c32", "c64"]
K_VALUES = [4, 8, 16, 32, 64]

LINE_STYLE = {
    "linewidth": 1.5,
    "markersize": 8,
}

CONFIGS = [
        ("l", "uniform"),
        ("l", "zipf"),
        ("s", "uniform"),
        ("s", "zipf"),
    ]

# ---------------------------------------------------------------------------
# M/M/m model helpers
# ---------------------------------------------------------------------------


def data_dir_for(label: str, size: str, dist: str):
    return f"csv/p2/exp3/{label}/{size}/{dist}"


def response_time_mmm(m, lam, mu):
    p = min(lam / (m * mu), 0.9999)
    mp = m * p

    p0 = 1.0 / (
        1 + sum(mp**n / FACT[n] for n in range(1, m)) + mp**m / (FACT[m] * (1 - p))
    )

    q = mp**m / (FACT[m] * (1 - p)) * p0

    return (1.0 / mu) * (1.0 + q / (m * (1 - p)))


def closed_throughput(m, mu):
    lo, hi = 0.0, m * mu * 0.99999

    for _ in range(200):
        mid = (lo + hi) / 2.0
        er = response_time_mmm(m, mid, mu)

        if er == float("inf") or mid > m / er:
            hi = mid
        else:
            lo = mid

    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def load_runs(data_dir):
    csvs = sorted(
        glob.glob(
            os.path.join(
                data_dir,
                "**/*.csv",
            ),
            recursive=True,
        )
    )

    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]

    runs = []

    for path in csvs:
        run = load_csv(path)

        if not run:
            print(
                f"Warning: empty CSV skipped: {path}",
                file=sys.stderr,
            )
            continue

        runs.append(run)

    return runs


def run_throughputs(runs):
    return [float(run[-1]["txns"]) / float(run[-1]["time_s"]) for run in runs if run]


# ---------------------------------------------------------------------------
# Service rate estimation (returns mu and its 95% CI)
# ---------------------------------------------------------------------------


def estimate_mu(size, dist):
    """Estimate mu and its 95% CI from K=1 no-cache runs.

    Returns (mu, mu_ci_lo, mu_ci_hi).
    """
    data_dir = f"{NOCACHE_DIR}/c1/{size}/{dist}"

    runs = load_runs(data_dir)

    if not runs:
        return None

    throughputs = run_throughputs(runs)

    if not throughputs:
        return None

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
# Cached measurements
# ---------------------------------------------------------------------------


def load_measured(size, dist):
    results = {}

    for label in LEVELS:
        data_dir = data_dir_for(
            label,
            size,
            dist,
        )

        runs = load_runs(data_dir)

        if not runs:
            print(
                f"Warning: no measured data: {data_dir}",
                file=sys.stderr,
            )
            continue

        throughputs = run_throughputs(runs)

        if not throughputs:
            continue

        mean, ci_lo, ci_hi = mean_ci(throughputs)

        results[label] = {
            "mean": mean,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
        }

    return results


# ---------------------------------------------------------------------------
# No-cache measurements
# ---------------------------------------------------------------------------


def load_no_cache(size, dist):
    results = {}

    for label in LEVELS:
        data_dir = f"{NOCACHE_DIR}/{label}/{size}/{dist}"

        runs = load_runs(data_dir)

        if not runs:
            print(
                f"Warning: no no-cache data: {data_dir}",
                file=sys.stderr,
            )
            continue

        throughputs = run_throughputs(runs)

        if not throughputs:
            continue

        mean, ci_lo, ci_hi = mean_ci(throughputs)

        results[label] = {
            "mean": mean,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
        }

    return results


# ---------------------------------------------------------------------------
# Align all data by concurrency level
# ---------------------------------------------------------------------------


def build_aligned_data(
    measured,
    no_cache,
):
    ks = []
    measured_means = []
    measured_ci_lo = []
    measured_ci_hi = []
    no_cache_means = []
    no_cache_ci_lo = []
    no_cache_ci_hi = []

    for label, k in zip(
        LEVELS,
        K_VALUES,
    ):
        if label not in measured:
            print(
                f"Warning: missing measured data for {label}",
                file=sys.stderr,
            )
            continue

        if label not in no_cache:
            print(
                f"Warning: missing no-cache data for {label}",
                file=sys.stderr,
            )
            continue

        ks.append(k)

        measured_means.append(measured[label]["mean"])

        measured_ci_lo.append(measured[label]["ci_lo"])

        measured_ci_hi.append(measured[label]["ci_hi"])

        no_cache_means.append(no_cache[label]["mean"])
        no_cache_ci_lo.append(no_cache[label]["ci_lo"])
        no_cache_ci_hi.append(no_cache[label]["ci_hi"])

    return (
        ks,
        measured_means,
        measured_ci_lo,
        measured_ci_hi,
        no_cache_means,
        no_cache_ci_lo,
        no_cache_ci_hi,
    )


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------


def nice_step(max_val, target_bins=10):
    if max_val <= 0:
        return 1.0

    step = max_val / target_bins
    exp = 10 ** math.floor(math.log10(step))

    return round(step / exp) * exp


def add_measured(
    ax,
    ks,
    means,
    ci_lo,
    ci_hi,
):
    ax.plot(
        ks,
        means,
        color=BLUE,
        marker="o",
        label="Measured",
        **LINE_STYLE,
    )

    ax.errorbar(
        ks,
        means,
        yerr=[
            [means[i] - ci_lo[i] for i in range(len(ks))],
            [ci_hi[i] - means[i] for i in range(len(ks))],
        ],
        fmt="none",
        color=BLUE,
        capsize=4,
        capthick=1.5,
    )


def add_no_cache(
    ax,
    ks,
    means,
    ci_lo=None,
    ci_hi=None,
):
    ax.plot(
        ks,
        means,
        color=RED,
        marker="^",
        label="No cache",
        **LINE_STYLE,
    )

    if ci_lo is not None and ci_hi is not None:
        ax.errorbar(
            ks,
            means,
            yerr=[
                [means[i] - ci_lo[i] for i in range(len(ks))],
                [ci_hi[i] - means[i] for i in range(len(ks))],
            ],
            fmt="none",
            color=RED,
            capsize=4,
            capthick=1.5,
        )


def add_predicted(
    ax,
    ks,
    mmm_pred,
    mmm_ci_lo=None,
    mmm_ci_hi=None,
):
    ax.plot(
        ks,
        mmm_pred,
        color=GREEN,
        marker="s",
        label="M/M/m",
        **LINE_STYLE,
    )

    if mmm_ci_lo is not None and mmm_ci_hi is not None:
        ax.errorbar(
            ks,
            mmm_pred,
            yerr=[
                [mmm_pred[i] - mmm_ci_lo[i] for i in range(len(ks))],
                [mmm_ci_hi[i] - mmm_pred[i] for i in range(len(ks))],
            ],
            fmt="none",
            color=GREEN,
            capsize=4,
            capthick=1.5,
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
    title="M/M/m throughput",
):
    ax.set_title(title)
    ax.set_xlabel("Concurrency level (K = m)")
    ax.set_xticks(ks)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    ax.yaxis.set_major_locator(MultipleLocator(nice_step(max(valid_vals))))

    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)


# ---------------------------------------------------------------------------
# Single plot
# ---------------------------------------------------------------------------


def plot_single(
    ks,
    means,
    ci_lo,
    ci_hi,
    mmm_pred,
    mmm_ci_lo,
    mmm_ci_hi,
    no_cache_means,
    no_cache_ci_lo,
    no_cache_ci_hi,
    valid_vals,
):
    fig, ax = plt.subplots(
        figsize=(
            FIGSIZE[0] * 1.4,
            FIGSIZE[1],
        )
    )

    add_measured(
        ax,
        ks,
        means,
        ci_lo,
        ci_hi,
    )

    add_no_cache(
        ax,
        ks,
        no_cache_means,
        no_cache_ci_lo,
        no_cache_ci_hi,
    )

    add_predicted(
        ax,
        ks,
        mmm_pred,
        mmm_ci_lo,
        mmm_ci_hi,
    )

    format_axes(
        ax,
        ks,
        valid_vals,
    )

    ax.set_ylabel("Throughput [txns/s]")

    plt.tight_layout()

    return fig


# ---------------------------------------------------------------------------
# Broken y-axis plot
# ---------------------------------------------------------------------------


def plot_broken(
    ks,
    means,
    ci_lo,
    ci_hi,
    mmm_pred,
    mmm_ci_lo,
    mmm_ci_hi,
    no_cache_means,
    no_cache_ci_lo,
    no_cache_ci_hi,
    break_low,
    break_high,
    y_max,
    finite_vals,
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
            FIGSIZE[0] * 1.4,
            FIGSIZE[1] * 2,
        ),
    )

    # Top
    add_measured(
        ax_top,
        ks,
        means,
        ci_lo,
        ci_hi,
    )

    add_no_cache(
        ax_top,
        ks,
        no_cache_means,
        no_cache_ci_lo,
        no_cache_ci_hi,
    )

    add_predicted(
        ax_top,
        ks,
        mmm_pred,
        mmm_ci_lo,
        mmm_ci_hi,
    )

    ax_top.set_ylim(
        break_high,
        y_max,
    )

    ax_top.yaxis.set_major_locator(MultipleLocator(nice_step(y_max - break_high)))

    ax_top.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax_top.set_title("M/M/m throughput")

    ax_top.grid(
        True,
        **grid_style,
    )

    ax_top.spines["bottom"].set_visible(False)

    ax_top.tick_params(bottom=False)

    ax_top.legend(**legend_pos)

    # Bottom
    add_measured(
        ax_bot,
        ks,
        means,
        ci_lo,
        ci_hi,
    )

    add_no_cache(
        ax_bot,
        ks,
        no_cache_means,
        no_cache_ci_lo,
        no_cache_ci_hi,
    )

    add_predicted(
        ax_bot,
        ks,
        mmm_pred,
        mmm_ci_lo,
        mmm_ci_hi,
    )

    ax_bot.set_ylim(
        0,
        break_low,
    )

    valid_bot = [v for v in finite_vals if v <= break_low]

    if valid_bot:
        ax_bot.yaxis.set_major_locator(MultipleLocator(nice_step(max(valid_bot))))

    ax_bot.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax_bot.grid(
        True,
        **grid_style,
    )

    ax_bot.spines["top"].set_visible(False)

    ax_bot.tick_params(top=False)

    ax_bot.set_xlabel("Concurrency level (K = m)")

    ax_bot.set_xticks(ks)

    ax_bot.legend(**legend_pos)

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
        "Throughput [txns/s]",
        va="center",
        rotation="vertical",
        fontsize=11,
    )

    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    for size, dist in CONFIGS:
        measured = load_measured(
            size,
            dist,
        )

        no_cache = load_no_cache(
            size,
            dist,
        )

        if not measured:
            continue

        if not no_cache:
            continue

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

        (
            ks,
            means,
            ci_lo,
            ci_hi,
            no_cache_means,
            no_cache_ci_lo,
            no_cache_ci_hi,
        ) = build_aligned_data(
            measured,
            no_cache,
        )

        if not ks:
            continue

        mmm_pred = [
            closed_throughput(
                k,
                mu,
            )
            for k in ks
        ]

        mmm_ci_lo = [
            closed_throughput(
                k,
                mu_lo,
            )
            for k in ks
        ]

        mmm_ci_hi = [
            closed_throughput(
                k,
                mu_hi,
            )
            for k in ks
        ]

        # Include all three curves and CI bounds
        # when determining the y-axis range.
        all_vals = sorted(
            set(
                means
                + no_cache_means
                + mmm_pred
                + ci_lo
                + ci_hi
                + no_cache_ci_lo
                + no_cache_ci_hi
                + mmm_ci_lo
                + mmm_ci_hi
            )
        )

        finite_meas = [v for v in means if math.isfinite(v)]

        finite_no_cache = [v for v in no_cache_means if math.isfinite(v)]

        finite_mmm = [v for v in mmm_pred if math.isfinite(v)]

        max_meas = max(finite_meas) if finite_meas else 0

        max_no_cache = max(finite_no_cache) if finite_no_cache else 0

        max_mmm = max(finite_mmm) if finite_mmm else 0

        max_upper = max(
            max_meas,
            max_no_cache,
            max_mmm,
        )

        # Broken axis only if measured/no-cache values are
        # much larger than the M/M/m prediction.
        if max_mmm > 0 and max_upper > 5 * max_mmm:
            break_low, break_high = find_break(all_vals)

            fig = plot_broken(
                ks,
                means,
                ci_lo,
                ci_hi,
                mmm_pred,
                mmm_ci_lo,
                mmm_ci_hi,
                no_cache_means,
                no_cache_ci_lo,
                no_cache_ci_hi,
                break_low,
                break_high,
                max_upper * 1.1,
                finite_meas + finite_no_cache + finite_mmm,
            )
        else:
            fig = plot_single(
                ks,
                means,
                ci_lo,
                ci_hi,
                mmm_pred,
                mmm_ci_lo,
                mmm_ci_hi,
                no_cache_means,
                no_cache_ci_lo,
                no_cache_ci_hi,
                all_vals,
            )

        os.makedirs(
            OUT_DIR,
            exist_ok=True,
        )

        out_path = f"{OUT_DIR}mmm-throughput-{size}-{dist}.png"

        plt.savefig(
            out_path,
            dpi=300,
            bbox_inches="tight",
        )

        print(f"Saved to {out_path}")

        plt.close(fig)


if __name__ == "__main__":
    main()
