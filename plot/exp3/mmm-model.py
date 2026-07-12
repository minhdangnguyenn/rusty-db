import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    data_dir_for,  # pyright: ignore[reportAttributeAccessIssue]
    figsize_single,  # pyright: ignore[reportAttributeAccessIssue]
    grid_style,  # pyright: ignore[reportAttributeAccessIssue]
    legend_pos,  # pyright: ignore[reportAttributeAccessIssue]
    load_csv,  # pyright: ignore[reportAttributeAccessIssue]
    mean_ci,  # pyright: ignore[reportAttributeAccessIssue]
)

CC_LEVELS = ["c4", "c8", "c16", "c32", "c64"]
M = [4, 8, 16, 32, 64]


def throughput_per_run(data):
    last = data[-1]
    return last["txns"] / last["time_s"]


def main():
    parser = argparse.ArgumentParser(description="M/M/m model plot")
    parser.add_argument(
        "--mode", choices=["throughput", "response-time"], default="throughput"
    )
    args = parser.parse_args()

    EXPS = [("l", "uniform"), ("l", "zipf"), ("s", "uniform"), ("s", "zipf")]

    for size, dist in EXPS:
        all_S = []
        means = []
        ci_lowers = []
        ci_uppers = []

        for i, label in enumerate(CC_LEVELS):
            data_dir = data_dir_for(label, size, dist)
            csvs = sorted(glob.glob(os.path.join(data_dir, "**/*.csv"), recursive=True))
            csvs = [
                f
                for f in csvs
                if "summary" not in os.path.basename(f)
                and "avg" not in os.path.basename(f)
            ]
            if not csvs:
                continue

            runs = [load_csv(f) for f in csvs]
            tps = [throughput_per_run(r) for r in runs]

            S_vals = [M[i] / tp for tp in tps]
            all_S.extend(S_vals)

            m, lo, hi = mean_ci(tps)
            means.append(m)
            ci_lowers.append(lo)
            ci_uppers.append(hi)

        S_mean = sum(all_S) / len(all_S)
        mu = 1.0 / S_mean
        n = len(M)

        fig, ax = plt.subplots(figsize=figsize_single)

        if args.mode == "response-time":
            rt_means = [M[i] / means[i] * 1000 for i in range(n)]
            rt_lowers = [M[i] / ci_uppers[i] * 1000 for i in range(n)]
            rt_uppers = [M[i] / ci_lowers[i] * 1000 for i in range(n)]
            rt_ideal = S_mean * 1000

            ax.plot(
                M,
                rt_means,
                color="#e41a1c",
                linewidth=1.5,
                marker="o",
                markersize=8,
                label="Measured (Little's law: m / throughput)",
            )
            ax.errorbar(
                M,
                rt_means,
                yerr=[
                    [rt_means[i] - rt_lowers[i] for i in range(n)],
                    [rt_uppers[i] - rt_means[i] for i in range(n)],
                ],
                fmt="none",
                color="#e41a1c",
                capsize=4,
                capthick=1.5,
            )
            ax.axhline(
                y=rt_ideal,
                linestyle="--",
                color="#377eb8",
                linewidth=2,
                label=f"S̅ = {rt_ideal:.1f} ms  (M/M/m ideal, R = 1/μ)",
            )

            ax.set_ylabel("Average response time [ms]")
            ax.set_title("M/M/m average response time")
            ax.set_ylim(bottom=0)
            out_path = f"charts/cloud/exp3/{size}/{dist}/mmm-response-time.png"
        else:
            ax.plot(
                M,
                means,
                color="#e41a1c",
                linewidth=1.5,
                marker="o",
                markersize=8,
                label="Measured ± 95% CI",
            )
            ax.errorbar(
                M,
                means,
                yerr=[
                    [means[i] - ci_lowers[i] for i in range(n)],
                    [ci_uppers[i] - means[i] for i in range(n)],
                ],
                fmt="none",
                color="#e41a1c",
                capsize=4,
                capthick=1.5,
            )
            ax.plot(
                [0, max(M) * 1.05],
                [0, mu * max(M) * 1.05],
                linestyle="--",
                color="#377eb8",
                linewidth=2,
                label=f"μ = 1 / S̅ = {mu:.1f} (M/M/m, throughput = μ · m)",
            )
            ax.set_ylabel("Throughput [txns/s]")
            ax.set_title("M/M/m model fit")
            ax.set_ylim(bottom=0)
            out_path = f"charts/cloud/exp3/{size}/{dist}/mmm-throughput.png"

        ax.set_xlabel("Number of workers (m)")
        ax.set_xticks(M)
        ax.set_xlim(left=0)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
        ax.legend(**legend_pos)
        ax.grid(True, **grid_style)
        plt.tight_layout()

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        print(f"Saved to {out_path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
