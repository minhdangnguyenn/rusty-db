#!/bin/bash
# Removes all cluster node data (Raft log and SQL state machine).
for ID in 1 2 3 4 5; do
    rm -f "cluster/toydb$ID/data/raft" "cluster/toydb$ID/data/sql"
done
echo "Cluster data reset complete."
echo "After sanitizing, remeber to restart the cluster."
