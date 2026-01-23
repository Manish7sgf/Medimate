# eval_disease.py
"""
Evaluate medimate disease classifier on medimate_dataset_2000_realistic.jsonl.

Usage:
  python eval_disease.py
"""

import json
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, classification_report
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sklearn.model_selection import train_test_split

# Adjust if your file name is different
DATASET_PATH = "medimate_dataset_top100.jsonl"
MODEL_DIR = "medimate-disease-model"

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            records.append(json.loads(line.strip()))
    return records

def get_label_map(config):
    # Some configs use string keys; handle both
    id2label = config.id2label
    # Normalize to int-key dict
    if all(isinstance(k, str) for k in id2label.keys()):
        new = {}
        for k, v in id2label.items():
            try:
                new[int(k)] = v
            except:
                # fallback: keep order
                new[len(new)] = v
        return new
    return id2label

def batch_predict(texts, tokenizer, model, device="cpu", batch_size=16):
    model.to(device)
    preds = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            enc = tokenizer(batch, truncation=True, padding=True, max_length=128, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits.cpu().numpy()
            pred_ids = np.argmax(logits, axis=-1)
            preds.extend(pred_ids.tolist())
    return preds

def main():
    print("Loading dataset:", DATASET_PATH)
    data = load_jsonl(DATASET_PATH)
    texts = [r["text"] for r in data]
    labels = [r["label"] for r in data]

    # build label2id mapping (sorted)
    unique_labels = sorted(list(set(labels)))
    label2id = {lbl: i for i, lbl in enumerate(unique_labels)}
    id2label = {i: lbl for lbl, i in label2id.items()}
    y = [label2id[l] for l in labels]

    # create train/test split same style as training (10% test)
    X_train, X_test, y_train, y_test = train_test_split(texts, y, test_size=0.1, random_state=42, stratify=y)

    print(f"Total samples: {len(texts)}  Train: {len(X_train)}  Test: {len(X_test)}")
    print(f"Num labels: {len(unique_labels)}")

    # Load model/tokenizer
    print("Loading model from:", MODEL_DIR)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=True)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

    # Get predictions
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)
    y_pred_ids = batch_predict(X_test, tokenizer, model, device=device, batch_size=16)

    # model.config.id2label might map integers to labels; but training used a custom mapping.
    # Try to align predictions to our label ids: if model id2label matches our labels, convert; else assume same indexing.
    cfg_id2label = get_label_map(model.config)
    # If cfg_id2label keys align to 0..N-1 and values are strings labels, map predicted ids to label strings and back to our ids.
    try:
        pred_labels_str = [cfg_id2label[int(pid)] for pid in y_pred_ids]
        # convert to our id space
        y_pred = [label2id.get(s, -1) for s in pred_labels_str]
        # If many -1 (mismatch), fallback to direct numeric preds
        if sum(1 for x in y_pred if x == -1) > 0.3 * len(y_pred):
            print("Warning: model label names don't match dataset labels. Falling back to numeric mapping.")
            y_pred = y_pred_ids
    except Exception as e:
        print("Warning mapping by name failed:", e)
        y_pred = y_pred_ids

    # Filter any invalid preds (if any) by setting to most common class 0
    y_pred = [int(p) if (isinstance(p, int) and 0 <= p < len(unique_labels)) else 0 for p in y_pred]

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    print("Accuracy:", round(acc, 4))
    print("F1 (weighted):", round(f1, 4))

    # Optional: show classification report for top labels
    print("\nClassification report (top 10 labels by support):")
    try:
        print(classification_report(y_test, y_pred, target_names=[id2label[i] for i in range(len(unique_labels))], zero_division=0))
    except Exception:
        print("Could not print full report (too many labels).")

if __name__ == "__main__":
    main()
