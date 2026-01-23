# train_disease_classifier.py - FINAL CORRECT VERSION
import json
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd

import torch
from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EvalPrediction
)

from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

# ---------------------------
# FIXED PATHS & HYPERPARAMS
# ---------------------------
# Ensure these JSONL files exist in your directory
TRAIN_PATH = "medimate_option1_train_8000.jsonl"
VAL_PATH = "medimate_option1_val_1000.jsonl"
TEST_PATH = "medimate_option1_test_1000.jsonl"

MODEL_OUT = "medimate-disease-model"
BASE_MODEL = "emilyalsentzer/Bio_ClinicalBERT"

# Hyperparameters
EPOCHS = 5
BATCH_SIZE = 8
EVAL_BATCH_SIZE = 16
LR = 2e-5
MAX_LENGTH = 128
SEED = 42

# ---------------------------
# Reproducibility & device
# ---------------------------
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🚀 Device for training: {device} (torch {torch.__version__})")
os.makedirs(MODEL_OUT, exist_ok=True)

# ---------------------------
# Helpers to read jsonl into pandas
# ---------------------------
def read_jsonl_to_df(path):
    if not Path(path).exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            recs.append(json.loads(line))
    df = pd.DataFrame(recs)
    return df

# ---------------------------
# Load dataset
# ---------------------------
print("Loading separate train/val/test JSONL files...")
try:
    df_train = read_jsonl_to_df(TRAIN_PATH)
    df_val = read_jsonl_to_df(VAL_PATH)
    df_test = read_jsonl_to_df(TEST_PATH)
    df_all = pd.concat([df_train, df_val, df_test], ignore_index=True)
except FileNotFoundError as e:
    print(f"FATAL ERROR: {e}")
    print("Please ensure your dataset files are present before running.")
    exit()

print(f"Dataset sizes -> train: {len(df_train)}, val: {len(df_val)}, test: {len(df_test)}")

# ---------------------------
# Label mapping (THE CRITICAL 72-CLASS FIX)
# ---------------------------
if "label" not in df_all.columns:
    raise ValueError("Dataset missing 'label' column.")
if "label" not in df_all.columns or "severity" not in df_all.columns:
    raise ValueError("Dataset missing 'label' or 'severity' column required for combined classification.")

# Create a new combined label: Disease_Severity (e.g., 'Appendicitis_severe')
df_all["combined_label"] = df_all["label"] + "_" + df_all["severity"]

# Redefine labels based on the new combined column
labels = sorted(df_all["combined_label"].unique())
label2id = {lbl: i for i, lbl in enumerate(labels)}
id2label = {i: lbl for lbl, i in label2id.items()}

# Add the new combined label_id column to the splits
for df in (df_train, df_val, df_test):
    df["label_id"] = (df["label"] + "_" + df["severity"]).map(label2id).astype(int)

# Save label classes for inference mapping (Updated to save combined labels)
np.save(os.path.join(MODEL_OUT, "label_classes.npy"), np.array(labels))
print(f"Saved label_classes.npy with {len(labels)} classes.")

# ---------------------------
# Convert pandas to HF Dataset
# ---------------------------
hf_train = Dataset.from_pandas(df_train.reset_index(drop=True))
hf_val = Dataset.from_pandas(df_val.reset_index(drop=True))
hf_test = Dataset.from_pandas(df_test.reset_index(drop=True))

def cleanup_dataset(ds):
    remove_cols = [c for c in ds.column_names if c not in ("text", "label", "label_id", "symptoms", "duration", "severity", "red_flags")]
    if remove_cols:
        ds = ds.remove_columns(remove_cols)
    return ds

hf_train = cleanup_dataset(hf_train)
hf_val = cleanup_dataset(hf_val)
hf_test = cleanup_dataset(hf_test)

# ---------------------------
# Tokenizer & tokenization
# ---------------------------
print(f"Loading tokenizer for: {BASE_MODEL}")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)

def tokenize_batch(batch):
    enc = tokenizer(
        batch["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH
    )
    enc["labels"] = batch["label_id"]
    return enc

print("Tokenizing datasets (batched)...")
hf_train = hf_train.map(tokenize_batch, batched=True, batch_size=256, remove_columns=[c for c in hf_train.column_names if c not in ("text", "label_id")])
hf_val = hf_val.map(tokenize_batch, batched=True, batch_size=256, remove_columns=[c for c in hf_val.column_names if c not in ("text", "label_id")])
hf_test = hf_test.map(tokenize_batch, batched=True, batch_size=256, remove_columns=[c for c in hf_test.column_names if c not in ("text", "label_id")])

# Keep only required columns for Trainer
keep_cols = ["input_ids", "attention_mask", "labels"]
if "token_type_ids" in hf_train.column_names:
    keep_cols.append("token_type_ids")

hf_train = hf_train.select_columns(keep_cols)
hf_val = hf_val.select_columns(keep_cols)
hf_test = hf_test.select_columns(keep_cols)

# ---------------------------
# Model
# ---------------------------
print(f"Loading base model: {BASE_MODEL} with {len(labels)} labels")
model = AutoModelForSequenceClassification.from_pretrained(
    BASE_MODEL,
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id
)

# ---------------------------
# Metrics
# ---------------------------
def compute_metrics(pred: EvalPrediction):
    logits = pred.predictions
    labels_arr = pred.label_ids
    if logits is None or labels_arr is None:
        return {"accuracy": 0.0, "f1": 0.0}
    preds = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels_arr, preds)
    f1 = f1_score(labels_arr, preds, average="weighted", zero_division=0)
    return {"accuracy": float(acc), "f1": float(f1)}

# ---------------------------
# TrainingArguments builder
# ---------------------------
def make_training_args(output_dir):
    try:
        args_tf = TrainingArguments(
            output_dir=output_dir,
            evaluation_strategy="steps",
            eval_steps=500 if len(hf_train) > 500 else max(1, len(hf_train)//10),
            logging_steps=50,
            save_steps=1000,
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=EVAL_BATCH_SIZE,
            learning_rate=LR,
            num_train_epochs=EPOCHS,
            weight_decay=0.01,
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            save_total_limit=2,
            fp16=torch.cuda.is_available(),
            warmup_ratio=0.06,
            max_grad_norm=1.0,
            seed=SEED,
            dataloader_drop_last=False,
            report_to="none"
        )
        print("DEBUG: Using modern TrainingArguments.")
    except TypeError as e:
        # Fallback for older library versions
        args_tf = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=EVAL_BATCH_SIZE,
            learning_rate=LR,
            num_train_epochs=EPOCHS,
            weight_decay=0.01,
            logging_steps=50,
            save_steps=500,
            fp16=torch.cuda.is_available(),
            seed=SEED,
        )
        print("DEBUG: Using fallback TrainingArguments (compatible).")
    return args_tf

training_args = make_training_args(MODEL_OUT)

# ---------------------------
# Trainer
# ---------------------------
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=hf_train,
    eval_dataset=hf_val,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics
)

# ---------------------------
# Train
# ---------------------------
print("Starting training...")
trainer.train()

# Save model & tokenizer
trainer.save_model(MODEL_OUT)
tokenizer.save_pretrained(MODEL_OUT)
print("Saved trained model to:", MODEL_OUT)

# ---------------------------
# Evaluate on test set & save reports
# ---------------------------
print("Running evaluation on test set...")
preds_out = trainer.predict(hf_test)
logits = preds_out.predictions
labels_true = preds_out.label_ids
preds = np.argmax(logits, axis=-1)

acc = accuracy_score(labels_true, preds)
f1w = f1_score(labels_true, preds, average="weighted", zero_division=0)
print(f"Test Accuracy: {acc:.4f} \tWeighted-F1: {f1w:.4f}")

# Classification report (per-class)
report = classification_report(labels_true, preds, labels=list(range(len(labels))), target_names=labels, zero_division=0, output_dict=True)
report_df = pd.DataFrame(report).transpose()
report_csv = os.path.join(MODEL_OUT, "classification_report.csv")
report_df.to_csv(report_csv, index=True)
print("Saved classification report to:", report_csv)

# Confusion matrix
cm = confusion_matrix(labels_true, preds, labels=list(range(len(labels))))
cm_df = pd.DataFrame(cm, index=labels, columns=labels)
cm_csv = os.path.join(MODEL_OUT, "confusion_matrix.csv")
cm_df.to_csv(cm_csv)
print("Saved confusion matrix to:", cm_csv)

# Save simple metrics summary
metrics_summary = {
    "test_accuracy": float(acc),
    "test_weighted_f1": float(f1w),
    "num_classes": len(labels),
    "num_train_samples": len(hf_train),
    "num_val_samples": len(hf_val),
    "num_test_samples": len(hf_test)
}
with open(os.path.join(MODEL_OUT, "metrics_summary.json"), "w", encoding="utf-8") as fh:
    json.dump(metrics_summary, fh, indent=2)
print("Saved metrics summary to:", os.path.join(MODEL_OUT, "metrics_summary.json"))

print("🔥 Training + evaluation complete.")