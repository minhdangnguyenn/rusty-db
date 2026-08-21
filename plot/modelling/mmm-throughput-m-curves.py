#!/usr/bin/env python3
"""Closed M/M/m curves X(K) = min(K, m) * mu for m = 1..5, vs measured.

Shows that measured throughput grows past every fixed-m saturation
ceiling, proving the real cluster serves reads faster than m * mu_hat.
"""

import csv
import glob
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

NOCACHE_DIR = os.path.join(PROJECT_ROOT, "csv", "p2", "exp3-no-cache")
OUT_DIR = os.path.join(PROJECT_ROOT, "charts", "p2", "modelling")
os.makedirs(OUT_DIR, exist_ok=True)

M_VALUES = [1, 2, 3, 4, 5]
COLORS = {1: "#7B1FA2", 2: "#E91E63", 3: "#E67E22", 4: "#9C27B0", 5: "#388E3C"}
K_SMOOTH = list(range(1, 65))


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


def closed_mmm_curve(m, mu):
    """X(K) = min(K, m) * mu for K = 1..64."""
    return [min(k, m) * mu for k in K_SMOOTH]


def plot_one(size, dist):
    mu = estimate_mu(size, dist)
    if mu is None:
        return
    measured = load_measured(size, dist)
    if not measured:
        return

    ks = sorted(measured.keys())
    m_vals = [measured[k] for k in ks]

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)

    # M/M/m saturation curves (one per m)
    for m_val in M_VALUES:
        curve = closed_mmm_curve(m_val, mu)
        ax.plot(K_SMOOTH, curve, "-", color=COLORS[m_val], linewidth=1.8,
                alpha=0.85, label=f"M/M/m (m={m_val}, saturates at {m_val}·μ̂={m_val*mu:.0f})")
        # Mark the saturation point
        ax.plot([m_val], [m_val * mu], "o", color=COLORS[m_val], markersize=5)

    # Measured
    ax.plot(ks, m_vals, "D-", color="#1976D2", linewidth=2.5, markersize=8,
            label="Measured (benchmark)", zorder=6)
    for k, v in zip(ks, m_vals):
        ax.annotate(f"{v:.0f}", xy=(k, v), xytext=(0, 12),
                    textcoords="offset points", fontsize=8,
                    color="#1976D2", fontweight="bold", ha="center")

    # Shade region above the m=5 ceiling
    ceiling5 = 5 * mu
    ax.axhline(ceiling5, color="#388E3C", alpha=0.35, linestyle="--", linewidth=1.2)
    ymax = max(m_vals) * 1.15
    ax.fill_between([ks[0], ks[-1]], ceiling5, ymax,
                    alpha=0.08, color="#388E3C",
                    label=f"Region above m=5 ceiling ({ceiling5:.0f})")

    # Annotate the crossing: measured above ALL model curves
    excess = m_vals[-1] / ceiling5
    ax.annotate(
        f"Measured at K={ks[-1]} = {m_vals[-1]:.0f}\n"
        f"= {excess:.2f} × the m=5 ceiling ({ceiling5:.0f})\n"
        f"→ cluster serves reads faster than 5·μ̂",
        xy=(ks[-1], m_vals[-1]),
        xytext=(ks[-1] * 0.42, m_vals[-1] * 0.8),
        fontsize=9, color="#1976D2", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E3F2FD", edgecolor="#1976D2"),
        arrowprops=dict(arrowstyle="->", color="#1976D2", lw=1.5),
    )

    ax.set_xlabel("Concurrency (K)", fontsize=11)
    ax.set_ylabel("Throughput (txns/s)", fontsize=11)
    ax.set_title(
        f"Closed M/M/m: X(K) = min(K, m)·μ̂ for m = 1..5 — {size}/{dist} no-cache\n"
        f"μ̂ = {mu:.0f} req/s (from K=1)",
        fontsize=12, fontweight="bold",
    )
    ax.legend(fontsize=8, loc="upper left")
    ax.set_xlim(0, 68)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    fname = os.path.join(OUT_DIR, f"mmm-throughput-m-curves-{size}-{dist}.png")
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {fname}")

    # Print table
    print(f"\n  {size}/{dist} no-cache (μ̂={mu:.0f} req/s):")
    print(f"  {'K':>4} | {'Measured':>10} | " + " | ".join(
        f"{'m='+str(m):>9}" for m in M_VALUES) + " | best m")
    print(f"  {'-'*4}-+-{'-'*10}-+-" + "-+-".join("-" * 9 for _ in M_VALUES) + "-+----------")
    for k, v in zip(ks, m_vals):
        preds = [min(k, m) * mu for m in M_VALUES]
        best_m = min(range(1, 6), key=lambda m: abs(min(k, m) * mu - v))
        row = f"  {k:4d} | {v:10.0f} | " + " | ".join(f"{p:9.0f}" for p in preds)
        print(row + f" | m={best_m}")


if __name__ == "__main__":
    for size in ["l", "s"]:
        for dist in ["uniform", "zipf"]:
            plot_one(size, dist)
    print("\nDone.")
