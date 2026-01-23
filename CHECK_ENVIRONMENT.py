#!/usr/bin/env python3
"""
Quick check script to verify all dependencies are installed correctly
and GPU is available for training
"""

import sys

print("\n" + "="*50)
print("MEDIMATE ENVIRONMENT CHECK")
print("="*50 + "\n")

# Check Python version
print(f"✓ Python Version: {sys.version}")

# Check PyTorch
try:
    import torch
    print(f"✓ PyTorch: {torch.__version__}")
    print(f"  - CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  - GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"  - GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("  ⚠ GPU not available - training will use CPU (slower)")
except ImportError:
    print("✗ PyTorch not installed")

# Check transformers
try:
    import transformers
    print(f"✓ Transformers: {transformers.__version__}")
except ImportError:
    print("✗ Transformers not installed")

# Check datasets
try:
    import datasets
    print(f"✓ Datasets: {datasets.__version__}")
except ImportError:
    print("✗ Datasets not installed")

# Check Flask
try:
    import flask
    print(f"✓ Flask: {flask.__version__}")
except ImportError:
    print("✗ Flask not installed")

# Check SQLAlchemy
try:
    import sqlalchemy
    print(f"✓ SQLAlchemy: {sqlalchemy.__version__}")
except ImportError:
    print("✗ SQLAlchemy not installed")

# Check scikit-learn
try:
    import sklearn
    print(f"✓ Scikit-learn: {sklearn.__version__}")
except ImportError:
    print("✗ Scikit-learn not installed")

# Check required data files
import os
from pathlib import Path

print("\n" + "="*50)
print("DATA FILES CHECK")
print("="*50 + "\n")

required_files = [
    "medimate_option1_train_8000.jsonl",
    "medimate_option1_val_1000.jsonl",
    "medimate_option1_test_1000.jsonl"
]

for file in required_files:
    if Path(file).exists():
        size_mb = Path(file).stat().st_size / (1024*1024)
        print(f"✓ {file} ({size_mb:.2f} MB)")
    else:
        print(f"✗ {file} (MISSING)")

print("\n" + "="*50)
if torch.cuda.is_available():
    print("✓ Ready for GPU training!")
else:
    print("⚠ GPU not available - will train on CPU")
print("="*50 + "\n")
