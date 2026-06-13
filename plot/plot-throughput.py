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
        f"charts/{base}-throughput.png"
        if len(files) == 1
        else "charts/comparison-throughput.png"
    )


def guess_label(path):
    data = load_csv(path)
    if data and "experiment" in data[0]:
        return data[0]["experiment"]
    return os.path.basename(path)


def main():
    parser = argparse.ArgumentParser(description="Plot throughput over time")
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
        tps = [r["rate_tps"] for r in data]
        single = len(t) == 1
        if single:
            val = tps[0]
            t, tps = [0, t[0]], [val, val]
        ax.plot(t, tps, marker="o", markevery=[-1] if single else None, label=label)

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Throughput [txns/s]")
    ax.set_title("Throughput over time")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()
