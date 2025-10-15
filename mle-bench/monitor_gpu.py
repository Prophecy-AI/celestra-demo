#!/usr/bin/env python3
"""
Monitor GPU usage and training progress for MLE-bench runs
"""
import subprocess
import time
import sys
import json
from pathlib import Path
from datetime import datetime


def check_gpu_status():
    """Check if GPU is available and being used"""
    try:
        # Check nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", 
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split(", ")
            return {
                "name": gpu_info[0],
                "memory_used_mb": int(gpu_info[1]),
                "memory_total_mb": int(gpu_info[2]),
                "utilization": int(gpu_info[3]),
                "status": "active" if int(gpu_info[3]) > 0 else "idle"
            }
    except:
        pass
    return {"status": "no_gpu"}


def monitor_training_logs(log_file):
    """Monitor training logs for progress indicators"""
    if not Path(log_file).exists():
        return None
    
    progress_indicators = []
    with open(log_file, 'r') as f:
        for line in f:
            # Look for common progress patterns
            if any(pattern in line.lower() for pattern in [
                'epoch', 'fold', 'loss', 'score', 'accuracy', 
                'kappa', 'val_', 'train_', 'iteration'
            ]):
                progress_indicators.append(line.strip())
    
    # Return last 5 progress lines
    return progress_indicators[-5:] if progress_indicators else None


def main():
    """Main monitoring loop"""
    print("=" * 60)
    print("MLE-BENCH GPU & TRAINING MONITOR")
    print("=" * 60)
    
    # Check for log file argument
    log_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    iteration = 0
    while True:
        iteration += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check GPU
        gpu_info = check_gpu_status()
        
        print(f"\n[{timestamp}] Iteration {iteration}")
        print("-" * 40)
        
        if gpu_info["status"] == "no_gpu":
            print("❌ NO GPU DETECTED!")
        else:
            print(f"✅ GPU: {gpu_info['name']}")
            print(f"   Memory: {gpu_info['memory_used_mb']}/{gpu_info['memory_total_mb']} MB "
                  f"({gpu_info['memory_used_mb']/gpu_info['memory_total_mb']*100:.1f}%)")
            print(f"   Utilization: {gpu_info['utilization']}%")
            
            if gpu_info['utilization'] == 0:
                print("   ⚠️ WARNING: GPU is idle! Training might be on CPU!")
            elif gpu_info['utilization'] > 80:
                print("   🚀 GPU is actively training!")
        
        # Check training progress
        if log_file:
            progress = monitor_training_logs(log_file)
            if progress:
                print("\n📊 Recent Training Progress:")
                for line in progress:
                    print(f"   {line[:100]}...")  # Truncate long lines
        
        # Sleep before next check
        time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)
