#!/bin/bash
# Setup GitHub Actions self-hosted runner on GPU machines
# Run this script on each GPU machine

set -e

echo "=========================================="
echo "GitHub Actions Runner Setup"
echo "=========================================="
echo ""

# Prompt for machine number
read -p "Which GPU machine is this? (1 or 2): " MACHINE_NUM

if [ "$MACHINE_NUM" != "1" ] && [ "$MACHINE_NUM" != "2" ]; then
    echo "❌ ERROR: Please enter 1 or 2"
    exit 1
fi

RUNNER_NAME="gpu-runner-$MACHINE_NUM"
RUNNER_LABELS="gpu,gpu-$MACHINE_NUM"

echo "Configuration:"
echo "  Runner name: $RUNNER_NAME"
echo "  Labels: $RUNNER_LABELS"
echo ""

# Prompt for GitHub token
echo "To get your GitHub token:"
echo "1. Go to: https://github.com/YOUR_ORG/canada-research/settings/actions/runners/new"
echo "2. Select Linux + x64"
echo "3. Copy the token from the './config.sh' command"
echo ""
read -p "Enter GitHub token: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ ERROR: Token cannot be empty"
    exit 1
fi

# Create runner directory
RUNNER_DIR="$HOME/actions-runner-$MACHINE_NUM"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo ""
echo "=========================================="
echo "Step 1: Download Runner"
echo "=========================================="

# Latest runner version (as of 2025-10-14)
# Check for updates at: https://github.com/actions/runner/releases
RUNNER_VERSION="2.329.0"
RUNNER_FILE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
RUNNER_SHA256="194f1e1e4bd02f80b7e9633fc546084d8d4e19f3928a324d512ea53430102e1d"

if [ ! -f "$RUNNER_FILE" ]; then
    echo "Downloading GitHub Actions runner v${RUNNER_VERSION}..."
    curl -o "$RUNNER_FILE" -L \
        "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_FILE}"

    # Verify SHA256 checksum for security
    echo "Verifying checksum..."
    echo "$RUNNER_SHA256  $RUNNER_FILE" | sha256sum --check

    if [ $? -eq 0 ]; then
        echo "✅ Downloaded and verified"
    else
        echo "❌ ERROR: Checksum verification failed!"
        echo "   The downloaded file may be corrupted or tampered with."
        echo "   Removing file..."
        rm -f "$RUNNER_FILE"
        exit 1
    fi
else
    echo "✅ Runner already downloaded"
fi

# Extract
if [ ! -f "config.sh" ]; then
    echo "Extracting runner..."
    tar xzf "$RUNNER_FILE"
    echo "✅ Extracted"
else
    echo "✅ Runner already extracted"
fi

echo ""
echo "=========================================="
echo "Step 2: Configure Runner"
echo "=========================================="

# Check if already configured
if [ -f ".runner" ]; then
    echo "⚠️  Runner already configured"
    read -p "Reconfigure? (y/n): " RECONFIG
    if [ "$RECONFIG" = "y" ]; then
        ./config.sh remove --token "$GITHUB_TOKEN" || true
        rm -f .runner .credentials .credentials_rsaparams
    else
        echo "Skipping configuration"
    fi
fi

if [ ! -f ".runner" ]; then
    echo "Configuring runner..."
    ./config.sh \
        --url https://github.com/YOUR_ORG/canada-research \
        --token "$GITHUB_TOKEN" \
        --name "$RUNNER_NAME" \
        --labels "$RUNNER_LABELS" \
        --work _work \
        --unattended \
        --replace

    echo "✅ Configured"
else
    echo "✅ Already configured"
fi

echo ""
echo "=========================================="
echo "Step 3: Install as Service"
echo "=========================================="

# Install as systemd service
if systemctl is-active --quiet "actions.runner.*" 2>/dev/null; then
    echo "⚠️  Service already running"
    read -p "Reinstall service? (y/n): " REINSTALL
    if [ "$REINSTALL" = "y" ]; then
        sudo ./svc.sh stop || true
        sudo ./svc.sh uninstall || true
    else
        echo "Skipping service installation"
    fi
fi

if ! systemctl is-active --quiet "actions.runner.*" 2>/dev/null; then
    echo "Installing as systemd service..."
    sudo ./svc.sh install
    echo "✅ Service installed"

    echo "Starting service..."
    sudo ./svc.sh start
    echo "✅ Service started"
else
    echo "✅ Service already running"
fi

echo ""
echo "=========================================="
echo "Step 4: Verify Installation"
echo "=========================================="

# Check service status
sleep 2
SERVICE_NAME=$(systemctl list-units --type=service --all | grep "actions.runner" | awk '{print $1}' | head -1)

if [ -n "$SERVICE_NAME" ]; then
    echo "Service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager | head -10
    echo ""
    echo "✅ Service is running!"
else
    echo "⚠️  Could not find service"
fi

# Check runner logs
if [ -f "_diag/Runner_*.log" ]; then
    echo ""
    echo "Recent runner logs:"
    tail -20 _diag/Runner_*.log | tail -10
fi

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Runner installed:"
echo "  Name: $RUNNER_NAME"
echo "  Labels: $RUNNER_LABELS"
echo "  Directory: $RUNNER_DIR"
echo ""
echo "Next steps:"
echo "1. Go to: https://github.com/YOUR_ORG/canada-research/settings/actions/runners"
echo "2. Verify you see: $RUNNER_NAME (Idle)"
echo "3. Repeat this script on the other GPU machine"
echo "4. Add ANTHROPIC_API_KEY to GitHub repo secrets"
echo "5. Test a workflow run!"
echo ""
echo "To check runner status:"
echo "  sudo systemctl status actions.runner.*.service"
echo ""
echo "To view runner logs:"
echo "  tail -f $RUNNER_DIR/_diag/Runner_*.log"
echo ""
echo "To stop runner:"
echo "  sudo $RUNNER_DIR/svc.sh stop"
echo ""
echo "To start runner:"
echo "  sudo $RUNNER_DIR/svc.sh start"
