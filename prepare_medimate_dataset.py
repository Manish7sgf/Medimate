# prepare_medimate_dataset.py
# Usage:
# python prepare_medimate_dataset.py --input medimate_custom_100.csv --output medimate_bio.jsonl --model MODEL_NAME
import argparse, json, re
from transformers import AutoTokenizer
import pandas as pd

def clean_placeholder(s):
    if not isinstance(s, str):
        return ""
    s = s.strip()
    if s in ("---", "", "—"):
        return ""
    return s

def main(input_path, output_path, model_name):
    df = pd.read_csv(input_path)
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    out = []
    for _, row in df.iterrows():
        text = str(row['text']).strip()
        # symptoms column is semicolon separated
        symptoms = [s.strip() for s in str(row.get('symptoms', '')).split(';') if s.strip()]
        # clean placeholders
        duration = clean_placeholder(row.get('duration', ''))
        severity = clean_placeholder(row.get('severity', ''))

        # we'll build a list of spans to mark as SYMNS in the text (lowercased for matching)
        spans = []
        for s in symptoms:
            if not s:
                continue
            # find all occurrences of the symptom phrase (naive substring find)
            start = 0
            s_l = s.lower()
            text_l = text.lower()
            while True:
                idx = text_l.find(s_l, start)
                if idx == -1:
                    break
                spans.append((idx, idx + len(s_l), "SYM"))
                start = idx + len(s_l)

        # if duration/ severity exist and appear in text, add spans (optional)
        if duration:
            di = text.lower().find(str(duration).lower())
            if di != -1:
                spans.append((di, di + len(str(duration)), "DUR"))
        if severity:
            si = text.lower().find(str(severity).lower())
            if si != -1:
                spans.append((si, si + len(str(severity)), "SEV"))

        # Tokenize with fast tokenizer and use word_ids to align
        encoding = tokenizer(text, return_offsets_mapping=True, truncation=True, max_length=256)
        offsets = encoding["offset_mapping"]
        # Build labels per token
        labels = ["O"] * len(offsets)
        for i, (st, ed) in enumerate(offsets):
            if st == ed:  # special tokens
                labels[i] = "O"
                continue
            token_span_start = st
            token_span_end = ed
            # check if token span overlaps any annotated span
            assigned = False
            for span_start, span_end, span_type in spans:
                # overlap check
                if token_span_end <= span_start or token_span_start >= span_end:
                    continue
                # overlapping → decide B- or I- based on whether token start matches span_start
                if token_span_start == span_start:
                    labels[i] = f"B-{span_type}"
                else:
                    labels[i] = f"I-{span_type}"
                assigned = True
                # we don't break because multiple spans unlikely, but break anyway
                break
            if not assigned:
                labels[i] = "O"

        # Convert tokens to simple list for inspection
        tokens = tokenizer.convert_ids_to_tokens(encoding["input_ids"])
        # Export record (tokens as tokenizer tokens, labels)
        out.append({"tokens": tokens, "labels": labels, "text": text})

    # write JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("Wrote", output_path, "with", len(out), "records")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="medimate_custom_100.csv")
    parser.add_argument("--output", default="medimate_bio.jsonl")
    parser.add_argument("--model", default="bert-base-uncased", help="HF model name for tokenizer alignment")
    args = parser.parse_args()
    main(args.input, args.output, args.model)
