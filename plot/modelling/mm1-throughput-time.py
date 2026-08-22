"""Per-second throughput at the default concurrency K=16 vs the M/M/1 model.

The M/M/1 (single-leader + fixed delay) model is fit to the no-cache runs
(di from the saturated K=64 throughput, z from the K=1 throughput) and
predicts a single steady-state throughput for K=16. This chart overlays that
prediction on the measured per-second throughput (1-30s) for the cached and
no-cache runs so the fit can be judged over time.

Model (closed single-server loop with delay, mean-value-analysis iteration):

  R_server(n) = di * (1 + Q(n-1))
  R(n)        = Z + R_server(n)
  X(n)        = n / R(n)
  Q(n)        = X(n) * R_server(n)
"""

import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.ticker import FuncFormatter  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from plot.config import (  # pyright: ignore[reportMissingImports]
    BLUE,
    FIGSIZE,
    GREEN,
    RED,
    compute_ci_from_dir,
    grid_style,
    legend_pos,
    load_csv,
    mean_ci,
)

CACHE_DIR = "csv/p2/exp3"
NOCACHE_DIR = "csv/p2/exp3-no-cache"
OUT_DIR = "charts/p2/modelling/"

K = 16
N_SECONDS = 30

CONFIGS = [
    ("l", "uniform"),
    ("l", "zipf"),
    ("s", "uniform"),
    ("s", "zipf"),
]


def closed_mm1(k: int, di: float, z: float) -> float:
    """Throughput of a closed single-server center with fixed delay z."""
    q = 0.0
    x = 0.0
    for n in range(1, k + 1):
        r_server = di * (1.0 + q)
        r = z + r_server
        x = n / r
        q = x * r_server
    return x


def run_throughputs(data_dir: str) -> list[float]:
    csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
    csvs = [f for f in csvs if "summary" not in f and "avg" not in f]

    tps: list[float] = []

    for path in csvs:
        run = load_csv(path)
        if run:
            tps.append(float(run[-1]["txns"]) / float(run[-1]["time_s"]))

    return tps


def estimate_params(size: str, dist: str):
    """Estimate (di, z) and their CIs from the no-cache runs.

    Returns a dict with point estimates and CI corners, or None when the
    K=1/K=64 no-cache data is missing.
    """
    tps64 = run_throughputs(f"{NOCACHE_DIR}/c64/{size}/{dist}")
    tps1 = run_throughputs(f"{NOCACHE_DIR}/c1/{size}/{dist}")

    if not tps64 or not tps1:
        return None

    x64, x64_lo, x64_hi = mean_ci(tps64)
    x1, x1_lo, x1_hi = mean_ci(tps1)

    di = 1.0 / x64
    z = max(1.0 / x1 - di, 0.0)

    # Throughput is decreasing in both di and z, so the prediction CI is
    # [closed_mm1(k, di_hi, z_hi), closed_mm1(k, di_lo, z_lo)].
    di_lo = 1.0 / x64_hi
    di_hi = 1.0 / x64_lo
    z_lo = max(1.0 / x1_hi - di_hi, 0.0)
    z_hi = 1.0 / x1_lo - di_lo

    return {
        "di": di,
        "z": z,
        "di_lo": di_lo,
        "di_hi": di_hi,
        "z_lo": z_lo,
        "z_hi": z_hi,
    }


def plot_config(size: str, dist: str) -> None:
    times_nc, means_nc, cis_nc = compute_ci_from_dir(f"{NOCACHE_DIR}/c16/{size}/{dist}")
    times_ca, means_ca, cis_ca = compute_ci_from_dir(f"{CACHE_DIR}/c16/{size}/{dist}")

    if not times_nc:
        print(f"skip {size}/{dist}: no no-cache K=16 data")
        return

    params = estimate_params(size, dist)

    if params is None:
        print(f"skip {size}/{dist}: missing c1/c64 no-cache data")
        return

    model = closed_mm1(K, params["di"], params["z"])
    model_lo = closed_mm1(K, params["di_hi"], params["z_hi"])
    model_hi = closed_mm1(K, params["di_lo"], params["z_lo"])

    fig, ax = plt.subplots(figsize=FIGSIZE)

    if times_ca:
        ax.plot(
            times_ca,
            means_ca,
            "o-",
            color=BLUE,
            linewidth=1.5,
            markersize=4,
            label="Measured (with cache)",
        )
        ax.fill_between(
            times_ca,
            [m - c for m, c in zip(means_ca, cis_ca)],
            [m + c for m, c in zip(means_ca, cis_ca)],
            color=BLUE,
            alpha=0.15,
        )

    ax.plot(
        times_nc,
        means_nc,
        "^-",
        color=RED,
        linewidth=1.5,
        markersize=4,
        label="No cache",
    )
    ax.fill_between(
        times_nc,
        [m - c for m, c in zip(means_nc, cis_nc)],
        [m + c for m, c in zip(means_nc, cis_nc)],
        color=RED,
        alpha=0.15,
    )

    ax.axhline(
        model,
        color=GREEN,
        linestyle="--",
        linewidth=2,
        label=f"M/M/1 predicted model = {model:,.0f}txns/s",
    )
    ax.fill_between(times_nc, model_lo, model_hi, color=GREEN, alpha=0.15)

    ax.set_title(f"M/M/1 at K={K} — {size}/{dist}", fontsize=11, fontweight="bold")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_xlim(left=0, right=N_SECONDS + 0.5)
    ax.set_xticks(range(0, N_SECONDS + 1, 5))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, **grid_style)
    ax.legend(**legend_pos)

    # With-cache throughput can be orders of magnitude above the no-cache
    # and model values (e.g. s/* configs), which crushes the lower curves
    # against the bottom on a linear axis. Use a log scale in that case.
    all_means = means_nc + (means_ca if times_ca else [])
    if times_ca and max(means_ca) > 20 * max(means_nc):
        ax.set_yscale("log")
        ax.set_ylim(bottom=min(all_means) * 0.5)
    else:
        ax.set_ylim(bottom=0)

    plt.tight_layout()

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = f"{OUT_DIR}mm1-throughput-time-{size}-{dist}.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved to {out_path}  (model={model:,.0f}/s at K={K})")
    plt.close(fig)


def main() -> None:
    for size, dist in CONFIGS:
        plot_config(size, dist)


if __name__ == "__main__":
    main()
