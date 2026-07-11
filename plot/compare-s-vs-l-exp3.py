import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.dirname(__file__))
from config import (  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    mean_ci,  # pyright: ignore[reportAttributeAccessIssue]
)

CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]
M = [4, 8, 16, 32, 64]


def data_dir_for(label, size, dist):
    if label == "c16":
        return f"csv/cloud/exp1/cache/{dist}/{size}"
    return f"csv/cloud/exp3/{label}/{size}/{dist}"


if __name__ == "__main__":
    for dist in ["uniform", "zipf"]:
        fig, ax = plt.subplots(figsize=figsize_single)

        for size, color, marker, label in [
            ("s", "#377eb8", "o", "Small (1000 rows)"),
            ("l", "#e41a1c", "s", "Large (10000 rows)"),
        ]:
            means, lowers, uppers = [], [], []
            for label_cc, m in zip(CC_LEVELS, M):
                data_dir = data_dir_for(label_cc, size, dist)
                csvs = sorted(
                    glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True)
                )
                csvs = [
                    f
                    for f in csvs
                    if "summary" not in os.path.basename(f)
                    and "avg" not in os.path.basename(f)
                ]
                runs = [load_csv(f) for f in csvs]
                tps = [r[-1]["throughput"] for r in runs]
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
                capsize=4,
                capthick=1.5,
            )

        ax.set_xticks(M)
        ax.set_xlabel("Number of workers (m)")
        ax.set_ylabel("Throughput [txns/s]")
        ax.set_title(f"Small vs Large dataset (exp3, {dist})")
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        out_dir = f"charts/cloud/exp3/{dist}"
        os.makedirs(out_dir, exist_ok=True)
        out_path = f"{out_dir}/compare-s-vs-l.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)
