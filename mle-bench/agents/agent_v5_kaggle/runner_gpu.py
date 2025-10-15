"""
GPU-aware bridge between mle-bench environment and agent_v5 KaggleAgent
"""
import asyncio
import os
import sys
from pathlib import Path

# Add agent_v5 to path
AGENT_DIR = os.environ.get('AGENT_DIR', '/home/agent')
sys.path.insert(0, AGENT_DIR)

from kaggle_agent_gpu import KaggleAgentGPU
from debug import log


async def main():
    """Run Kaggle competition agent with GPU support"""
    
    # Get environment variables from mle-bench
    data_dir = "/home/data"
    code_dir = os.environ.get('CODE_DIR', '/home/code')
    submission_dir = os.environ.get('SUBMISSION_DIR', '/home/submission')
    logs_dir = os.environ.get('LOGS_DIR', '/home/logs')
    instructions_path = "/home/instructions.txt"
    competition_id = os.environ.get('COMPETITION_ID', 'unknown')
    
    log(f"🏆 Starting Kaggle Agent (GPU-aware) for: {competition_id}")
    
    # Check GPU availability
    try:
        import torch
        if torch.cuda.is_available():
            log(f"✅ GPU DETECTED: {torch.cuda.get_device_name(0)}")
            log(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            log("⚠️ NO GPU DETECTED - will use CPU (slower)")
    except ImportError:
        log("⚠️ PyTorch not available for GPU check")
    
    log(f"📊 Data: {data_dir}")
    log(f"💻 Workspace: {code_dir}")
    log(f"📤 Submission: {submission_dir}")
    
    # Create directories
    Path(code_dir).mkdir(exist_ok=True, parents=True)
    Path(submission_dir).mkdir(exist_ok=True, parents=True)
    Path(logs_dir).mkdir(exist_ok=True, parents=True)
    
    # Create agent
    agent = KaggleAgentGPU(
        session_id=competition_id,
        workspace_dir=code_dir,
        data_dir=data_dir,
        submission_dir=submission_dir,
        instructions_path=instructions_path
    )
    
    # Initial message with GPU emphasis
    initial_message = (
        f"You are competing in: {competition_id}\n\n"
        f"CRITICAL: First check GPU availability and adjust your approach!\n"
        f"- If GPU available: Use deep learning with progress tracking\n"
        f"- If CPU only: Use simpler models (RandomForest, XGBoost)\n\n"
        f"Data: {data_dir}/\n"
        f"Submission: {submission_dir}/submission.csv\n\n"
        f"Start by:\n"
        f"1. Check GPU with torch.cuda.is_available()\n"
        f"2. Read instructions at {instructions_path}\n"
        f"3. Quick EDA with progress prints\n"
        f"4. Train model with FREQUENT progress updates"
    )
    
    log("→ Starting agent run")
    
    # Track progress
    progress_counter = 0
    last_tool = ""
    
    try:
        async for message in agent.run(initial_message):
            if message.get("type") == "text_delta":
                text = message["text"]
                print(text, end="", flush=True)
                
                # Track progress indicators in text
                if any(word in text.lower() for word in ['epoch', 'fold', 'score', 'loss']):
                    progress_counter += 1
                    if progress_counter % 5 == 0:
                        log(f"📊 Progress update #{progress_counter}")
                        
            elif message.get("type") == "tool_execution":
                tool_name = message["tool_name"]
                last_tool = tool_name
                log(f"🔧 Tool: {tool_name}")
                
                # Special handling for background tasks
                if tool_name == "Bash" and "background" in str(message.get("input", "")):
                    log("   Running in background - use ReadBashOutput to monitor")
                    
    except Exception as e:
        log(f"❌ Agent error: {e}", 2)
        print(f"\n\nERROR: {e}\n", flush=True)
        sys.exit(1)
    
    print("\n")
    log("✓ Agent run complete")
    
    # Check if submission was created
    submission_path = Path(submission_dir) / "submission.csv"
    if submission_path.exists():
        log(f"✅ Submission created: {submission_path}")
        log(f"   Size: {submission_path.stat().st_size} bytes")
        
        # Read first few lines
        try:
            with open(submission_path, 'r') as f:
                lines = f.readlines()[:5]
                log(f"   Preview:\n{''.join(lines)}")
        except Exception as e:
            log(f"   Could not preview: {e}")
        
        return 0
    else:
        log("❌ WARNING: No submission file found!", 2)
        log(f"   Expected at: {submission_path}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
