#!/bin/bash
# Build and run agent_v5_kaggle
# Must be run from the mle-bench directory

set -e  # Exit on error

# === ACTIVATE VIRTUAL ENVIRONMENT IF PRESENT ===
# When running with sudo, venv is not preserved, so source it
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment: $VIRTUAL_ENV"
    source "$VIRTUAL_ENV/bin/activate"
elif [ -f "venv/bin/activate" ]; then
    echo "Found venv in current directory, activating..."
    source venv/bin/activate
fi

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
AGENT_ID="${AGENT_ID:-agent_v5_kaggle}"  # Agent registry ID (no Docker tag)
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
echo "Agent ID: $AGENT_ID"
echo "Dry run mode: $DRY_RUN"
echo ""

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY not set"
    echo "   Please run: export ANTHROPIC_API_KEY=your-key-here"
    exit 1
fi

echo "✅ ANTHROPIC_API_KEY is set"

# Check if mlebench is installed
if ! python -c "import mlebench" 2>/dev/null; then
    echo ""
    echo "⚠️  mlebench not installed"

    # Only auto-install if we're in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "   Installing in virtual environment..."
        pip install -e . --quiet
        echo "✅ mlebench installed"
    else
        echo "❌ ERROR: mlebench not found and not in a virtual environment"
        echo "   Please run one of:"
        echo "     1. cd mle-bench && python3 -m venv venv && source venv/bin/activate && pip install -e ."
        echo "     2. pip install -e . --break-system-packages (not recommended)"
        exit 1
    fi
fi

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
    echo "   Context: .. (canada-research root, to resolve symlinks)"
    echo "   Dockerfile: mle-bench/agents/agent_v5_kaggle/Dockerfile"
    echo "   Platform: linux/amd64"
else
    # Build from parent directory (canada-research) to resolve symlinks
    # The symlinks in agent_v5_kaggle/ point to ../../../agent_v5, etc.
    cd ..
    docker build --platform=linux/amd64 -t "$IMAGE_TAG" \
      -f mle-bench/agents/agent_v5_kaggle/Dockerfile \
      . \
      --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
      --build-arg LOGS_DIR=$LOGS_DIR \
      --build-arg CODE_DIR=$CODE_DIR \
      --build-arg AGENT_DIR=$AGENT_DIR
    cd mle-bench
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
    echo "   Agent ID: ${AGENT_ID}"
    echo "   Competition set: experiments/splits/custom-set.txt"
    echo "   Config: $TMP_CONFIG"
    echo ""
    echo "✅ DRY RUN COMPLETE - No actual execution performed"
    rm -f "$TMP_CONFIG"
    exit 0
fi

# Run the agent in the background
python run_agent.py \
--agent-id "${AGENT_ID}" \
--competition-set experiments/splits/custom-set.txt \
--container-config "$TMP_CONFIG" &

AGENT_PID=$!

# Wait a moment for the container to start
sleep 10

# Get the latest running container
CONTAINER_ID=$(docker ps --latest --format "{{.ID}}")

if [ -n "$CONTAINER_ID" ]; then
    echo "Container started: $CONTAINER_ID"
    echo "Waiting for agent.log to be created..."

    # Wait for agent.log to exist (max 60 seconds)
    for i in {1..60}; do
        if docker exec "$CONTAINER_ID" test -f /home/logs/agent.log 2>/dev/null; then
            echo "✅ agent.log found, streaming logs..."
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""

    # Tail the agent log file
    docker exec "$CONTAINER_ID" tail -f /home/logs/agent.log 2>&1 || true
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

if [ -z "$RUN_GROUP" ]; then
    echo "❌ ERROR: No run results found in runs/"
    exit 1
fi

echo "Run group: $RUN_GROUP"
echo ""

# Check what files were created
echo "Files in run directory:"
ls -la "runs/$RUN_GROUP/" | head -20
echo ""

# Check if grading already happened
GRADING_REPORT=$(find "runs/$RUN_GROUP/" -name "*_grading_report.json" -o -name "results.json" | head -1)
if [ -n "$GRADING_REPORT" ]; then
    echo "✅ Grading already complete"
    echo "   Report: $GRADING_REPORT"
else
    echo ""
    echo "=========================================="
    echo "Step 5: Grade Submission"
    echo "=========================================="

    # Check if submission.jsonl exists, if not create it
    if [ ! -f "runs/$RUN_GROUP/submission.jsonl" ]; then
        echo "Generating submission JSONL..."
        python experiments/make_submission.py \
          --metadata runs/$RUN_GROUP/metadata.json \
          --output runs/$RUN_GROUP/submission.jsonl
    fi

    # Grade
    echo "Grading submission..."
    mlebench grade \
      --submission runs/$RUN_GROUP/submission.jsonl \
      --output-dir runs/$RUN_GROUP

    # Find the grading report
    GRADING_REPORT=$(find "runs/$RUN_GROUP/" -name "*_grading_report.json" -o -name "results.json" | head -1)
fi

echo ""
echo "=========================================="
echo "COMPLETE!"
echo "=========================================="
echo "Results in: runs/$RUN_GROUP/"
echo ""

# Find the actual competition directory
COMP_DIR=$(find "runs/$RUN_GROUP/" -maxdepth 1 -type d ! -name "$(basename runs/$RUN_GROUP)" | head -1)

if [ -n "$COMP_DIR" ]; then
    COMP_NAME=$(basename "$COMP_DIR")
    echo "Competition: $COMP_NAME"
    echo ""
    echo "View logs:"
    echo "  find $COMP_DIR -name '*.log' -exec cat {} \;"
    echo ""
    echo "View code:"
    echo "  ls $COMP_DIR/code/ 2>/dev/null || echo 'No code directory'"
    echo ""
    echo "View submission:"
    echo "  ls $COMP_DIR/submission/ 2>/dev/null || echo 'No submission directory'"
    echo ""
fi

if [ -n "$GRADING_REPORT" ]; then
    echo "View grading results:"
    echo "  cat $GRADING_REPORT"
    echo ""
    echo "Grading summary:"
    cat "$GRADING_REPORT" | head -30
fi
