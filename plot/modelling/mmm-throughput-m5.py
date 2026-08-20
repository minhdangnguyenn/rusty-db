import csv
import glob
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.ticker import FuncFormatter, MultipleLocator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import BLUE, FIGSIZE, RED, grid_style, legend_pos

FACT = [math.factorial(n) for n in range(65)]

NOCACHE_DIR = "csv/p2/exp3-no-cache"

K_VALUES = [4, 8, 16, 32, 64]
OUT_DIR = "charts/p2/modelling/"


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
    files = sorted(glob.glob(
        os.path.join(NOCACHE_DIR, "c1", size, dist, "**",
                     "exp3-nocache-c1-*-summary.csv"),
        recursive=True))
    if not files:
        return None
    tps = [float(next(csv.DictReader(open(f)))["throughput"]) for f in files]
    sts = [1.0 / t for t in tps]
    return 1.0 / (sum(sts) / len(sts))


def load_measured_no_cache(size, dist):
    results = []
    for k in K_VALUES:
        c = f"c{k}"
        d = os.path.join(NOCACHE_DIR, c, size, dist)
        files = sorted(glob.glob(os.path.join(d, "**", "*-summary.csv"),
                                 recursive=True))
        if not files:
            results.append(None)
            continue
        tps = [float(next(csv.DictReader(open(f)))["throughput"]) for f in files]
        results.append(sum(tps) / len(tps))
    return results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

LINE_STYLE = {"linewidth": 1.6, "markersize": 9}





def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    combos = [("l", "uniform"), ("l", "zipf"),
              ("s", "uniform"), ("s", "zipf")]
    for size, dist in combos:
        mu = estimate_mu(size, dist)
        if mu is None:
            continue

        measured = load_measured_no_cache(size, dist)
        pred_mK = [closed_throughput(k, mu) for k in K_VALUES]
        pred_m5 = [closed_throughput(5, mu) for _ in K_VALUES]
        valid_meas = [m for m in measured if m is not None]

        fig, ax = plt.subplots(figsize=FIGSIZE)

        ax.plot(K_VALUES, measured, color=BLUE, marker="o",
                label="Measured", **LINE_STYLE)
        ax.plot(K_VALUES, pred_mK, color=RED, marker="s",
                label="M/M/m (m=K)", linestyle="--", **LINE_STYLE)
        ax.plot(K_VALUES, pred_m5, color="#4daf4a", marker="^",
                label="M/M/m (m=5)", linestyle=":", linewidth=2, markersize=9)

        ax.set_title(f"{size}/{dist} no-cache  (μ̂={mu:,.0f}/s)",
                     fontsize=12)
        ax.set_xlabel("Concurrency level (K = m)")
        ax.set_ylabel("Throughput [txns/s]")
        ax.set_xticks(K_VALUES)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.yaxis.set_major_locator(MultipleLocator(
            max(valid_meas) / 4 if valid_meas else 1000))
        ax.grid(True, **grid_style)
        ax.legend(loc="upper left", fontsize=9)

        plt.tight_layout()
        out_path = os.path.join(
            OUT_DIR, f"mmm-throughput-compare-{size}-{dist}.png")
        plt.savefig(out_path, dpi=200, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
