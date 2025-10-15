# GitHub Actions Setup for MLE-Bench (Concurrency: 2)

Complete setup guide for running MLE-bench experiments on 2 GPU machines with GitHub Actions.

---

## **Overview**

This setup enables:
- ✅ **Concurrent runs**: 2 experiments can run simultaneously (one per GPU)
- ✅ **Branch selection**: Run experiments on any branch via GitHub UI
- ✅ **Competition sets**: Choose from Lite (21), Medium (38), High (14), or custom
- ✅ **Dry run mode**: Validate setup without executing
- ✅ **Auto cleanup**: Docker images/containers cleaned after each run
- ✅ **Results artifacts**: Download logs, code, and submissions from GitHub

---

## **Prerequisites**

Before starting, ensure you have:

- [ ] **2 GPU machines** (Ubuntu, identical setup)
- [ ] **SSH access** to both machines (same `.pem` key)
- [ ] **Docker + NVIDIA drivers** installed on both
- [ ] **Admin access** to GitHub repository
- [ ] **Repository is private** (for secure secrets)

---

## **Part 1: Initial Setup (One-Time)**

### **Step 1: Commit Modified Files**

On your local machine:

```bash
cd /Users/iliaaa/ilia/work/celestra/canada-research/canada-research

# Check what was modified
git status

# You should see:
#   modified:   mle-bench/RUN_AGENT_V5_KAGGLE.sh
#   modified:   .gitignore
#   new file:   .github/workflows/run-mle-bench.yml
#   new file:   scripts/setup-runner.sh

# Review changes
git diff mle-bench/RUN_AGENT_V5_KAGGLE.sh
git diff .gitignore

# Commit
git add .github/workflows/run-mle-bench.yml
git add scripts/setup-runner.sh
git add mle-bench/RUN_AGENT_V5_KAGGLE.sh
git add .gitignore

git commit -m "Add GitHub Actions workflow with concurrency support

- Modified RUN_AGENT_V5_KAGGLE.sh to support workspace-awareness and unique Docker tags
- Added GitHub Actions workflow with dry run mode and GPU targeting
- Added setup-runner.sh helper script
- Updated .gitignore for runner artifacts"

# Push to GitHub
git push origin main
```

### **Step 2: Update Setup Script with Your Repo URL**

Before running the setup script, update it with your actual GitHub org/repo:

```bash
# Edit scripts/setup-runner.sh
# Replace "YOUR_ORG" with your actual GitHub organization name
sed -i '' 's/YOUR_ORG/celestra/g' scripts/setup-runner.sh

# Commit the change
git add scripts/setup-runner.sh
git commit -m "Update setup script with actual repo URL"
git push origin main
```

---

## **Part 2: Setup GPU Machine 1**

### **Step 1: SSH into GPU Machine 1**

```bash
ssh -i your-key.pem ubuntu@209.20.159.127
sudo su
cd /home/ubuntu
```

### **Step 2: Clone Repository (if not already present)**

```bash
# If not already cloned:
git clone https://github.com/celestra/canada-research.git
cd canada-research

# If already cloned, pull latest:
cd canada-research
git pull origin main
```

### **Step 3: Get GitHub Runner Token**

On your computer, in a browser:

1. Go to: `https://github.com/celestra/canada-research/settings/actions/runners/new`
2. Select: **Linux** and **x64**
3. Copy the **token** from the command that looks like:
   ```
   ./config.sh --url https://github.com/celestra/canada-research --token ABCD1234...
   ```
4. Keep this browser tab open (you'll need it for GPU Machine 2)

### **Step 4: Run Setup Script**

```bash
# Make script executable (if not already)
chmod +x scripts/setup-runner.sh

# Run setup
./scripts/setup-runner.sh

# When prompted:
#   Which GPU machine is this? (1 or 2): 1
#   Enter GitHub token: <paste token from browser>

# Script will:
# - Download GitHub Actions runner
# - Configure it as "gpu-runner-1" with labels "gpu,gpu-1"
# - Install as systemd service
# - Start the service
# - Verify it's running
```

### **Step 5: Verify Runner is Active**

```bash
# Check service status
sudo systemctl status actions.runner.*.service

# You should see: "Active: active (running)"

# Check runner logs
tail -f ~/actions-runner-1/_diag/Runner_*.log
# Press Ctrl+C to exit

# On GitHub, go to:
# https://github.com/celestra/canada-research/settings/actions/runners
# You should see: gpu-runner-1 (Idle) with green dot
```

---

## **Part 3: Setup GPU Machine 2**

### **Step 1: SSH into GPU Machine 2**

```bash
# On a new terminal
ssh -i your-key.pem ubuntu@XXX.XXX.XXX.XXX  # Your GPU Machine 2 IP
sudo su
cd /home/ubuntu
```

### **Step 2: Clone Repository**

```bash
git clone https://github.com/celestra/canada-research.git
cd canada-research
```

### **Step 3: Get New GitHub Runner Token**

**IMPORTANT**: You need a NEW token for the second runner!

1. Go back to: `https://github.com/celestra/canada-research/settings/actions/runners/new`
2. Click **New self-hosted runner** again
3. Copy the NEW token (it's different from Machine 1's token)

### **Step 4: Run Setup Script**

```bash
chmod +x scripts/setup-runner.sh
./scripts/setup-runner.sh

# When prompted:
#   Which GPU machine is this? (1 or 2): 2
#   Enter GitHub token: <paste NEW token from browser>
```

### **Step 5: Verify Both Runners**

On GitHub:
- Go to: `https://github.com/celestra/canada-research/settings/actions/runners`
- You should see:
  - ✅ **gpu-runner-1** (Idle) - labels: gpu, gpu-1
  - ✅ **gpu-runner-2** (Idle) - labels: gpu, gpu-2

---

## **Part 4: Add GitHub Secrets**

### **Step 1: Add ANTHROPIC_API_KEY**

1. Go to: `https://github.com/celestra/canada-research/settings/secrets/actions`
2. Click: **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: `your-anthropic-api-key-here`
5. Click: **Add secret**

### **Step 2: Verify Secret is Set**

- You should see `ANTHROPIC_API_KEY` in the list
- Note: The value is hidden (only shows "Updated X seconds ago")

---

## **Part 5: Test the Setup**

### **Test 1: Dry Run (Quick Validation)**

1. Go to: `https://github.com/celestra/canada-research/actions`
2. Click: **Run MLE-Bench Agent** (left sidebar)
3. Click: **Run workflow** (top right)
4. Fill in:
   - **Use workflow from**: `main`
   - **Competition set**: `custom-set.txt`
   - **Custom competitions**: (leave empty)
   - **Dry run mode**: ✅ **Check this box**
   - **Target GPU**: `any`
5. Click: **Run workflow** (green button)

**Expected result:**
- Workflow starts in ~5 seconds
- Completes in ~30 seconds
- Shows "🔍 DRY RUN" messages in logs
- No actual Docker build or agent run

### **Test 2: Single Real Run**

1. Same as above, but:
   - **Dry run mode**: ❌ **Uncheck**
   - **Custom competitions**: Enter `aerial-cactus-identification`
2. Click: **Run workflow**

**Expected result:**
- Builds Docker image (~5 min)
- Prepares competition data
- Runs agent (~10-30 min for simple competition)
- Uploads results as artifacts
- Shows grading results in logs

### **Test 3: Concurrent Runs (The Big Test!)**

**Person 1:**
1. Checkout a test branch: `git checkout -b test-branch-a`
2. Make a small change (e.g., add comment to agent code)
3. Push: `git push origin test-branch-a`
4. Go to Actions → Run workflow
5. Select:
   - **Branch**: `test-branch-a`
   - **Competition set**: `custom-set.txt`
   - **Target GPU**: `gpu-1` (force to Machine 1)
6. Click Run

**Person 2 (or you in another tab):**
1. Checkout another branch: `git checkout -b test-branch-b`
2. Make a different change
3. Push: `git push origin test-branch-b`
4. Go to Actions → Run workflow
5. Select:
   - **Branch**: `test-branch-b`
   - **Competition set**: `custom-set.txt`
   - **Target GPU**: `gpu-2` (force to Machine 2)
6. Click Run

**Expected result:**
- Both jobs start simultaneously
- Job 1 runs on gpu-runner-1 (Machine 1)
- Job 2 runs on gpu-runner-2 (Machine 2)
- Both complete independently
- No conflicts, no errors
- Both produce separate artifacts

---

## **Part 6: Daily Usage**

### **Running an Experiment**

1. Go to: `https://github.com/celestra/canada-research/actions`
2. Click: **Run MLE-Bench Agent**
3. Click: **Run workflow**
4. Configure:
   - **Branch**: Select your branch (or `main`)
   - **Competition set**: Choose from dropdown
     - `custom-set.txt` - Whatever is in that file
     - `low.txt (Lite - 21 competitions)` - All easy ones
     - `medium.txt (38 competitions)` - Medium difficulty
     - `high.txt (14 competitions)` - Hard ones
   - **Custom competitions**: (optional) Override with specific competitions:
     ```
     aerial-cactus-identification
     spaceship-titanic
     ```
   - **Dry run**: Uncheck (unless validating)
   - **Target GPU**:
     - `any` - Use any available GPU
     - `gpu-1` - Force to Machine 1
     - `gpu-2` - Force to Machine 2
5. Click: **Run workflow**

### **Monitoring Progress**

1. Click on the workflow run (appears in list)
2. Click on job: **run-agent**
3. Watch live logs streaming
4. See steps:
   - Show run configuration
   - Clean workspace
   - Checkout code
   - Setup competition set
   - Run MLE-Bench (main step - takes hours)
   - Upload results
   - Display results summary
   - Cleanup Docker
   - Cleanup workspace

### **Downloading Results**

1. Wait for workflow to complete
2. Scroll to bottom of workflow page
3. See **Artifacts** section
4. Download:
   - `mle-bench-results-branchname-run123.zip` - Full results
   - `grading-report-branchname-run123.zip` - Grading JSON

### **Checking Runner Status**

SSH into either machine:
```bash
# Check if runner is active
sudo systemctl status actions.runner.*.service

# View runner logs
tail -f ~/actions-runner-1/_diag/Runner_*.log  # or actions-runner-2

# See what it's currently processing
ps aux | grep python | grep run_agent
```

---

## **Troubleshooting**

### **Runner Shows Offline**

```bash
# SSH into the machine
ssh -i key.pem ubuntu@machine-ip
sudo su

# Check service
sudo systemctl status actions.runner.*.service

# If stopped, restart
cd ~/actions-runner-1  # or actions-runner-2
sudo ./svc.sh stop
sudo ./svc.sh start

# Check logs
tail -50 _diag/Runner_*.log
```

### **Workflow Fails: "No runner found"**

- Both runners might be busy
- Wait for current jobs to finish
- Or: Add more runners (see "Adding More Runners" below)

### **Docker Build Fails: "No space left on device"**

```bash
# SSH into machine
# Clean up old Docker resources
docker system prune -af --volumes

# Check disk space
df -h
```

### **Job Stuck: "Waiting for a runner"**

- All runners are busy
- Job will start when a runner becomes available
- Or: Cancel job and specify target GPU with `target_gpu: gpu-1` or `gpu-2`

### **Can't See Runners in GitHub**

- Check runner service is running (see above)
- Regenerate token and reconfigure:
  ```bash
  cd ~/actions-runner-1
  ./config.sh remove
  # Get new token from GitHub
  ./config.sh --url ... --token NEW_TOKEN --name gpu-runner-1 --labels gpu,gpu-1
  sudo ./svc.sh install
  sudo ./svc.sh start
  ```

---

## **Advanced: Adding More Runners**

To support concurrency: 3 or higher:

1. Get a 3rd GPU machine
2. Run setup script:
   ```bash
   ./scripts/setup-runner.sh
   # Enter: 3 (for gpu-runner-3)
   ```
3. Update workflow file:
   - Add `gpu-3` to `target_gpu` options

**Or: Add 2nd runner on same machine** (if machine has 2 GPUs):

```bash
# On GPU Machine 1
cd ~
mkdir actions-runner-1b
cd actions-runner-1b

# Download and extract runner (same as setup script)
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L ...
tar xzf actions-runner-linux-x64-2.311.0.tar.gz

# Configure with different name and GPU label
./config.sh \
  --url https://github.com/celestra/canada-research \
  --token NEW_TOKEN \
  --name gpu-runner-1b \
  --labels gpu,gpu-1,gpu-1b \
  --work _work

# Install and start
sudo ./svc.sh install
sudo ./svc.sh start
```

---

## **Maintenance**

### **Updating Runner Software**

**Current version installed by script: v2.329.0** (latest as of 2025-10-14)

GitHub will notify you when updates are available. The runner also supports automatic updates.

To manually update:

```bash
# 1. Check for new version at https://github.com/actions/runner/releases

# 2. Update the setup script
cd /home/ubuntu/canada-research
# Edit scripts/setup-runner.sh and update:
#   RUNNER_VERSION="2.NEW.VERSION"
#   RUNNER_SHA256="new-sha256-checksum"

# 3. Stop and remove old runner
cd ~/actions-runner-1
sudo ./svc.sh stop
./config.sh remove --token YOUR_TOKEN

# 4. Download new version (example for v2.329.0)
RUNNER_VERSION="2.329.0"
curl -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz -L \
  https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# 5. Verify checksum (get from releases page)
echo "194f1e1e4bd02f80b7e9633fc546084d8d4e19f3928a324d512ea53430102e1d  actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" | sha256sum --check

# 6. Extract
tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# 7. Reconfigure (same settings)
./config.sh --url https://github.com/YOUR_ORG/canada-research \
  --token NEW_TOKEN \
  --name gpu-runner-1 \
  --labels gpu,gpu-1 \
  --work _work

# 8. Reinstall service
sudo ./svc.sh install
sudo ./svc.sh start
```

**Note**: The setup script includes SHA256 verification for security. Always verify checksums when downloading!

### **Monitoring Disk Usage**

```bash
# Check disk space
df -h

# Clean Docker (safe)
docker system prune -f

# Aggressive clean (removes all unused images)
docker system prune -af --volumes
```

### **Restarting After Server Reboot**

Runner service auto-starts on boot, but verify:

```bash
sudo systemctl status actions.runner.*.service
# If not running:
cd ~/actions-runner-1
sudo ./svc.sh start
```

---

## **Architecture Diagram**

```
┌─────────────────────────────────────────────────────┐
│              GitHub.com (Cloud)                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  Repository: canada-research                 │    │
│  │  ┌────────────────────────────────────────┐ │    │
│  │  │  Actions Tab                            │ │    │
│  │  │  - Run MLE-Bench Agent (workflow)      │ │    │
│  │  │  - Job Queue: [Job 1] [Job 2]         │ │    │
│  │  └────────────────────────────────────────┘ │    │
│  │                                              │    │
│  │  Secrets: ANTHROPIC_API_KEY                 │    │
│  └─────────────────────────────────────────────┘    │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
       Poll for jobs       Poll for jobs
               │                  │
   ┌───────────▼─────────┐    ┌──▼──────────────────┐
   │  GPU Machine 1      │    │  GPU Machine 2       │
   │  209.20.159.127     │    │  XXX.XXX.XXX.XXX     │
   │                     │    │                      │
   │  gpu-runner-1       │    │  gpu-runner-2        │
   │  (systemd service)  │    │  (systemd service)   │
   │                     │    │                      │
   │  Workspace:         │    │  Workspace:          │
   │  ~/actions-runner-1/│    │  ~/actions-runner-2/ │
   │   _work/            │    │   _work/             │
   │    canada-research/ │    │    canada-research/  │
   │                     │    │                      │
   │  Docker + NVIDIA    │    │  Docker + NVIDIA     │
   │  GPU: Tesla/A100    │    │  GPU: Tesla/A100     │
   └─────────────────────┘    └──────────────────────┘
```

---

## **Summary**

You now have:
- ✅ 2 GPU machines running GitHub Actions runners
- ✅ Concurrent execution (2 jobs at once)
- ✅ Web UI for triggering runs (no SSH needed)
- ✅ Automatic cleanup and artifact uploads
- ✅ Dry run mode for validation
- ✅ Full isolation (each run has own workspace and Docker image)

**Next steps:**
1. Run test experiments on both machines
2. Share GitHub repo access with team
3. Train team on using Actions UI
4. Monitor and adjust GPU memory limits if needed
