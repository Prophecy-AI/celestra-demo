#!/bin/bash
# Build and run agent_v5_kaggle
# Must be run from the mle-bench directory
#
# Production-grade CI/CD implementation with:
# - Foreground execution (no race conditions)
# - Signal handlers (cleanup on cancel/Ctrl+C)
# - Container tracking and cleanup
# - Proper error handling

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
RUN_ID="${RUN_ID:-local}"  # GitHub run ID for tracking containers
export SUBMISSION_DIR="${SUBMISSION_DIR:-/home/submission}"
export LOGS_DIR="${LOGS_DIR:-/home/logs}"
export CODE_DIR="${CODE_DIR:-/home/code}"
export AGENT_DIR="${AGENT_DIR:-/home/agent}"

# Temporary config file (cleaned up by trap)
TMP_CONFIG=""

# === CLEANUP FUNCTION ===
cleanup() {
    local EXIT_CODE=$?

    echo ""
    echo "🧹 Cleanup triggered (exit code: $EXIT_CODE)"

    # Clean up temp config
    if [ -n "$TMP_CONFIG" ] && [ -f "$TMP_CONFIG" ]; then
        rm -f "$TMP_CONFIG"
        echo "   Removed temp config: $TMP_CONFIG"
    fi

    # Call cleanup script to kill containers
    CLEANUP_SCRIPT="$(dirname "$0")/../scripts/cleanup-containers.sh"
    if [ -f "$CLEANUP_SCRIPT" ]; then
        echo "   Running cleanup script..."
        bash "$CLEANUP_SCRIPT" || true
    else
        echo "   ⚠️  Cleanup script not found: $CLEANUP_SCRIPT"
        # Fallback: manual cleanup
        if [ -n "$RUN_ID" ]; then
            echo "   Attempting manual cleanup for run_id=$RUN_ID"
            CONTAINERS=$(docker ps -q --filter "label=run_id=$RUN_ID" 2>/dev/null || true)
            if [ -n "$CONTAINERS" ]; then
                docker stop $CONTAINERS 2>/dev/null || true
                docker rm $CONTAINERS 2>/dev/null || true
            fi
        fi
    fi

    echo "✅ Cleanup complete"
    exit $EXIT_CODE
}

# === REGISTER SIGNAL HANDLERS ===
# Cleanup on normal exit, Ctrl+C, kill, or term signal
trap cleanup EXIT INT TERM

echo "=========================================="
echo "Agent V5 Kaggle - Build & Run"
echo "=========================================="
echo "Working directory: $(pwd)"
echo "Docker image: $IMAGE_TAG"
echo "Agent ID: $AGENT_ID"
echo "Run ID: $RUN_ID"
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

# Clean Python bytecode BEFORE building Docker images
echo "Cleaning Python bytecode..."
cd ..
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
cd mle-bench
echo "✅ Python bytecode cleaned"
echo ""

# Check if base mlebench-env image exists (only build once)
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
    echo "✅ Base image mlebench-env already exists (using cached)"
    echo ""
fi

# Build agent_v5_kaggle image
echo "Building agent_v5_kaggle image..."
echo $(pwd)
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
    echo $(pwd)
    #cat debug.py
    docker build --platform=linux/amd64 -t "$IMAGE_TAG" -t "agent_v5_kaggle:latest" \
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

# Create temporary container config with GPU and labels
TMP_CONFIG=$(mktemp /tmp/container_config_XXXXXX.json)
cat > "$TMP_CONFIG" <<EOF
{
    "mem_limit": "80G",
    "shm_size": "16G",
    "nano_cpus": 8e9,
    "gpus": -1,
    "labels": {
        "run_id": "${RUN_ID}",
        "workflow": "mle-bench",
        "image_tag": "${IMAGE_TAG}"
    }
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
    # Cleanup handled by trap
    exit 0
fi

# === RUN AGENT IN FOREGROUND ===
# This is the key change: no background execution, no race conditions
# Python's stdout/stderr stream directly to our stdout
# Logs appear in real-time without docker exec hacks
# Cleanup trap handles containers on any exit (normal, Ctrl+C, cancel)

echo "Starting agent (foreground execution)..."
echo "Logs will stream in real-time..."
echo ""

# Use -u for unbuffered output (real-time log streaming)
DEBUG=1 python -u run_agent.py \
  --agent-id "${AGENT_ID}" \
  --competition-set experiments/splits/custom-set.txt \
  --container-config "$TMP_CONFIG"

# If we reach here, agent completed successfully
echo ""
echo "✅ Agent process completed successfully"

echo ""
echo "=========================================="
echo "Step 4: Check Results"
echo "=========================================="

# Find latest run
RUN_GROUP=$(ls -t runs/ 2>/dev/null | head -1)

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
GRADING_REPORT=$(find "runs/$RUN_GROUP/" -name "*_grading_report.json" -o -name "results.json" 2>/dev/null | head -1)
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
    GRADING_REPORT=$(find "runs/$RUN_GROUP/" -name "*_grading_report.json" -o -name "results.json" 2>/dev/null | head -1)
fi

echo ""
echo "=========================================="
echo "COMPLETE!"
echo "=========================================="
echo "Results in: runs/$RUN_GROUP/"
echo ""

# Find the actual competition directory
COMP_DIR=$(find "runs/$RUN_GROUP/" -maxdepth 1 -type d ! -name "$(basename runs/$RUN_GROUP)" 2>/dev/null | head -1)

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
