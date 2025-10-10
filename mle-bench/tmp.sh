
# Find latest run
RUN_GROUP=$(ls -t runs/ | head -1)
echo "Run group: $RUN_GROUP"
echo ""

echo ""
echo "=========================================="
echo "Step 4: Grade Submission"
echo "=========================================="

# Generate submission JSONL
python experiments/make_submission.py \
  --metadata runs/$RUN_GROUP/metadata.json \
  --output runs/$RUN_GROUP/submission.jsonl

# Grade
mlebench grade \
  --submission runs/$RUN_GROUP/submission.jsonl \
  --output-dir runs/$RUN_GROUP
