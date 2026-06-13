import argparse
import csv
import os

import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]


def load_csv(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                try:
                    parsed[k] = float(v)
                except ValueError:
                    parsed[k] = v
            rows.append(parsed)
    return rows


def guess_output(files):
    os.makedirs("charts", exist_ok=True)
    base = os.path.splitext(os.path.basename(files[0]))[0]
    if base.endswith("-summary"):
        base = base[: -len("-summary")]
    return (
        f"charts/{base}-latency.png"
        if len(files) == 1
        else "charts/comparison-latency.png"
    )


def guess_label(path):
    data = load_csv(path)
    if data and "experiment" in data[0]:
        return data[0]["experiment"]
    return os.path.basename(path)


def main():
    parser = argparse.ArgumentParser(description="Plot latency percentiles over time")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--labels", nargs="+")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    labels = args.labels if args.labels else [guess_label(f) for f in args.files]
    output = args.output if args.output else guess_output(args.files)

    if len(labels) != len(args.files):
        parser.error("number of --labels must match number of files")

    fig, ax = plt.subplots(figsize=(6, 4))
    for path, label in zip(args.files, labels):
        data = load_csv(path)
        t = [r["time_s"] for r in data]
        p50 = [r["p50_ms"] for r in data]
        p90 = [r["p90_ms"] for r in data]
        p99 = [r["p99_ms"] for r in data]
        maxv = [r["max"] for r in data]
        marker = "o" if len(t) == 1 else ""
        ax.plot(t, p50, marker=marker, label=f"{label} p50")
        ax.plot(t, p90, marker=marker, linestyle="-.", label=f"{label} p90")
        ax.plot(t, p99, marker=marker, linestyle="--", label=f"{label} p99")
        ax.plot(t, maxv, marker=marker, linestyle=":", label=f"{label} max")

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Latency [ms]")
    ax.set_title("Latency over time")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
