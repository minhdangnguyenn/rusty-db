#!/usr/bin/env python3
"""Clear visualization: Measured vs M/M/m with m=5.

Shows that measured throughput exceeds the 5-node cluster ceiling,
indicating parallel read serving across all Raft replicas.
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


def plot_one(size, dist):
    mu = estimate_mu(size, dist)
    if mu is None:
        return
    measured = load_measured(size, dist)
    if not measured:
        return

    ks = sorted(measured.keys())
    m_vals = [measured[k] for k in ks]
    mmm_m5 = [closed_throughput(5, mu) for _ in ks]
    ceiling = 5 * mu

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)

    # M/M/m m=5 (green dashed)
    ax.plot(ks, mmm_m5, "s--", color="#388E3C", linewidth=2, markersize=7,
            label=f"M/M/m (m=5, μ̂={mu:.0f})", zorder=4)

    # Saturation ceiling
    ax.axhline(ceiling, color="#388E3C", alpha=0.3, linestyle="-.", linewidth=1.5)
    ax.text(ks[-1] * 1.02, ceiling + ceiling * 0.03,
            f"Ceiling = 5 × μ̂ = {ceiling:.0f} txns/s",
            fontsize=9, color="#388E3C", fontweight="bold", va="bottom")

    # Measured (blue solid, thick)
    ax.plot(ks, m_vals, "o-", color="#1976D2", linewidth=2.5, markersize=8,
            label="Measured (benchmark)", zorder=5)

    # Annotate each measured point with value
    for k, v in zip(ks, m_vals):
        ax.annotate(f"{v:.0f}", xy=(k, v), xytext=(0, 10),
                    textcoords="offset points", fontsize=8,
                    color="#1976D2", fontweight="bold", ha="center")

    # Shade the "excess" region (measured above ceiling)
    ax.fill_between(ks, ceiling, m_vals,
                    where=[v > ceiling for v in m_vals],
                    alpha=0.15, color="#1976D2",
                    label="Excess beyond 5·μ̂ ceiling")

    # Annotate the excess at K=64
    if m_vals[-1] > ceiling:
        excess = m_vals[-1] / ceiling
        ax.annotate(
            f"Measured = {m_vals[-1]:.0f}\n"
            f"= {excess:.2f} × ceiling\n"
            f"({m_vals[-1] - ceiling:.0f} above 5·μ̂)",
            xy=(ks[-1], m_vals[-1]),
            xytext=(ks[-1] * 0.55, m_vals[-1] * 0.85),
            fontsize=9, color="#1976D2", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#E3F2FD", edgecolor="#1976D2"),
            arrowprops=dict(arrowstyle="->", color="#1976D2", lw=1.5),
        )

    ax.set_xlabel("Concurrency (K)", fontsize=11)
    ax.set_ylabel("Throughput (txns/s)", fontsize=11)
    ax.set_title(
        f"M/M/m with m=5 vs Measured — {size}/{dist} no-cache\n"
        f"5-node toyDB cluster, μ̂ = {mu:.0f} req/s",
        fontsize=12, fontweight="bold",
    )
    ax.legend(fontsize=9, loc="upper left")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fname = os.path.join(OUT_DIR, f"mmm-throughput-m5-{size}-{dist}.png")
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {fname}")


if __name__ == "__main__":
    for size in ["l", "s"]:
        for dist in ["uniform", "zipf"]:
            plot_one(size, dist)
    print("Done.")
