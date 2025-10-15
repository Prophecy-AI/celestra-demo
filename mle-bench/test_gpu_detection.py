#!/usr/bin/env python3
"""
Quick test to verify GPU detection and usage
"""
import sys
import time

def test_gpu():
    """Test GPU availability and basic operations"""
    print("=" * 60)
    print("GPU DETECTION TEST")
    print("=" * 60)
    
    # Test PyTorch
    try:
        import torch
        print(f"\n✅ PyTorch version: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"✅ CUDA available!")
            print(f"   Device: {torch.cuda.get_device_name(0)}")
            print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
            
            # Test basic operation
            print("\nTesting GPU computation...")
            device = torch.device('cuda')
            x = torch.randn(1000, 1000).to(device)
            y = torch.randn(1000, 1000).to(device)
            
            start = time.time()
            z = torch.matmul(x, y)
            torch.cuda.synchronize()
            elapsed = time.time() - start
            
            print(f"   Matrix multiplication (1000x1000): {elapsed*1000:.1f}ms")
            
            # Test model loading
            print("\nTesting model on GPU...")
            from torchvision import models
            model = models.resnet18(pretrained=False).to(device)
            input_tensor = torch.randn(1, 3, 224, 224).to(device)
            
            start = time.time()
            with torch.no_grad():
                output = model(input_tensor)
            torch.cuda.synchronize()
            elapsed = time.time() - start
            
            print(f"   ResNet18 inference: {elapsed*1000:.1f}ms")
            print(f"   Output shape: {output.shape}")
            
            return True
        else:
            print("❌ CUDA not available - GPU not detected")
            print("   Will fall back to CPU (slower)")
            return False
            
    except ImportError as e:
        print(f"❌ PyTorch not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during GPU test: {e}")
        return False


def test_tensorflow():
    """Test TensorFlow GPU support"""
    print("\n" + "=" * 60)
    print("TENSORFLOW GPU TEST")
    print("=" * 60)
    
    try:
        import tensorflow as tf
        print(f"\n✅ TensorFlow version: {tf.__version__}")
        
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"✅ TensorFlow GPUs available: {len(gpus)}")
            for gpu in gpus:
                print(f"   {gpu}")
        else:
            print("❌ No TensorFlow GPUs found")
            
    except ImportError:
        print("ℹ️ TensorFlow not installed")
    except Exception as e:
        print(f"❌ TensorFlow error: {e}")


def recommendations(has_gpu):
    """Print recommendations based on GPU availability"""
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if has_gpu:
        print("""
✅ GPU is available and working!

For optimal performance:
1. Use batch size 32-64 (or higher if memory allows)
2. Use mixed precision training:
   with torch.cuda.amp.autocast():
       output = model(input)
3. Use DataLoader with pin_memory=True
4. Consider gradient accumulation for larger effective batch sizes

Example training config:
   batch_size = 64
   num_workers = 8
   pin_memory = True
   device = 'cuda'
""")
    else:
        print("""
⚠️ No GPU detected - falling back to CPU

For best CPU performance:
1. Use smaller batch size (8-16)
2. Use simpler models (RandomForest, XGBoost)
3. Consider feature extraction instead of end-to-end training
4. Use all CPU cores: n_jobs=-1 for sklearn

Example CPU config:
   batch_size = 8
   num_workers = 4
   device = 'cpu'
   # Or use XGBoost/LightGBM instead of deep learning
""")


if __name__ == "__main__":
    has_gpu = test_gpu()
    test_tensorflow()
    recommendations(has_gpu)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    sys.exit(0 if has_gpu else 1)
