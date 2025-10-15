#!/bin/bash
set -e  # Exit on error
set -x  # Print commands (debug mode)

echo "========================================="
echo "Agent V5 Kaggle - GPU-Aware Start"
echo "========================================="
echo "Competition ID: ${COMPETITION_ID}"
echo "Code dir: ${CODE_DIR}"
echo "Data dir: /home/data"
echo "Submission dir: ${SUBMISSION_DIR}"
echo "========================================="

# Check for GPU availability
echo "Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
    echo "GPU detected, using GPU-aware runner"
    RUNNER_SCRIPT="${AGENT_DIR}/runner_gpu.py"
else
    echo "No GPU detected, using standard runner"
    RUNNER_SCRIPT="${AGENT_DIR}/runner.py"
fi

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate agent

# Test GPU in Python
echo "Testing GPU in Python environment..."
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
else:
    print('No GPU available - will use CPU')
" || echo "PyTorch GPU check failed"

# Set working directory to CODE_DIR (agent's workspace)
cd ${CODE_DIR}

# Start GPU monitor in background (if GPU available)
if command -v nvidia-smi &> /dev/null; then
    echo "Starting GPU monitor in background..."
    (while true; do
        echo "=== GPU Status at $(date) ===" >> ${LOGS_DIR}/gpu_monitor.log
        nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits >> ${LOGS_DIR}/gpu_monitor.log
        sleep 30
    done) &
    GPU_MONITOR_PID=$!
    echo "GPU monitor PID: ${GPU_MONITOR_PID}"
fi

# Run the Kaggle agent (unbuffered for real-time logs)
echo "Starting agent with runner: ${RUNNER_SCRIPT}"
python -u ${RUNNER_SCRIPT} 2>&1 | tee ${LOGS_DIR}/agent.log

# Stop GPU monitor if running
if [ ! -z "${GPU_MONITOR_PID}" ]; then
    kill ${GPU_MONITOR_PID} 2>/dev/null || true
    echo "GPU monitor stopped"
fi

# Check if submission was created
if [ -f ${SUBMISSION_DIR}/submission.csv ]; then
    echo "✅ Submission file created"
    echo "File size: $(wc -c < ${SUBMISSION_DIR}/submission.csv) bytes"
    echo "Line count: $(wc -l < ${SUBMISSION_DIR}/submission.csv) lines"
    echo ""
    echo "First 5 lines:"
    head -5 ${SUBMISSION_DIR}/submission.csv
    echo ""
    
    # Show GPU usage summary if available
    if [ -f ${LOGS_DIR}/gpu_monitor.log ]; then
        echo "GPU Usage Summary:"
        tail -5 ${LOGS_DIR}/gpu_monitor.log
    fi
    
    # Validate submission (optional, but helpful)
    if [ -f /home/validate_submission.sh ]; then
        echo "Running validation..."
        bash /home/validate_submission.sh ${SUBMISSION_DIR}/submission.csv || true
    fi
else
    echo "❌ ERROR: No submission file found at ${SUBMISSION_DIR}/submission.csv"
    echo "Contents of ${SUBMISSION_DIR}:"
    ls -la ${SUBMISSION_DIR}
    exit 1
fi

echo "========================================="
echo "Agent V5 Kaggle - Complete"
echo "========================================="
