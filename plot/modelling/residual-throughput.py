import csv
import glob
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import (  # pyright: ignore[reportMissingImports]
    BLUE,
    FIGSIZE,
    RED,
    grid_style,
)

FACT = [math.factorial(n) for n in range(65)]

NOCACHE_DIR = "csv/p2/exp3-no-cache"
CACHE_DIR = "csv/p2/exp3"

LEVELS = ["c4", "c8", "c16", "c32", "c64"]
K_VALUES = [4, 8, 16, 32, 64]

OUT_DIR = "charts/p2/modelling/"


# ---------------------------------------------------------------------------
# M/M/m helpers (mirror plot/modelling/mmm-throughput.py)
# ---------------------------------------------------------------------------


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
# Data loading
# ---------------------------------------------------------------------------


def load_mean_throughput(files):
    if not files:
        return None
    tps = []
    for f in files:
        r = next(csv.DictReader(open(f)))
        tps.append(float(r["throughput"]))
    return sum(tps) / len(tps)


def mean_measured_over_k(size: str, dist: str, cached: bool):
    means = []
    for label in LEVELS:
        if cached:
            files = sorted(glob.glob(
                os.path.join(CACHE_DIR, label, size, dist, "**",
                             f"exp3-{label}-{size}-{dist}-*-summary.csv"),
                recursive=True))
        else:
            files = sorted(glob.glob(
                os.path.join(NOCACHE_DIR, label, size, dist, "**",
                             f"exp3-nocache-{label}-{size}-{dist}-*-summary.csv"),
                recursive=True))
        means.append(load_mean_throughput(files))
    return means


def estimate_mu_from_k1(size: str, dist: str):
    files = sorted(glob.glob(
        os.path.join(NOCACHE_DIR, "c1", size, dist, "**",
                     "exp3-nocache-c1-*-summary.csv"),
        recursive=True))
    if not files:
        return None
    tps = [float(next(csv.DictReader(open(f)))["throughput"]) for f in files]
    service_times = [1.0 / t for t in tps]
    return 1.0 / (sum(service_times) / len(service_times))


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def fmt_ratio(r):
    if r >= 1:
        if r >= 100:
            return f"{r:.0f}×"
        if r >= 10:
            return f"{r:.1f}×"
        return f"{r:.2f}×"
    return f"÷{1 / r:.0f}"


def add_curve(ax, ks, ratios, label, color, marker, linestyle="-", annotate=True):
    pts = [(k, r) for k, r in zip(ks, ratios) if r is not None and r > 0]
    if not pts:
        return
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, marker=marker, linewidth=1.6, markersize=9,
            linestyle=linestyle, label=label)

    for k, r in pts:
        if annotate and (r > 10 or r < 0.01):
            ax.annotate(
                fmt_ratio(r),
                xy=(k, r),
                xytext=(7, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=8,
                color=color,
                clip_on=False,
            )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    combos = [("l", "uniform"), ("l", "zipf"), ("s", "uniform"), ("s", "zipf")]

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(FIGSIZE[0] * 1.4, FIGSIZE[1] * 2.2),
    )
    fig.suptitle("M/M/m ÷ measured throughput ratio (log scale)", fontsize=13,
                 y=0.995)

    print(f"{'size':>4} {'dist':>7} | {'variant':>8} | "
          + " | ".join(f"K={k:>2}" for k in K_VALUES))
    print("-" * 72)

    for ax, (size, dist) in zip(axes.flat, combos):
        mu = estimate_mu_from_k1(size, dist)
        if mu is None:
            ax.text(0.5, 0.5, "(no K=1 no-cache data)",
                    ha="center", va="center", transform=ax.transAxes)
            ax.set_title(f"{size}/{dist}")
            continue

        meas_cache = mean_measured_over_k(size, dist, cached=True)
        meas_nc = mean_measured_over_k(size, dist, cached=False)

        mmm_pred = [closed_throughput(k, mu) for k in K_VALUES]

        ratio_cache = [(p / m) if (m and p) else None
                       for m, p in zip(meas_cache, mmm_pred)]
        ratio_nc = [(p / m) if (m and p) else None
                    for m, p in zip(meas_nc, mmm_pred)]

        add_curve(ax, K_VALUES, ratio_cache,
                  label="cache", color=BLUE, marker="o", linestyle="-")
        add_curve(ax, K_VALUES, ratio_nc,
                  label="no-cache", color=RED, marker="^", linestyle="--")

        ax.axhline(1.0, color="black", linewidth=0.8, linestyle=":",
                   label="perfect fit")

        ax.set_title(f"{size}/{dist}  (μ̂={mu:,.0f}/s)", fontsize=11)
        ax.set_xlabel("Concurrency level (K = m)")
        ax.set_xticks(K_VALUES)
        ax.set_xticklabels([str(k) for k in K_VALUES])
        ax.set_xlim(left=0)
        ax.set_yscale("log")
        ax.set_ylim(0.0003, 10)
        ax.grid(True, which="both", **grid_style)
        ax.legend(loc="lower left", fontsize=9, framealpha=0.9)

        def fmt_row(variant, ratios):
            cells = []
            for r in ratios:
                if r is None:
                    cells.append("     -")
                elif r >= 1:
                    cells.append(f"{r:>6.1f}")
                else:
                    cells.append(f"÷{1 / r:>4.0f} ")
            return f"{size:>4} {dist:>7} | {variant:>8} | " + " | ".join(cells)

        print(fmt_row("cache", ratio_cache))
        print(fmt_row("no-cache", ratio_nc))

    for ax in axes[:, 0]:
        ax.set_ylabel("M/M/m ÷ measured  (log scale)")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = os.path.join(OUT_DIR, "residual-throughput.png")
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"\nSaved to {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
