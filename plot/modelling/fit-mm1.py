#!/usr/bin/env python3
"""Fit a closed single-server (M/M/1 + fixed delay) model to exp3 data.

The 5-node cluster is a Raft single-leader system: only the leader executes
reads, so the effective server count is m = 1.  Each read also pays a fixed
network + quorum round-trip (Z) before the leader runs the query.

Parameters are estimated from the *no-cache* runs:
  di  = 1 / mu_local    from the saturated K=64 no-cache throughput
  Z   = R(K=1) - di     fixed network/quorum delay, from the K=1 no-cache run

Closed single-server loop with delay (mean-value-analysis iteration):

  R_server(k) = di * (1 + Q(k-1))
  R(k)        = Z + R_server(k)
  X(k)        = k / R(k)
  Q(k)        = X(k) * R_server(k)

Plots measured (no-cache and with-cache) vs this M/M/1 model.
"""

import csv
import glob
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.ticker import FuncFormatter  # pyright: ignore[reportMissingImports]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from plot.config import BLUE, FIGSIZE, GREEN, RED, grid_style  # pyright: ignore[reportMissingImports]

NOCACHE_DIR = "csv/p2/exp3-no-cache"
CACHE_DIR = "csv/p2/exp3"
OUT_DIR = "charts/p2/modelling/"

K_VALUES = [4, 8, 16, 32, 64]


def mean_throughput(pattern: str) -> float | None:
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        return None
    tps = [float(next(csv.DictReader(open(f)))["throughput"]) for f in files]
    return sum(tps) / len(tps)


def measured_series(root: str, size: str, dist: str, cached: bool) -> list[float]:
    series = []
    for k in K_VALUES:
        c = f"c{k}"
        if cached:
            pattern = os.path.join(root, c, size, dist, "**",
                                   f"exp3-{c}-{size}-{dist}-*-summary.csv")
        else:
            pattern = os.path.join(root, c, size, dist, "**",
                                    f"exp3-nocache-{c}-{size}-{dist}-*-summary.csv")
        series.append(mean_throughput(pattern))
    return series


def closed_single_server(k: int, di: float, z: float) -> float:
    """Throughput X(k) for a closed single-server center with fixed delay z."""
    q = 0.0
    for _ in range(k):
        r_server = di * (1.0 + q)
        r = z + r_server
        x = k / r
        q = x * r_server
    return k / (z + di * (1.0 + q))


def estimate_params(size: str, dist: str) -> tuple[float, float, float] | None:
    """Return (di, z, mu_local) from no-cache runs, or None if data missing."""
    mu64 = mean_throughput(os.path.join(
        NOCACHE_DIR, "c64", size, dist, "**",
        f"exp3-nocache-c64-{size}-{dist}-*-summary.csv"))
    if not mu64:
        return None
    di = 1.0 / mu64

    tp1 = mean_throughput(os.path.join(
        NOCACHE_DIR, "c1", size, dist, "**",
        f"exp3-nocache-c1-{size}-{dist}-*-summary.csv"))
    if not tp1:
        return None
    z = (1.0 / tp1) - di
    if z < 0:
        z = 0.0
    return di, z, mu64


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    combos = [("l", "uniform"), ("l", "zipf"),
              ("s", "uniform"), ("s", "zipf")]
    for size, dist in combos:
        params = estimate_params(size, dist)
        if params is None:
            print(f"skip {size}/{dist}: missing no-cache c1/c64 data")
            continue
        di, z, mu = params

        meas_nc = measured_series(NOCACHE_DIR, size, dist, False)
        meas_ca = measured_series(CACHE_DIR, size, dist, True)
        model = [closed_single_server(k, di, z) for k in K_VALUES]

        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.plot(K_VALUES, meas_nc, "o-", color=RED, linewidth=2, markersize=8,
                label="measured (no-cache)")
        ax.plot(K_VALUES, meas_ca, "s-", color=BLUE, linewidth=2, markersize=6,
                label="measured (with cache)")
        ax.plot(K_VALUES, model, "^--", color=GREEN, linewidth=2, markersize=8,
                label="M/M/1 predicted")

        ax.set_title(
            f"M/M/1 (single leader) vs {size}/{dist}",
            fontsize=11, fontweight="bold")
        ax.set_xlabel("Concurrency level (K)")
        ax.set_ylabel("Throughput [txns/s]")
        ax.set_xticks(K_VALUES)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.grid(True, **grid_style)
        ax.legend(loc="upper left", fontsize=9)

        plt.tight_layout()
        out = os.path.join(OUT_DIR, f"mm1-throughput-{size}-{dist}.png")
        plt.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Saved to {out}  (di={di * 1000:.3f}ms, Z={z * 1000:.2f}ms, mu={mu:,.0f}/s)")
        plt.close(fig)


if __name__ == "__main__":
    main()