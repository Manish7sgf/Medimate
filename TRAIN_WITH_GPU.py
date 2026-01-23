#!/usr/bin/env python3
"""
GPU Training Script for Medimate Models
Trains both disease classifier and NER models with GPU acceleration
"""

import torch
import os
import sys
from pathlib import Path

def main():
    print("\n" + "="*60)
    print("MEDIMATE GPU MODEL TRAINING")
    print("="*60 + "\n")
    
    # Check GPU availability
    if torch.cuda.is_available():
        print(f"✓ GPU Available: {torch.cuda.get_device_name(0)}")
        print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        print(f"✓ PyTorch CUDA Version: {torch.version.cuda}")
    else:
        print("⚠ GPU NOT available - training will use CPU (much slower)")
        
    print(f"✓ PyTorch Version: {torch.__version__}")
    
    # Check for training data files
    print("\n" + "="*60)
    print("CHECKING DATA FILES")
    print("="*60 + "\n")
    
    required_files = [
        "medimate_option1_train_8000.jsonl",
        "medimate_option1_val_1000.jsonl",
        "medimate_option1_test_1000.jsonl"
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            size_mb = Path(file).stat().st_size / (1024*1024)
            print(f"✓ {file} ({size_mb:.2f} MB)")
        else:
            print(f"✗ {file} MISSING")
            all_exist = False
    
    if not all_exist:
        print("\n✗ Error: Missing training data files!")
        sys.exit(1)
    
    # Train models
    print("\n" + "="*60)
    print("TRAINING DISEASE CLASSIFIER MODEL")
    print("="*60 + "\n")
    
    try:
        import train_disease_classifier
    except Exception as e:
        print(f"Error during disease classifier training: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("TRAINING NER MODEL")
    print("="*60 + "\n")
    
    try:
        # NER training requires manual invocation
        os.system("python train_medimate_ner.py --jsonl medimate_option1_train_8000.jsonl --model emilyalsentzer/Bio_ClinicalBERT --out medimate-ner-output")
    except Exception as e:
        print(f"Error during NER training: {e}")
        sys.exit(1)
    
    # Verify models exist
    print("\n" + "="*60)
    print("VERIFYING TRAINED MODELS")
    print("="*60 + "\n")
    
    disease_model_exists = Path("medimate-disease-model").exists()
    ner_model_exists = Path("medimate-ner-output").exists()
    
    if disease_model_exists:
        print("✓ Disease Classifier Model: Ready")
    else:
        print("✗ Disease Classifier Model: NOT FOUND")
    
    if ner_model_exists:
        print("✓ NER Model: Ready")
    else:
        print("✗ NER Model: NOT FOUND")
    
    if disease_model_exists and ner_model_exists:
        print("\n✓ All models trained successfully!")
        return 0
    else:
        print("\n✗ Some models failed to train")
        return 1

if __name__ == "__main__":
    sys.exit(main())
