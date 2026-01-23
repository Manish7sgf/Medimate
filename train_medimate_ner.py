# train_medimate_ner.py
"""
Minimal, compatible training script for token classification (NER).
Usage:
python train_medimate_ner.py --jsonl medimate_bio.jsonl --model emilyalsentzer/Bio_ClinicalBERT --out medimate-ner-output
"""
import argparse
import json
import numpy as np
import evaluate
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            records.append(json.loads(s))
    print(f"Loaded {len(records)} records from {path}")
    return records

def main(jsonl_path, model_name, output_dir):
    records = load_jsonl(jsonl_path)

    # Collect label set from data
    label_set = set()
    for r in records:
        for lab in r["labels"]:
            label_set.add(lab)
    label_set.add("O")
    # Deterministic ordering: O first, then sorted others
    labels = ["O"] + sorted([l for l in label_set if l != "O"])
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}

    print("Labels:", labels)

    # tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(model_name, num_labels=len(labels), id2label=id2label, label2id=label2id)

    # Build encodings (we expect records to already contain tokenizer-aligned tokens & labels)
    input_ids = []
    attention_mask = []
    label_ids = []
    for r in records:
        enc = tokenizer(r["text"], truncation=True, padding="max_length", max_length=256)
        # ensure labels length matches tokenized length
        labs = r["labels"]
        if len(labs) < len(enc["input_ids"]):
            labs = labs + ["O"] * (len(enc["input_ids"]) - len(labs))
        elif len(labs) > len(enc["input_ids"]):
            labs = labs[: len(enc["input_ids"])]
        numeric_labels = [label2id.get(l, label2id["O"]) for l in labs]
        input_ids.append(enc["input_ids"])
        attention_mask.append(enc["attention_mask"])
        label_ids.append(numeric_labels)

    ds = Dataset.from_dict({"input_ids": input_ids, "attention_mask": attention_mask, "labels": label_ids})

    # TrainingArguments (minimal, widely compatible)
    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=3e-5,
        per_device_train_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        save_total_limit=2,
        remove_unused_columns=False,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer)

    metric = evaluate.load("seqeval")
    def compute_metrics(eval_pred):
        logits, labels_batch = eval_pred
        preds = np.argmax(logits, axis=2)
        true_labels = []
        true_preds = []
        for i in range(len(labels_batch)):
            lab = labels_batch[i]
            pred = preds[i]
            seq_true = []
            seq_pred = []
            for j, lab_id in enumerate(lab):
                # skip special tokens if using -100; here we did not use -100, so include all up to mask
                if lab_id == -100:
                    continue
                seq_true.append(id2label.get(int(lab_id), "O"))
                seq_pred.append(id2label.get(int(pred[j]), "O"))
            true_labels.append(seq_true)
            true_preds.append(seq_pred)
        results = metric.compute(predictions=true_preds, references=true_labels)
        return {
            "precision": results.get("overall_precision"),
            "recall": results.get("overall_recall"),
            "f1": results.get("overall_f1"),
        }

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds,
        eval_dataset=None,
        data_collator=data_collator,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(output_dir)
    print("Saved model to", output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", default="medimate_bio.jsonl")
    parser.add_argument("--model", default="bert-base-uncased")
    parser.add_argument("--out", default="medimate-ner-output")
    args = parser.parse_args()
    main(args.jsonl, args.model, args.out)
