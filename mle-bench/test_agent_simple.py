#!/usr/bin/env python3
"""
Simple test runner for agent_v5 on aerial-cactus-identification
without Docker
"""
import asyncio
import os
import sys
import json
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

# Add agent_v5 to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent / "agents/agent_v5_kaggle"))

# Set up environment variables
os.environ["DEBUG"] = "1"
os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")

from kaggle_agent import KaggleAgent
from debug import log


async def test_agent_on_competition(competition_id="aerial-cactus-identification"):
    """Test agent on a single competition"""
    
    # Set up paths
    base_dir = Path("/tmp/mle_bench_test") / datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir.mkdir(exist_ok=True, parents=True)
    
    # MLE-bench data location
    mle_data = Path.home() / "Library/Caches/mle-bench/data" / competition_id / "prepared/public"
    
    if not mle_data.exists():
        print(f"❌ Competition data not found at {mle_data}")
        print(f"   Please run: mlebench prepare -c {competition_id}")
        return None
    
    # Create test directories
    data_dir = base_dir / "data"
    code_dir = base_dir / "code"
    submission_dir = base_dir / "submission"
    
    data_dir.mkdir(exist_ok=True)
    code_dir.mkdir(exist_ok=True)
    submission_dir.mkdir(exist_ok=True)
    
    # Copy competition data
    print(f"📊 Copying competition data from {mle_data}")
    for file in mle_data.iterdir():
        if file.is_file():
            shutil.copy(file, data_dir)
            print(f"   ✓ Copied {file.name}")
    
    # Create simplified instructions
    instructions_path = base_dir / "instructions.txt"
    instructions_path.write_text(f"""
Competition: {competition_id}

Task: Image Classification - Identify if aerial images contain columnar cacti

Data Files:
- train.csv: Training labels (id, has_cactus)
- train.zip: Training images
- test.zip: Test images to classify
- sample_submission.csv: Example of submission format

Objective:
1. Build a model to classify if images contain cacti
2. Generate predictions for all test images
3. Save predictions to submission/submission.csv in the format:
   id,has_cactus
   0004be2cfeaba1c0361d39e2b000257b.jpg,0
   ...

Evaluation: Classification accuracy
    """)
    
    print(f"\n🏁 Starting agent test on {competition_id}")
    print(f"📁 Working directory: {base_dir}")
    
    # Create agent
    agent = KaggleAgent(
        session_id=competition_id,
        workspace_dir=str(code_dir),
        data_dir=str(data_dir),
        submission_dir=str(submission_dir),
        instructions_path=str(instructions_path)
    )
    
    # Initial message
    initial_message = (
        f"You are competing in the Kaggle competition: {competition_id}\n\n"
        f"Your goal: Analyze the data in {data_dir}/, build a machine learning model, "
        f"and create a valid submission file at {submission_dir}/submission.csv\n\n"
        f"Start by reading the competition instructions at {instructions_path} and "
        f"exploring the data files.\n\n"
        f"IMPORTANT: This is the aerial-cactus-identification competition. "
        f"You need to classify images as containing cacti (1) or not (0)."
    )
    
    print("\n🤖 Agent starting...\n")
    print("="*60)
    
    # Run agent
    full_response = []
    tool_count = 0
    
    try:
        async for message in agent.run(initial_message):
            if message.get("type") == "text_delta":
                text = message["text"]
                print(text, end="", flush=True)
                full_response.append(text)
            elif message.get("type") == "tool_execution":
                tool_count += 1
                tool_name = message["tool_name"]
                print(f"\n[Tool #{tool_count}: {tool_name}]\n", flush=True)
    except Exception as e:
        print(f"\n\n❌ Agent error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    print("\n" + "="*60)
    print("\n✅ Agent run complete!")
    
    # Check results
    submission_path = submission_dir / "submission.csv"
    
    results = {
        "competition": competition_id,
        "timestamp": datetime.now().isoformat(),
        "working_dir": str(base_dir),
        "tools_used": tool_count,
        "submission_created": submission_path.exists(),
    }
    
    if submission_path.exists():
        # Read submission
        with open(submission_path, 'r') as f:
            lines = f.readlines()
        
        results["submission_lines"] = len(lines)
        results["submission_preview"] = lines[:5]
        
        print(f"\n📤 Submission created successfully!")
        print(f"   Lines: {len(lines)}")
        print(f"   Preview:")
        for line in lines[:5]:
            print(f"     {line.strip()}")
        
        # Compare with sample submission format
        sample_path = data_dir / "sample_submission.csv"
        if sample_path.exists():
            with open(sample_path, 'r') as f:
                sample_lines = f.readlines()
            print(f"\n   Expected {len(sample_lines)} lines (based on sample)")
            
            if len(lines) == len(sample_lines):
                print("   ✅ Line count matches sample submission!")
            else:
                print(f"   ⚠️ Line count mismatch (got {len(lines)}, expected {len(sample_lines)})")
    else:
        print(f"\n❌ No submission file created at {submission_path}")
        print(f"   Contents of submission directory:")
        for item in submission_dir.iterdir():
            print(f"     - {item.name}")
    
    # Save results
    results_path = base_dir / "results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to: {results_path}")
    print(f"🗂️ All files saved to: {base_dir}")
    
    return results


if __name__ == "__main__":
    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Run test
    results = asyncio.run(test_agent_on_competition())
    
    if results and results["submission_created"]:
        print("\n🎉 SUCCESS: Agent completed the competition!")
        sys.exit(0)
    else:
        print("\n⚠️ INCOMPLETE: Agent did not create a submission")
        sys.exit(1)


