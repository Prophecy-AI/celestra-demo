# MLE-Bench Agent V5 Kaggle - Setup Instructions

## SSH Access

1. **Connect to the server:**
   ```bash
   ssh ubuntu@209-20-159-127
   ```

2. **Switch to root user:**
   ```bash
   sudo su
   ```

3. **Navigate to the project:**
   ```bash
   cd /home/ubuntu/research/canada-research/mle-bench
   ```

4. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

5. **Set your Anthropic API key:**
   ```bash
   export ANTHROPIC_API_KEY=your-api-key-here
   ```

6. **Run the agent:**
   ```bash
   ./RUN_AGENT_V5_KAGGLE.sh
   ```

## What the Script Does

- Builds the Docker image with agent_v5_kaggle
- Prepares the competition datasets
- Runs the agent on the competitions in `experiments/splits/custom-set.txt`
- Shows live logs from the agent
- Grades the submissions automatically

## Viewing Results

After completion, results are saved in `runs/[timestamp]/`:
- **Logs:** `runs/[latest]/*/logs/agent.log`
- **Code:** `runs/[latest]/*/code/`
- **Submission:** `runs/[latest]/*/submission/submission.csv`
- **Grading:** `runs/[latest]/*_grading_report.json`

## Important Notes

- Make sure git-lfs is installed: `git lfs pull` (already done on this server)
- The agent uses GPU resources, so coordinate with teammates to avoid conflicts
- Logs are streamed in real-time during execution
