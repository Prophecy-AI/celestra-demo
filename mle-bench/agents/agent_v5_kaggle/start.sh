#!/bin/bash
set -e  # Exit on error
set -x  # Print commands (debug mode)

echo "========================================="
echo "Agent V5 Kaggle - Start"
echo "========================================="
echo "Competition ID: ${COMPETITION_ID}"
echo "Code dir: ${CODE_DIR}"
echo "Data dir: /home/data"
echo "Submission dir: ${SUBMISSION_DIR}"
echo "========================================="

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate agent

# Set working directory to CODE_DIR (agent's workspace)
cd ${CODE_DIR}

# Run the Kaggle agent (unbuffered for real-time logs)
python -u ${AGENT_DIR}/runner.py 2>&1 | tee ${LOGS_DIR}/agent.log

# Check if submission was created
if [ -f ${SUBMISSION_DIR}/submission.csv ]; then
    echo "✅ Submission file created"
    echo "File size: $(wc -c < ${SUBMISSION_DIR}/submission.csv) bytes"
    echo "Line count: $(wc -l < ${SUBMISSION_DIR}/submission.csv) lines"
    echo ""
    echo "First 5 lines:"
    head -5 ${SUBMISSION_DIR}/submission.csv
    echo ""

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
