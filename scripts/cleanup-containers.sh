#!/bin/bash
# Idempotent container cleanup for MLE-bench runs
# Can be called multiple times safely (from trap, from GitHub Actions, manually)

set -e

RUN_ID="${RUN_ID:-local}"
CONTAINER_TRACKING_FILE="/tmp/mlebench_containers_${RUN_ID}.txt"

echo "🧹 Cleaning up containers for run_id: $RUN_ID"

# Method 1: Kill containers by label
echo "Looking for containers with label run_id=$RUN_ID..."
LABELED_CONTAINERS=$(docker ps -aq --filter "label=run_id=$RUN_ID" 2>/dev/null || true)

if [ -n "$LABELED_CONTAINERS" ]; then
    echo "Found containers by label: $LABELED_CONTAINERS"
    for CONTAINER_ID in $LABELED_CONTAINERS; do
        echo "  Stopping container: $CONTAINER_ID"
        docker stop "$CONTAINER_ID" 2>/dev/null || true
        docker rm "$CONTAINER_ID" 2>/dev/null || true
    done
else
    echo "No containers found by label"
fi

# Method 2: Kill containers from tracking file (if exists)
if [ -f "$CONTAINER_TRACKING_FILE" ]; then
    echo "Found container tracking file: $CONTAINER_TRACKING_FILE"
    while read -r CONTAINER_ID; do
        if [ -n "$CONTAINER_ID" ]; then
            # Check if container still exists
            if docker ps -aq --filter "id=$CONTAINER_ID" | grep -q .; then
                echo "  Stopping tracked container: $CONTAINER_ID"
                docker stop "$CONTAINER_ID" 2>/dev/null || true
                docker rm "$CONTAINER_ID" 2>/dev/null || true
            fi
        fi
    done < "$CONTAINER_TRACKING_FILE"
    rm -f "$CONTAINER_TRACKING_FILE"
    echo "Removed tracking file"
fi

# Verify cleanup
REMAINING=$(docker ps -q --filter "label=run_id=$RUN_ID" 2>/dev/null || true)
if [ -n "$REMAINING" ]; then
    echo "⚠️  Warning: Some containers still running: $REMAINING"
    echo "   They may still be shutting down. GitHub Actions cleanup will catch them."
else
    echo "✅ All containers cleaned up successfully"
fi

# Always exit 0 (idempotent - safe to run multiple times)
exit 0
