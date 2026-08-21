#!/usr/bin/env python3
"""Clear two-panel figure: measured vs M/M/m models.

Panel 1: Measured vs M/M/m (m=K) — shows over-prediction at high K
Panel 2: Measured vs M/M/m (m=5) — shows under-prediction at high K

Each panel has only 2 lines for maximum clarity.
"""

import csv
import glob
import math
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

FACT = [math.factorial(n) for n in range(65)]

NOCACHE_DIR = os.path.join(PROJECT_ROOT, "csv", "p2", "exp3-no-cache")
OUT_DIR = os.path.join(PROJECT_ROOT, "charts", "p2", "modelling")
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# M/M/m helpers
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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def estimate_mu(size, dist):
    pattern = os.path.join(
        NOCACHE_DIR, "c1", size, dist, "**",
        "exp3-nocache-c1-*-summary.csv",
    )
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        return None
    tps = [float(next(csv.DictReader(open(f)))["throughput"]) for f in files]
    return len(tps) / sum(1.0 / t for t in tps)


def load_measured(size, dist):
    pattern = os.path.join(
        NOCACHE_DIR, "c*", size, dist, "*",
        "exp3-nocache-*-*-summary.csv",
    )
    data = {}
    for p in glob.glob(pattern):
        with open(p) as f:
            for row in csv.DictReader(f):
                k = int(row["concurrency"])
                t = float(row["throughput"])
                data.setdefault(k, []).append(t)
    return {k: sum(v) / len(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Plot: one clear figure per config, 2 subplots side by side
# ---------------------------------------------------------------------------

def plot_one(size, dist):
    mu = estimate_mu(size, dist)
    if mu is None:
        return
    measured = load_measured(size, dist)
    if not measured:
        return

    ks = sorted(measured.keys())
    m_vals = [measured[k] for k in ks]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)

    # ── Panel 1: Measured vs M/M/m m=K ──────────────────────────────
    mmm_mk = [closed_throughput(k, mu) for k in ks]

    ax1.plot(ks, m_vals, "o-", color="#1976D2", linewidth=2.5, markersize=8,
             label="Measured (from benchmark)", zorder=5)
    ax1.plot(ks, mmm_mk, "s--", color="#D32F2F", linewidth=2, markersize=7,
             label="M/M/m (m = K)", zorder=4)

    # Shade the gap
    ax1.fill_between(ks, m_vals, mmm_mk, alpha=0.12, color="#D32F2F")

    # Annotate the gap at K=64
    gap_hi = mmm_mk[-1]
    gap_lo = m_vals[-1]
    ax1.annotate(
        f"Over-predicts\nby {gap_hi/gap_lo:.1f}×",
        xy=(ks[-1], (gap_hi + gap_lo) / 2),
        xytext=(ks[-1] * 0.6, gap_hi * 0.85),
        fontsize=9, color="#D32F2F", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#D32F2F", lw=1.5),
    )

    ax1.set_title(
        f"Panel A: M/M/m assumes m = K servers\n"
        f"({size}/{dist} no-cache, μ̂ = {mu:.0f} req/s)",
        fontsize=11, fontweight="bold",
    )
    ax1.set_xlabel("Concurrency (K)", fontsize=10)
    ax1.set_ylabel("Throughput (txns/s)", fontsize=10)
    ax1.legend(fontsize=9, loc="upper left")
    ax1.set_xlim(left=0)
    ax1.set_ylim(bottom=0)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: Measured vs M/M/m m=5 ──────────────────────────────
    mmm_m5 = [closed_throughput(5, mu) for _ in ks]

    ax2.plot(ks, m_vals, "o-", color="#1976D2", linewidth=2.5, markersize=8,
             label="Measured (from benchmark)", zorder=5)
    ax2.plot(ks, mmm_m5, "s--", color="#388E3C", linewidth=2, markersize=7,
             label="M/M/m (m = 5)", zorder=4)

    # Shade the gap
    ax2.fill_between(ks, m_vals, mmm_m5, alpha=0.12, color="#388E3C")

    # Annotate the gap at K=64
    ceiling = 5 * mu
    ax2.axhline(ceiling, color="#388E3C", alpha=0.3, linestyle="-.", linewidth=1)
    ax2.text(ks[-1] * 1.02, ceiling, f"5·μ̂ = {ceiling:.0f}",
             fontsize=8, color="#388E3C", va="center")

    gap_hi2 = m_vals[-1]
    gap_lo2 = mmm_m5[-1]
    ax2.annotate(
        f"Under-predicts\nby {gap_hi2/gap_lo2:.1f}×",
        xy=(ks[-1], (gap_hi2 + gap_lo2) / 2),
        xytext=(ks[-1] * 0.6, gap_lo2 * 0.5),
        fontsize=9, color="#388E3C", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#388E3C", lw=1.5),
    )

    ax2.set_title(
        f"Panel B: M/M/m assumes m = 5 servers\n"
        f"({size}/{dist} no-cache, μ̂ = {mu:.0f} req/s)",
        fontsize=11, fontweight="bold",
    )
    ax2.set_xlabel("Concurrency (K)", fontsize=10)
    ax2.set_ylabel("Throughput (txns/s)", fontsize=10)
    ax2.legend(fontsize=9, loc="upper left")
    ax2.set_xlim(left=0)
    ax2.set_ylim(bottom=0)
    ax2.grid(True, alpha=0.3)

    fig.suptitle(
        f"M/M/m Model Validation — {size}/{dist} no-cache",
        fontsize=13, fontweight="bold", y=1.02,
    )
    fig.tight_layout()

    fname = os.path.join(OUT_DIR, f"mmm-throughput-vary-m-{size}-{dist}.png")
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {fname}")


if __name__ == "__main__":
    for size in ["l", "s"]:
        for dist in ["uniform", "zipf"]:
            plot_one(size, dist)
    print("Done.")
