# Agent V5 Kaggle - Autonomous Kaggle Competition Agent

Built on agent_v5 framework with custom system prompt for Kaggle competitions.

## Quick Start

### 1. Set Environment Variables

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 2. Build Docker Image

```bash
cd /home/ubuntu/canada-research/mle-bench

export SUBMISSION_DIR=/home/submission
export LOGS_DIR=/home/logs
export CODE_DIR=/home/code
export AGENT_DIR=/home/agent

docker build --platform=linux/amd64 -t agent_v5_kaggle \
  agents/agent_v5_kaggle/ \
  --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
  --build-arg LOGS_DIR=$LOGS_DIR \
  --build-arg CODE_DIR=$CODE_DIR \
  --build-arg AGENT_DIR=$AGENT_DIR
```

### 3. Run on Single Competition (spaceship-titanic)

```bash
cd /home/ubuntu/canada-research/mle-bench

python run_agent.py \
  --agent-id agent_v5_kaggle \
  --competition-set experiments/splits/spaceship-titanic.txt
```

### 4. Check Results

```bash
# Find latest run
RUN_GROUP=$(ls -t runs/ | head -1)
echo "Run group: $RUN_GROUP"

# View submission
cat runs/$RUN_GROUP/spaceship-titanic/submission/submission.csv | head

# View logs
cat runs/$RUN_GROUP/spaceship-titanic/logs/*.log

# View generated code
ls -la runs/$RUN_GROUP/spaceship-titanic/code/
```

### 5. Grade Submission

```bash
# Generate submission JSONL
python experiments/make_submission.py \
  --metadata runs/$RUN_GROUP/metadata.json \
  --output runs/$RUN_GROUP/submission.jsonl

# Grade with mle-bench
mlebench grade \
  --submission runs/$RUN_GROUP/submission.jsonl \
  --output-dir runs/$RUN_GROUP
```

## Architecture

```
agent_v5_kaggle/
├── config.yaml                     # mle-bench agent config
├── Dockerfile                      # Docker image definition
├── start.sh                        # Entry point script
├── runner.py                       # Bridge: mle-bench → agent_v5
├── requirements.txt                # Python dependencies
├── debug.py                        # Debug logging
├── security/                       # Path validation
├── observability/                  # Langfuse integration
└── agent_v5/
    ├── agent.py                    # ResearchAgent (base)
    ├── kaggle_agent.py            # KaggleAgent (extends ResearchAgent)
    ├── prompts/
    │   └── kaggle_system_prompt.py # Kaggle-specific system prompt
    └── tools/                      # All 7 core tools
        ├── bash.py
        ├── read.py
        ├── write.py
        ├── edit.py
        ├── glob.py
        ├── grep.py
        └── todo.py
```

## How It Works

1. **mle-bench** creates Docker container with competition data
2. **start.sh** activates conda environment and runs runner.py
3. **runner.py** creates KaggleAgent with competition context
4. **KaggleAgent** extends ResearchAgent with Kaggle-specific system prompt
5. **System prompt** guides agent through ML workflow (EDA → baseline → iteration → submission)
6. **Tools** (Bash, Read, Write, etc.) enable agent to execute Python scripts, read CSVs, etc.
7. **Agent** outputs submission.csv to /home/submission/
8. **mle-bench** extracts submission and evaluates it

## System Prompt Strategy

The Kaggle system prompt includes:

- **Competition instructions** (from /home/instructions.txt)
- **7-step workflow**: Understand → EDA → Baseline → Feature Eng → Iteration → Submission → Validation
- **Python/ML code templates**: XGBoost, LightGBM, cross-validation, preprocessing
- **Submission format rules**: Match sample_submission.csv exactly
- **Time management**: Allocate time wisely across steps
- **Critical rules**: Always use CV, apply same preprocessing to train/test, etc.

## Debugging

Enable debug logs:

```bash
# In config.yaml, already set:
env_vars:
  DEBUG: "1"
```

View debug output in logs:

```bash
cat runs/$RUN_GROUP/spaceship-titanic/logs/*.log | grep "→\|✓\|✗"
```

## Customization

### Add Domain-Specific Tools

Edit `agent_v5/kaggle_agent.py`:

```python
def _register_kaggle_tools(self):
    from agent_v5.tools.my_custom_tool import MyCustomTool
    self.tools.register(MyCustomTool(self.workspace_dir))
```

### Modify System Prompt

Edit `agent_v5/prompts/kaggle_system_prompt.py`:

```python
KAGGLE_SYSTEM_PROMPT_TEMPLATE = """
Your custom instructions here...
"""
```

## Testing

Run on simple competitions first:

```bash
# Easiest (tabular classification)
python run_agent.py --agent-id agent_v5_kaggle \
  --competition-set experiments/splits/spaceship-titanic.txt

# Medium (image classification)
python run_agent.py --agent-id agent_v5_kaggle \
  --competition-set experiments/splits/aerial-cactus-identification.txt

# Hard (text/NLP)
python run_agent.py --agent-id agent_v5_kaggle \
  --competition-set experiments/splits/detecting-insults-in-social-commentary.txt
```

## Expected Behavior

**On spaceship-titanic** (binary classification):

1. Agent reads instructions.txt
2. Uses Glob to find train.csv, test.csv
3. Writes eda.py to explore data
4. Writes baseline.py with RandomForest
5. Writes xgboost_model.py for better model
6. Writes submission.py to generate predictions
7. Creates /home/submission/submission.csv
8. Validates format

**Time**: 15-30 minutes on simple competitions

**Accuracy**: Should beat random baseline (>50% for binary classification)

## Troubleshooting

**No submission file created:**
- Check logs for errors: `cat runs/$RUN_GROUP/*/logs/*.log`
- Agent may have hit timeout (default 24hrs)
- Python script may have failed - check code directory

**Submission format invalid:**
- Agent should validate against sample_submission.csv
- Check column names, row count, dtypes

**Low accuracy:**
- Agent focuses on valid submission first, accuracy second
- For better results: increase time limit, add more ML libraries, refine system prompt

## Next Steps

1. ✅ Run on spaceship-titanic
2. Test on 5-10 diverse competitions
3. Benchmark against dummy agent and other mle-bench agents
4. Refine system prompt based on failure modes
5. Add competition type detection (classification vs regression)
6. Add ensemble strategies
7. Deploy at scale on all 75+ competitions
