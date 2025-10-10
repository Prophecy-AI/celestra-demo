# MLE-Bench Agent V5 Kaggle - Setup Instructions

## Important Notes

- [Important] This is a very early version of this pipeline, my end goal is to implement a CI/CD like pipeline to run mle-bench (or a subset of it) manually via GitHub Actions on push. Currently your changes to the agent aren't automatically reflected in this agent. **You have to `git pull` on the server's `research/canada-research` path before testing to apply your changes from remote.**


- You can do all these steps either from terminal or first ssh via VSCode and then use VSCode's terminal
- The agent uses GPU resources, so coordinate with teammates to avoid conflicts

## SSH Access

1. **Connect to the server:**
   ```bash
   ssh -i [the .pem file for this server] ubuntu@209-20-159-127
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