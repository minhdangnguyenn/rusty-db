import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from plot.config import (
    BLUE,
    CC_LEVELS,
    FIGSIZE,
    RED,
    M,
    data_dir_for,
    grid_style,
    legend_pos,
    load_csv,
    mean_ci,
)

if __name__ == "__main__":
    for dist in ["uniform", "zipf"]:
        fig, ax = plt.subplots(figsize=FIGSIZE)

        for size, color, marker, label in [
            ("s", BLUE, "o", "Small (1000 rows)"),
            ("l", RED, "s", "Large (10000 rows)"),
        ]:
            means, lowers, uppers = [], [], []
            for label_cc, m in zip(CC_LEVELS, M):
                data_dir = data_dir_for(label_cc, size, dist)
                csvs = sorted(
                    glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True)
                )
                csvs = [f for f in csvs if "summary" not in f and "avg" not in f]
                runs = [load_csv(f) for f in csvs]
                tps = [float(r[-1]["throughput"]) for r in runs]
                mean, lo, hi = mean_ci(tps)
                means.append(mean)
                lowers.append(lo)
                uppers.append(hi)

            ax.plot(
                M,
                means,
                color=color,
                marker=marker,
                markersize=8,
                linewidth=2,
                label=label,
            )
            ax.errorbar(
                M,
                means,
                yerr=[
                    [means[i] - lowers[i] for i in range(len(M))],
                    [uppers[i] - means[i] for i in range(len(M))],
                ],
                fmt="none",
                color=color,
                capsize=6,
                capthick=2.5,
            )

        ax.set_xticks(M)
        ax.set_xlabel("Number of workers (m)")
        ax.set_ylabel("Throughput [txns/s]")
        ax.set_title("Small vs Large dataset")
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        out_dir = "charts/cloud/exp3/throughput-s-vs-l"
        os.makedirs(out_dir, exist_ok=True)
        out_path = f"{out_dir}/{dist}.png"
        plt.savefig(out_path)
        print(f"Saved to {out_path}")
        plt.close(fig)
