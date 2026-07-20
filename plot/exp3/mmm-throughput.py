import glob
import math
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.ticker import FuncFormatter, MultipleLocator  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
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

NOCACHE_DIR = "csv/cloud/exp3-nocache"
OUT_DIR = "charts/cloud/exp3/"

LINE_STYLE = dict(linewidth=1.5, markersize=8)


# ---------------------------------------------------------------------------
# M/M/m model helpers
# ---------------------------------------------------------------------------

def response_time_mmm(m, lam, mu):
    p = min(lam / (m * mu), 0.9999)
    mp = m * p
    p0 = 1.0 / (
        1 + sum(mp**n / FACT[n] for n in range(1, m))
        + mp**m / (FACT[m] * (1 - p))
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


def estimate_mu(size, dist):
    data_dir = f"{NOCACHE_DIR}/{dist}/c1/{size}"
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
    if not csvs:
        return None
    runs = [load_csv(f) for f in csvs]
    throughputs = [r[-1]["txns"] / r[-1]["time_s"] for r in runs]
    mean_service_time = sum(1 / t for t in throughputs) / len(throughputs)
    return 1.0 / mean_service_time


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_measured(size, dist):
    means, ci_lo, ci_hi = [], [], []
    for label in CC_LEVELS:
        data_dir = data_dir_for(label, size, dist)
        csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
        csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
        if not csvs:
            continue
        runs = [load_csv(f) for f in csvs]
        throughputs = [r[-1]["txns"] / r[-1]["time_s"] for r in runs]
        m, lo, hi = mean_ci(throughputs)
        means.append(m)
        ci_lo.append(lo)
        ci_hi.append(hi)
    return means, ci_lo, ci_hi


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def nice_step(max_val, target_bins=10):
    if max_val <= 0:
        return 1.0
    step = max_val / target_bins
    exp = 10 ** math.floor(math.log10(step))
    return round(step / exp) * exp


def add_measured(ax, ks, means, ci_lo, ci_hi):
    ax.plot(ks, means, color=RED, marker="o", label="Measured", **LINE_STYLE)
    ax.errorbar(
        ks, means,
        yerr=[[means[i] - ci_lo[i] for i in range(len(ks))],
              [ci_hi[i] - means[i] for i in range(len(ks))]],
        fmt="none", color=RED, capsize=4, capthick=1.5,
    )


def add_predicted(ax, ks, mmm_pred):
    ax.plot(ks, mmm_pred, color=GREEN, marker="s", label="Predicted", **LINE_STYLE)


def add_break_marks(ax_top, ax_bot):
    d = 0.015
    kw = dict(color="k", clip_on=False)
    ax_bot.plot((-d, +d), (1 - d, 1 + d), transform=ax_bot.transAxes, **kw)
    ax_bot.plot((-d, +d), (1 + d, 1 - d), transform=ax_bot.transAxes, **kw)
    ax_top.plot((-d, +d), (-d, +d), transform=ax_top.transAxes, **kw)
    ax_top.plot((-d, +d), (-d - d, -d + d), transform=ax_top.transAxes, **kw)


def find_break(all_vals):
    best_ratio, gap_idx = 0, 0
    for i in range(1, len(all_vals)):
        if all_vals[i - 1] > 0:
            ratio = all_vals[i] / all_vals[i - 1]
            if ratio > best_ratio:
                best_ratio = ratio
                gap_idx = i
    return all_vals[gap_idx - 1] * 1.15, all_vals[gap_idx] * 0.85


def format_axes(ax, ks, valid_vals, title="M/M/m throughput"):
    ax.set_title(title)
    ax.set_xlabel("Concurrency level (K = m)")
    ax.set_xticks(ks)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(MultipleLocator(nice_step(max(valid_vals))))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.legend(**legend_pos)
    ax.grid(True, **grid_style)


def plot_single(ks, means, ci_lo, ci_hi, mmm_pred, valid_vals):
    fig, ax = plt.subplots(figsize=(FIGSIZE[0] * 1.4, FIGSIZE[1]))
    add_measured(ax, ks, means, ci_lo, ci_hi)
    add_predicted(ax, ks, mmm_pred)
    format_axes(ax, ks, valid_vals)
    ax.set_ylabel("Throughput [txns/s]")
    plt.tight_layout()
    return fig


def plot_broken(ks, means, ci_lo, ci_hi, mmm_pred, break_low, break_high, y_max, finite_meas):
    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, sharex=True,
        gridspec_kw={"height_ratios": [1, 1], "hspace": 0.1},
        figsize=(FIGSIZE[0] * 1.4, FIGSIZE[1] * 2),
    )

    # Top: measured (higher values)
    add_measured(ax_top, ks, means, ci_lo, ci_hi)
    ax_top.set_ylim(break_high, y_max)
    ax_top.yaxis.set_major_locator(MultipleLocator(nice_step(y_max - break_high)))
    ax_top.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax_top.set_title("M/M/m throughput")
    ax_top.grid(True, **grid_style)
    ax_top.spines["bottom"].set_visible(False)
    ax_top.tick_params(bottom=False)
    ax_top.legend(**legend_pos)

    # Bottom: predicted (lower values)
    add_predicted(ax_bot, ks, mmm_pred)
    ax_bot.set_ylim(0, break_low)
    valid_bot = [v for v in finite_meas if v <= break_low]
    if valid_bot:
        ax_bot.yaxis.set_major_locator(MultipleLocator(nice_step(max(valid_bot))))
    ax_bot.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax_bot.grid(True, **grid_style)
    ax_bot.spines["top"].set_visible(False)
    ax_bot.tick_params(top=False)
    ax_bot.set_xlabel("Concurrency level (K = m)")
    ax_bot.set_xticks(ks)
    ax_bot.legend(**legend_pos)

    add_break_marks(ax_top, ax_bot)
    fig.subplots_adjust(left=0.12, right=0.85, top=0.93, bottom=0.15)
    fig.text(0.05, 0.5, "Throughput [txns/s]", va="center", rotation="vertical", fontsize=11)
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
        means, ci_lo, ci_hi = load_measured(size, dist)
        if not means:
            continue

        mu = estimate_mu(size, dist)
        if mu is None:
            print(f"Warning: no c1 data for {size}/{dist}, falling back to heuristic",
                  file=sys.stderr)
            mu = max(means[i] / M[i] for i in range(len(means))) / 0.95
        else:
            print(f"({size}/{dist}) = {mu:.2f} req/s (from K=1 no-cache data)")

        ks = M[:len(means)]
        mmm_pred = [closed_throughput(ks[i], mu) for i in range(len(ks))]

        all_vals = sorted(set(means + mmm_pred))
        finite_meas = [v for v in means if math.isfinite(v)]
        finite_mmm = [v for v in mmm_pred if math.isfinite(v)]
        max_meas = max(finite_meas) if finite_meas else 0
        max_mmm = max(finite_mmm) if finite_mmm else 0

        if max_mmm > 0 and max_meas > 5 * max_mmm:
            break_low, break_high = find_break(all_vals)
            fig = plot_broken(ks, means, ci_lo, ci_hi, mmm_pred,
                              break_low, break_high, max_meas * 1.1, finite_mmm)
        else:
            fig = plot_single(ks, means, ci_lo, ci_hi, mmm_pred, all_vals)

        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = f"{OUT_DIR}mmm-throughput-{size}-{dist}.png"
        plt.savefig(out_path, dpi=300)
        print(f"Saved to {out_path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
