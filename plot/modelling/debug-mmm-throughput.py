import glob
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (
    FIGSIZE,
    GREEN,
    RED,
    grid_style,
    legend_pos,
    load_csv,
    mean_ci,
)

FACT = [math.factorial(n) for n in range(65)]

# ---------------------------------------------------------------------------
# Paths / configuration
# ---------------------------------------------------------------------------

CACHED_ROOT = "csv/p2/exp3"
NOCACHE_ROOT = "csv/p2/exp3-no-cache"

OUT_DIR = "charts/p2/modelling"

LEVELS = ["c4", "c8", "c16", "c32", "c64"]
K_VALUES = [4, 8, 16, 32, 64]

LINE_STYLE = {
    "linewidth": 1.5,
    "markersize": 8,
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def cached_data_dir(label: str, size: str, dist: str) -> str:
    return f"{CACHED_ROOT}/{label}/{size}/{dist}"


def no_cache_data_dir(label: str, size: str, dist: str) -> str:
    return f"{NOCACHE_ROOT}/{label}/{size}/{dist}"


def c1_no_cache_data_dir(size: str, dist: str) -> str:
    return f"{NOCACHE_ROOT}/c1/{size}/{dist}"


# ---------------------------------------------------------------------------
# M/M/m model
# ---------------------------------------------------------------------------


def response_time_mmm(m: int, lam: float, mu: float) -> float:
    """Mean response time for the current closed M/M/m formulation."""
    p = min(lam / (m * mu), 0.9999)
    mp = m * p

    p0 = 1.0 / (
        1.0 + sum(mp**n / FACT[n] for n in range(1, m)) + mp**m / (FACT[m] * (1.0 - p))
    )

    q = mp**m / (FACT[m] * (1.0 - p)) * p0

    return (1.0 / mu) * (1.0 + q / (m * (1.0 - p)))


def closed_throughput(m: int, mu: float) -> float:
    """Solve the current fixed-point throughput equation."""
    lo = 0.0
    hi = m * mu * 0.99999

    for _ in range(200):
        mid = (lo + hi) / 2.0
        er = response_time_mmm(m, mid, mu)

        if er == float("inf") or mid > m / er:
            hi = mid
        else:
            lo = mid

    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def load_runs(data_dir: str):
    """
    Load non-empty raw CSV runs.

    Summary files and avg.csv files are ignored.
    Empty CSVs are skipped and reported.
    """
    candidates = sorted(
        glob.glob(
            os.path.join(
                data_dir,
                "**/*.csv",
            ),
            recursive=True,
        )
    )

    candidates = [
        path for path in candidates if "summary" not in path and "avg" not in path
    ]

    valid_files = []
    runs = []

    for path in candidates:
        run = load_csv(path)

        if not run:
            print(
                f"WARNING: empty CSV skipped: {path}",
                file=sys.stderr,
            )
            continue

        valid_files.append(path)
        runs.append(run)

    return valid_files, runs


def run_throughputs(runs) -> list[float]:
    """Compute final throughput of every valid run."""
    return [float(run[-1]["txns"]) / float(run[-1]["time_s"]) for run in runs if run]


# ---------------------------------------------------------------------------
# Cached measurements
# ---------------------------------------------------------------------------


def load_measured(size: str, dist: str):
    results = {}

    print()
    print("=" * 80)
    print(f"CACHED MEASUREMENTS: size={size}, dist={dist}")
    print("=" * 80)

    for label in LEVELS:
        data_dir = cached_data_dir(
            label,
            size,
            dist,
        )

        print()
        print(f"[Measured] {label} -> {data_dir}")

        csvs, runs = load_runs(data_dir)

        print(f"  Valid CSV files: {len(csvs)}")

        if not csvs:
            print("  WARNING: no valid CSV files")
            continue

        throughputs = run_throughputs(runs)

        print("  Run throughputs: " + ", ".join(f"{x:.2f}" for x in throughputs))

        mean, ci_lo, ci_hi = mean_ci(throughputs)

        print(f"  Mean:  {mean:.2f}")
        print(f"  CI lo: {ci_lo:.2f}")
        print(f"  CI hi: {ci_hi:.2f}")

        results[label] = {
            "throughputs": throughputs,
            "mean": mean,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
        }

    return results


# ---------------------------------------------------------------------------
# No-cache measurements
# ---------------------------------------------------------------------------


def load_no_cache(size: str, dist: str):
    results = {}

    print()
    print("=" * 80)
    print(f"NO-CACHE MEASUREMENTS: size={size}, dist={dist}")
    print("=" * 80)

    for label in LEVELS:
        data_dir = no_cache_data_dir(
            label,
            size,
            dist,
        )

        print()
        print(f"[No-cache] {label} -> {data_dir}")

        csvs, runs = load_runs(data_dir)

        print(f"  Valid CSV files: {len(csvs)}")

        if not csvs:
            print("  WARNING: no valid CSV files")
            continue

        throughputs = run_throughputs(runs)

        print("  Run throughputs: " + ", ".join(f"{x:.2f}" for x in throughputs))

        mean, ci_lo, ci_hi = mean_ci(throughputs)

        print(f"  Mean:  {mean:.2f}")
        print(f"  CI lo: {ci_lo:.2f}")
        print(f"  CI hi: {ci_hi:.2f}")

        results[label] = {
            "throughputs": throughputs,
            "mean": mean,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
        }

    return results


# ---------------------------------------------------------------------------
# K=1 -> service rate
# ---------------------------------------------------------------------------


def estimate_mu(size: str, dist: str):
    data_dir = c1_no_cache_data_dir(
        size,
        dist,
    )

    print()
    print("=" * 80)
    print("SERVICE RATE ESTIMATION")
    print("=" * 80)
    print(f"K=1 path: {data_dir}")

    csvs, runs = load_runs(data_dir)

    print(f"Valid K=1 CSV files: {len(csvs)}")

    if not csvs:
        print("ERROR: no valid K=1 CSV files found")
        return None

    throughputs = run_throughputs(runs)

    print("K=1 run throughputs: " + ", ".join(f"{x:.6f}" for x in throughputs))

    arithmetic_mean = sum(throughputs) / len(throughputs)

    harmonic_mean = len(throughputs) / sum(1.0 / t for t in throughputs)

    mean_service_time = sum(1.0 / t for t in throughputs) / len(throughputs)

    mu = 1.0 / mean_service_time

    print()
    print(f"K=1 arithmetic mean throughput : {arithmetic_mean:.6f}")
    print(f"K=1 harmonic mean throughput   : {harmonic_mean:.6f}")
    print(f"Mean service time              : {mean_service_time:.12f}")
    print(f"mu                             : {mu:.6f}")

    k1_mmm = closed_throughput(
        1,
        mu,
    )

    print(f"M/M/m prediction at K=1        : {k1_mmm:.6f}")

    return mu


# ---------------------------------------------------------------------------
# Alignment
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

    for label, k in zip(
        LEVELS,
        K_VALUES,
    ):
        if label not in measured:
            print(f"ERROR: missing measured data for {label}")
            continue

        if label not in no_cache:
            print(f"ERROR: missing no-cache data for {label}")
            continue

        ks.append(k)

        measured_means.append(measured[label]["mean"])

        measured_ci_lo.append(measured[label]["ci_lo"])

        measured_ci_hi.append(measured[label]["ci_hi"])

        no_cache_means.append(no_cache[label]["mean"])

    return (
        ks,
        measured_means,
        measured_ci_lo,
        measured_ci_hi,
        no_cache_means,
    )


# ---------------------------------------------------------------------------
# Debug table
# ---------------------------------------------------------------------------


def print_comparison(
    ks,
    measured,
    no_cache,
    predicted,
):
    print()
    print("=" * 80)
    print("FINAL COMPARISON")
    print("=" * 80)

    print(f"{'K':>6}{'Measured':>18}{'No-cache':>18}{'M/M/m':>18}")

    print("-" * 80)

    for k, m, n, p in zip(
        ks,
        measured,
        no_cache,
        predicted,
    ):
        print(f"{k:>6}{m:>18.2f}{n:>18.2f}{p:>18.2f}")

    print("-" * 80)

    print()
    print("Pairwise differences:")
    print()

    for k, m, n, p in zip(
        ks,
        measured,
        no_cache,
        predicted,
    ):
        print(
            f"K={k}: "
            f"No-cache - Measured = {n - m:.2f}, "
            f"M/M/m - No-cache = {p - n:.2f}, "
            f"M/M/m - Measured = {p - m:.2f}"
        )


def print_response_time_check(
    ks,
    measured,
    no_cache,
    predicted,
):
    print()
    print("=" * 80)
    print("RESPONSE TIME SANITY CHECK")
    print("=" * 80)

    print(f"{'K':>6}{'Measured R(ms)':>20}{'No-cache R(ms)':>20}{'M/M/m R(ms)':>20}")

    print("-" * 80)

    for k, m, n, p in zip(
        ks,
        measured,
        no_cache,
        predicted,
    ):
        measured_r = k / m * 1000.0
        no_cache_r = k / n * 1000.0
        predicted_r = k / p * 1000.0

        print(f"{k:>6}{measured_r:>20.4f}{no_cache_r:>20.4f}{predicted_r:>20.4f}")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def nice_step(
    max_val: float,
    target_bins: int = 10,
):
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
        color=RED,
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
        color=RED,
        capsize=4,
        capthick=1.5,
    )


def add_no_cache(
    ax,
    ks,
    means,
):
    ax.plot(
        ks,
        means,
        color="black",
        marker="^",
        label="No cache",
        **LINE_STYLE,
    )


def add_predicted(
    ax,
    ks,
    predicted,
):
    ax.plot(
        ks,
        predicted,
        color=GREEN,
        marker="s",
        label="M/M/m",
        **LINE_STYLE,
    )


def plot_result(
    ks,
    measured,
    ci_lo,
    ci_hi,
    no_cache,
    predicted,
):
    all_values = measured + no_cache + predicted + ci_lo + ci_hi

    positive_values = [x for x in all_values if math.isfinite(x) and x > 0]

    if not positive_values:
        return None

    y_max = max(positive_values)

    fig, ax = plt.subplots(
        figsize=(
            FIGSIZE[0] * 1.4,
            FIGSIZE[1],
        )
    )

    add_measured(
        ax,
        ks,
        measured,
        ci_lo,
        ci_hi,
    )

    add_no_cache(
        ax,
        ks,
        no_cache,
    )

    add_predicted(
        ax,
        ks,
        predicted,
    )

    ax.set_title("M/M/m throughput comparison")

    ax.set_xlabel("Concurrency level (K = m)")

    ax.set_ylabel("Throughput [txns/s]")

    ax.set_xticks(ks)
    ax.set_xlim(
        0,
        max(ks) + 4,
    )

    ax.set_ylim(
        0,
        y_max * 1.15,
    )

    ax.yaxis.set_major_locator(MultipleLocator(nice_step(y_max)))

    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)

    plt.tight_layout()

    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # Start with one case while debugging.
    # Uncomment the remaining cases once the data is verified.
    EXP_CASES = [
        ("l", "uniform"),
        ("l", "zipf"),
        ("s", "uniform"),
        ("s", "zipf"),
    ]

    print()
    print("=" * 80)
    print("M/M/m DEBUG RUN")
    print("=" * 80)
    print(f"Cached root    : {CACHED_ROOT}")
    print(f"No-cache root  : {NOCACHE_ROOT}")
    print(f"Levels         : {LEVELS}")
    print(f"K values       : {K_VALUES}")

    for size, dist in EXP_CASES:
        print()
        print()
        print("#" * 80)
        print(f"# CASE: size={size}, dist={dist}")
        print("#" * 80)

        measured = load_measured(
            size,
            dist,
        )

        no_cache = load_no_cache(
            size,
            dist,
        )

        mu = estimate_mu(
            size,
            dist,
        )

        if mu is None:
            print("Skipping case because mu could not be estimated.")
            continue

        (
            ks,
            measured_means,
            measured_ci_lo,
            measured_ci_hi,
            no_cache_means,
        ) = build_aligned_data(
            measured,
            no_cache,
        )

        if not ks:
            print("No aligned data available.")
            continue

        predicted = [
            closed_throughput(
                k,
                mu,
            )
            for k in ks
        ]

        print_comparison(
            ks,
            measured_means,
            no_cache_means,
            predicted,
        )

        print_response_time_check(
            ks,
            measured_means,
            no_cache_means,
            predicted,
        )

        fig = plot_result(
            ks,
            measured_means,
            measured_ci_lo,
            measured_ci_hi,
            no_cache_means,
            predicted,
        )

        if fig is None:
            continue

        os.makedirs(
            OUT_DIR,
            exist_ok=True,
        )

        out_path = f"{OUT_DIR}/mmm-throughput-debug-{size}-{dist}.png"

        plt.savefig(
            out_path,
            dpi=300,
            bbox_inches="tight",
        )

        print()
        print(f"Saved debug plot to: {out_path}")

        plt.close(fig)


if __name__ == "__main__":
    main()
