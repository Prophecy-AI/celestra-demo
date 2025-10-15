# GPU Setup Options for MLE-bench on macOS

## Option 1: Google Colab Pro+ ($50/month)
**Pros**: A100 40GB GPU available, easy setup
**Cons**: Session limits, not persistent

```bash
# In Colab notebook:
!git clone https://github.com/yourusername/canada-research.git
!cd canada-research/mle-bench && pip install -e .
!cd canada-research/mle-bench && python run_agent.py --help
```

## Option 2: Modal.com (Recommended - Pay per use)
**Pros**: A100 GPUs, serverless, only pay for compute time
**Cons**: Requires account setup

```python
# modal_mle_bench.py
import modal

stub = modal.Stub("mle-bench-runner")

# Define the container with GPU
gpu_image = (
    modal.Image.debian_slim()
    .apt_install("git", "wget", "curl")
    .pip_install("torch", "tensorflow", "scikit-learn")
    .run_commands("git clone https://github.com/openai/mle-bench.git")
    .pip_install("-e mle-bench")
)

@stub.function(
    image=gpu_image,
    gpu="A100",  # or "A10" for cheaper option
    timeout=86400,  # 24 hours
    memory=81920,  # 80 GB
)
def run_mle_agent(competition_id):
    import subprocess
    result = subprocess.run(
        ["python", "run_agent.py", "--competition", competition_id],
        capture_output=True,
        text=True
    )
    return result.stdout

# Run with: modal run modal_mle_bench.py
```

## Option 3: AWS EC2 with GPU
**Instance Type**: g5.xlarge (24GB A10) or p3.2xlarge (16GB V100)
**Cost**: ~$1-4/hour

```bash
# After launching instance:
ssh ubuntu@your-instance-ip
git clone https://github.com/openai/mle-bench.git
cd mle-bench
pip install -e .

# Install Docker and NVIDIA Container Toolkit
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test GPU access
sudo docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## Option 4: RunPod.io (Cheapest for A100)
**Cost**: ~$2.50/hour for A100 40GB
**Setup**: Pre-configured ML templates available

```bash
# After launching pod:
cd /workspace
git clone https://github.com/openai/mle-bench.git
cd mle-bench
pip install -e .
```

## Option 5: Local Development Without GPU (Limited)

For testing and development only - NOT for full evaluation:

### Install Docker Desktop for Mac
```bash
# Download from https://www.docker.com/products/docker-desktop/
# Or use Homebrew:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install --cask docker
```

### Use CPU-optimized approach
```python
# Modify agent to detect no GPU and use simple models
import torch

if torch.cuda.is_available():
    device = 'cuda'
    model = ComplexCNN()
else:
    # Fallback to simple models
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_jobs=-1)  # Use all CPU cores
```

## Recommended Approach for MLE-bench

Given you need to process 3.3TB of data with proper GPU:

1. **For Development**: Use Modal.com or Colab to test on small competitions
2. **For Full Evaluation**: Use AWS/RunPod with persistent storage
3. **Budget Option**: Use spot instances on AWS (70-90% cheaper but can be interrupted)

## Quick Start with Modal (Easiest)

```bash
# Install modal
pip install modal

# Authenticate
modal token new

# Create a simple test script
cat > test_gpu.py << EOF
import modal

stub = modal.Stub()

@stub.function(gpu="A100")
def test_gpu():
    import torch
    if torch.cuda.is_available():
        return f"GPU: {torch.cuda.get_device_name(0)}"
    return "No GPU found"

@stub.local_entrypoint()
def main():
    result = test_gpu.remote()
    print(result)
EOF

# Run it
modal run test_gpu.py
```

## Cost Estimates

| Service | GPU Type | Cost/Hour | 24hr Run | 
|---------|----------|-----------|----------|
| Colab Pro+ | A100 40GB | $50/month | Included |
| Modal | A100 40GB | ~$3.50 | ~$84 |
| AWS Spot | A10 24GB | ~$0.80 | ~$19 |
| RunPod | A100 40GB | ~$2.50 | ~$60 |

## Important Notes

1. **Apple Silicon MPS**: While PyTorch supports MPS (Metal) on Mac, MLE-bench expects NVIDIA CUDA
2. **Docker on Mac**: Even with Docker Desktop, you can't access NVIDIA GPUs from macOS
3. **Best Practice**: Develop locally, run evaluations in cloud


