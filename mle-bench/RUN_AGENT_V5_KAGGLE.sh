#!/bin/bash
# Build and run agent_v5_kaggle
# Must be run from the mle-bench directory

set -e  # Exit on error

# === VALIDATE WE'RE IN THE RIGHT DIRECTORY ===
if [ ! -f "environment/Dockerfile" ]; then
    echo "❌ ERROR: Must run this script from the mle-bench directory"
    echo "   Expected to find: environment/Dockerfile"
    echo "   Current directory: $(pwd)"
    echo ""
    echo "Usage:"
    echo "  cd /path/to/mle-bench"
    echo "  ./RUN_AGENT_V5_KAGGLE.sh"
    exit 1
fi

# === CONFIGURATION (can be overridden via environment variables) ===
IMAGE_TAG="${IMAGE_TAG:-agent_v5_kaggle:latest}"
DRY_RUN="${DRY_RUN:-false}"
export SUBMISSION_DIR="${SUBMISSION_DIR:-/home/submission}"
export LOGS_DIR="${LOGS_DIR:-/home/logs}"
export CODE_DIR="${CODE_DIR:-/home/code}"
export AGENT_DIR="${AGENT_DIR:-/home/agent}"

echo "=========================================="
echo "Agent V5 Kaggle - Build & Run"
echo "=========================================="
echo "Working directory: $(pwd)"
echo "Docker image: $IMAGE_TAG"
echo "Dry run mode: $DRY_RUN"
echo ""

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY not set"
    echo "   Please run: export ANTHROPIC_API_KEY=your-key-here"
    exit 1
fi

echo "✅ ANTHROPIC_API_KEY is set"

echo ""
echo "=========================================="
echo "Step 1: Build Docker Images"
echo "=========================================="

# Check if base mlebench-env image exists
if ! docker image inspect mlebench-env:latest >/dev/null 2>&1; then
    echo "Building base image 'mlebench-env'..."
    echo ""

    if [ "$DRY_RUN" = "true" ]; then
        echo "🔍 DRY RUN: Would build mlebench-env base image"
    else
        docker build --platform=linux/amd64 -t mlebench-env -f environment/Dockerfile .
        echo "✅ Base image mlebench-env built successfully"
    fi
    echo ""
else
    echo "✅ Base image mlebench-env already exists"
    echo ""
fi

# Build agent_v5_kaggle image
echo "Building agent_v5_kaggle image..."

if [ "$DRY_RUN" = "true" ]; then
    echo "🔍 DRY RUN: Would build Docker image with:"
    echo "   Tag: $IMAGE_TAG"
    echo "   Context: agents/agent_v5_kaggle/"
    echo "   Platform: linux/amd64"
else
    docker build --platform=linux/amd64 -t "$IMAGE_TAG" \
      agents/agent_v5_kaggle/ \
      --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
      --build-arg LOGS_DIR=$LOGS_DIR \
      --build-arg CODE_DIR=$CODE_DIR \
      --build-arg AGENT_DIR=$AGENT_DIR
fi

echo ""
if [ "$DRY_RUN" = "true" ]; then
    echo "🔍 DRY RUN: Image build skipped"
else
    echo "✅ Agent image built successfully"
fi

echo ""
echo "=========================================="
echo "Step 2: Prepare Competitions"
echo "=========================================="

if [ "$DRY_RUN" = "true" ]; then
    echo "🔍 DRY RUN: Would prepare competitions from:"
    echo "   experiments/splits/custom-set.txt"
    if [ -f experiments/splits/custom-set.txt ]; then
        echo "   Competitions:"
        cat experiments/splits/custom-set.txt | sed 's/^/   - /'
    fi
    echo ""
    echo "🔍 DRY RUN: Would pull git lfs files"
else
    for line in $(cat experiments/splits/custom-set.txt); do
        echo "Preparing: $line"
        mlebench prepare -c $line
    done

    git lfs pull
fi

echo ""
echo "=========================================="
echo "Step 3: Run Agent"
echo "=========================================="

# Create temporary container config with GPU properly attached
TMP_CONFIG=$(mktemp /tmp/container_config_XXXXXX.json)
cat > "$TMP_CONFIG" << 'EOF'
{
    "mem_limit": "80G",
    "shm_size": "16G",
    "nano_cpus": 8e9,
    "gpus": -1
}
EOF

echo "Using container config: $TMP_CONFIG"
cat "$TMP_CONFIG"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    echo "🔍 DRY RUN: Would run agent with:"
    echo "   Agent ID: ${IMAGE_TAG}"
    echo "   Competition set: experiments/splits/custom-set.txt"
    echo "   Config: $TMP_CONFIG"
    echo ""
    echo "✅ DRY RUN COMPLETE - No actual execution performed"
    rm -f "$TMP_CONFIG"
    exit 0
fi

# Run the agent in the background
python run_agent.py \
--agent-id "${IMAGE_TAG}" \
--competition-set experiments/splits/custom-set.txt \
--container-config "$TMP_CONFIG" &

AGENT_PID=$!

# Wait a moment for the container to start
sleep 10

# Get the latest running container
CONTAINER_ID=$(docker ps --latest --format "{{.ID}}")

if [ -n "$CONTAINER_ID" ]; then
    echo "Container started: $CONTAINER_ID"
    echo "Tailing logs..."
    # Tail the logs (this will follow until the container stops)
    docker exec "$CONTAINER_ID" tail -f /home/logs/agent.log || true
else
    echo "⚠️  No container found, waiting for agent process..."
fi

# Wait for the background python process to complete
wait $AGENT_PID

echo ""
echo "Agent process completed"
# Clean up temporary config
rm -f "$TMP_CONFIG"

echo ""
echo "=========================================="
echo "Step 4: Check Results"
echo "=========================================="

# Find latest run
RUN_GROUP=$(ls -t runs/ | head -1)
echo "Run group: $RUN_GROUP"
echo ""

echo ""
echo "=========================================="
echo "Step 5: Grade Submission"
echo "=========================================="

# Generate submission JSONL
python experiments/make_submission.py \
  --metadata runs/$RUN_GROUP/metadata.json \
  --output runs/$RUN_GROUP/submission.jsonl

# Grade
mlebench grade \
  --submission runs/$RUN_GROUP/submission.jsonl \
  --output-dir runs/$RUN_GROUP

echo ""
echo "=========================================="
echo "COMPLETE!"
echo "=========================================="
echo "Results in: runs/$RUN_GROUP/"
echo ""
echo "View logs:"
echo "  cat runs/$RUN_GROUP/*/logs/*.log"
echo ""
echo "View code:"
echo "  ls runs/$RUN_GROUP/*/code/"
echo ""
echo "View submission:"
echo "  cat runs/$RUN_GROUP/*/submission/submission.csv"
echo ""
echo "View grading results:"
echo "  cat runs/$RUN_GROUP/results.json"
