#!/bin/bash
# Setup new GPU machine for GitHub Actions runner
# Run as: bash setup-new-runner.sh

set -e

echo "=========================================="
echo "Setting up new GitHub Actions GPU runner"
echo "=========================================="

# Install git-lfs
sudo apt-get update
sudo apt-get install -y git-lfs ca-certificates curl

# Clone repo
cd ~
git clone https://github.com/Prophecy-AI/canada-research.git
cd canada-research
git lfs install
git checkout workflow

# Install Docker
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install NVIDIA container toolkit
wget -nv -O- https://lambda.ai/install-lambda-stack.sh | 
I_AGREE_TO_THE_CUDNN_LICENSE=1 sh -

sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Add user to docker group
sudo usermod -aG docker ubuntu

# Setup Python venv and install mlebench
sudo apt-get install python3-full
cd ~/canada-research/mle-bench
python3 -m venv venv
source venv/bin/activate
pip install -e .

# setup kaggle.json
vim ~/.config/kaggle/kaggle.json

# Fix permissions
sudo chown -R ubuntu:ubuntu ~/.cache 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Reboot to apply docker group changes:"
echo "     sudo reboot"
echo ""
echo "2. After reboot, setup GitHub Actions runner:"
echo "     cd ~/canada-research"
echo "     ./scripts/setup-runner.sh"
echo ""
echo "3. Add secrets to repo:"
echo "     ANTHROPIC_API_KEY"
