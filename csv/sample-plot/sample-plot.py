import argparse
import csv

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


def experiment_names(data):
    names = set()
    for row in data:
        if "experiment" in row:
            names.add(row["experiment"])
    return " ".join(sorted(names))


def plot_timeseries(files, labels, output):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    for path, label in zip(files, labels):
        data = load_csv(path)
        t = [r["time_s"] for r in data]
        tps = [r["rate_tps"] for r in data]
        p50 = [r["p50_ms"] for r in data]
        p99 = [r["p99_ms"] for r in data]

        ax1.plot(t, tps, label=label)
        ax2.plot(t, p50, label=f"{label} p50")
        ax2.plot(t, p99, label=f"{label} p99", linestyle="--")

    exp = experiment_names(load_csv(files[0]))
    title = f"{exp} - " if exp else ""
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel("Throughput [txns/s]")
    ax1.set_title(f"{title}Throughput over time")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.3)

    ax2.set_xlabel("Time [s]")
    ax2.set_ylabel("Latency [ms]")
    ax2.set_title(f"{title}Latency over time")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.show()


def plot_summary(files, labels, output):
    data = [load_csv(f) for f in files]
    first = data[0][0]

    metrics = ["rate_tps", "p50_ms", "p90_ms", "p99_ms"]
    x = range(len(metrics))
    width = 0.8 / len(files)

    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (rows, label) in enumerate(zip(data, labels)):
        d = rows[0]
        values = [d[m] for m in metrics]
        offset = (i - (len(files) - 1) / 2) * width
        ax.bar([xi + offset for xi in x], values, width * 0.9, label=label)

    exp = first.get("experiment", "")
    title = f"{exp} - " if exp else ""
    ax.set_xticks(x)
    ax.set_xticklabels(["Throughput\n[tps]", "p50 [ms]", "p90 [ms]", "p99 [ms]"])
    ax.set_title(f"{title}Summary comparison")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Plot benchmark CSV data")
    parser.add_argument("files", nargs="+", help="CSV file(s) to plot")
    parser.add_argument(
        "--labels", nargs="+", help="Legend labels (default: filenames)"
    )
    parser.add_argument(
        "-o", "--output", default="sample-plot.png", help="Output image file"
    )
    args = parser.parse_args()

    labels = args.labels if args.labels else [f.split("/")[-1] for f in args.files]

    if len(labels) != len(args.files):
        parser.error("number of --labels must match number of files")

    sample = load_csv(args.files[0])
    if "time_s" in sample[0]:
        plot_timeseries(args.files, labels, args.output)
    else:
        plot_summary(args.files, labels, args.output)


if __name__ == "__main__":
    main()
