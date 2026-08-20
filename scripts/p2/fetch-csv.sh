#!/usr/bin/env bash
set -euo pipefail

# Fetches all phase2 benchmark CSVs from the benchmark client VM into the
# local csv/p2 directory, organized by experiment structure. Files are left
# untouched on the VM.
#
# Usage:
#   bash scripts/p2/fetch-csv.sh
#
# Environment:
#   ZONE    GCP zone (default europe-west3-c)
#   PREFIX  VM name prefix (default toydb)
#   NODE    VM to fetch CSVs from (default <PREFIX>-client)

ZONE="${ZONE:-europe-west3-c}"
PREFIX="${PREFIX:-toydb}"
NODE="${NODE:-$PREFIX-client}"

# Tar every top-level benchmark CSV (/opt/toydb/csv/exp*-*.csv) on the VM.
gcloud compute ssh "$NODE" --zone "$ZONE" --command \
    "cd /opt/toydb/csv && if ls exp*-*.csv >/dev/null 2>&1; then tar -cf /tmp/toydb-fetch.tar exp*-*.csv; else rm -f /tmp/toydb-fetch.tar; fi"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

if ! gcloud compute scp --zone "$ZONE" "$NODE:/tmp/toydb-fetch.tar" "$STAGE/" 2>/dev/null; then
    echo "No benchmark CSVs found on $NODE:/opt/toydb/csv"
    exit 0
fi
tar -xf "$STAGE/toydb-fetch.tar" -C "$STAGE"

# Organize the fetched files into csv/p2/<experiment structure>/<run id>/.
python3 - "$STAGE" <<'PYEOF'
import pathlib
import re
import shutil
import sys

stage = pathlib.Path(sys.argv[1])
base = pathlib.Path("csv/p2")

PATTERNS = [
    (
        re.compile(r"^exp1-(cache|no-cache)-(l|s)-(uniform|zipf)$"),
        lambda m: f"exp1/{m.group(1)}/{m.group(2)}/{m.group(3)}",
    ),
    (
        re.compile(r"^exp2-(fifo|lru)-(l|s)-(uniform|zipf)$"),
        lambda m: f"exp2/{m.group(1)}/{m.group(2)}/{m.group(3)}",
    ),
    (
        re.compile(r"^exp3-c(\d+)-(l|s)-(uniform|zipf)$"),
        lambda m: f"exp3/c{m.group(1)}/{m.group(2)}/{m.group(3)}",
    ),
    (
        re.compile(r"^exp3-nocache-c(\d+)-(l|s)-(uniform|zipf)$"),
        lambda m: f"exp3-no-cache/c{m.group(1)}/{m.group(2)}/{m.group(3)}",
    ),
]


def split_name(name):
    m = re.match(r"^(.*)-(\d+)$", name)
    if not m:
        raise ValueError(f"cannot split experiment/id from: {name}")
    return m.group(1), m.group(2)


moved = 0
for f in sorted(stage.iterdir()):
    if not f.is_file() or f.name == "toydb-fetch.tar":
        continue
    stem = f.stem
    body = stem[: -len("-summary")] if stem.endswith("-summary") else stem
    try:
        exp_part, id_part = split_name(body)
    except ValueError as e:
        print(f"skip: {e}")
        continue

    dest_dir = None
    for pattern, to_dir in PATTERNS:
        m = pattern.match(exp_part)
        if m:
            dest_dir = base / to_dir(m) / id_part
            break
    if dest_dir is None:
        print(f"skip (unrecognized experiment): {f.name}")
        continue

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(f), dest_dir / f.name)
    moved += 1
    print(f"{f.name} -> {dest_dir / f.name}")

print(f"\nFetched {moved} file(s) into {base}/")
PYEOF
