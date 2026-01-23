# inference_test.py (with RULE ENGINE)
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import torch.nn.functional as F
import re

MODEL_DIR = "medimate-ner-output"

# Load tokenizer + model
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=True)
model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR)
id2label = model.config.id2label


# -----------------------------
# RULE ENGINE
# -----------------------------
def rule_based_extraction(text):
    rules = []

    # Duration rules
    duration_patterns = [
        r"\b(\d+)\s*(day|days|hour|hours|week|weeks|minute|minutes)\b",
        r"\bsince\s+(yesterday|morning|evening|last night|today)\b",
        r"\bfor\s+(\d+)\s*(day|days|hour|hours|minutes)\b",
        r"\blast night\b",
        r"\byesterday\b"
    ]

    for p in duration_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            rules.append({
                "entity": "DUR",
                "text": m.group(0),
                "confidence": 0.90
            })

    # Severity rules
    severity_words = ["mild", "moderate", "severe", "slight", "very severe"]

    for w in severity_words:
        if w in text.lower():
            rules.append({
                "entity": "SEV",
                "text": w,
                "confidence": 0.85
            })

    return rules


# -----------------------------
# TOKEN CLASSIFIER MODEL NER
# -----------------------------
def model_entities(text, max_length=256):
    encoding = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
        return_offsets_mapping=True,
    )

    offsets = encoding["offset_mapping"][0].tolist()
    word_ids = encoding.word_ids(batch_index=0)

    model_inputs = {}
    for k, v in encoding.items():
        if k in ("input_ids", "attention_mask", "token_type_ids"):
            model_inputs[k] = v

    with torch.no_grad():
        logits = model(**model_inputs).logits[0]
        probs = F.softmax(logits, dim=-1)
        preds = probs.argmax(-1).tolist()

    tokens = tokenizer.convert_ids_to_tokens(model_inputs["input_ids"][0])

    # Merge subword tokens to whole words
    entities = []
    cur = None

    for i, wid in enumerate(word_ids):
        if wid is None:
            if cur:
                entities.append(cur); cur = None
            continue

        label = id2label[preds[i]]
        conf = float(probs[i, preds[i]])

        if label == "O":
            if cur:
                entities.append(cur); cur = None
            continue

        prefix, etype = label.split("-", 1)

        if prefix == "B" or cur is None or cur[2] != etype:
            if cur:
                entities.append(cur)
            cur = [wid, wid, etype, conf]
        else:
            cur[1] = wid
            if conf > cur[3]:
                cur[3] = conf

    if cur:
        entities.append(cur)

    # WORD RECONSTRUCTION
    input_text = text
    grouped = {}
    for token_idx, wid in enumerate(word_ids):
        if wid is None: continue
        grouped.setdefault(wid, []).append(token_idx)

    max_word = max([w for w in word_ids if w is not None])
    word_texts = []
    for wid in range(max_word + 1):
        if wid not in grouped:
            word_texts.append("")
            continue
        idxs = grouped[wid]
        s = offsets[idxs[0]][0]
        e = offsets[idxs[-1]][1]
        word_texts.append(input_text[s:e])

    # Final structured entities
    final = []
    for start, end, typ, conf in entities:
        ent_text = " ".join(word_texts[start:end+1]).strip()
        final.append({
            "entity": typ,
            "text": ent_text,
            "confidence": round(conf, 3)
        })

    return final


# -----------------------------
# COMBINED MODEL + RULE OUTPUT
# -----------------------------
def extract(text):
    model_out = model_entities(text)
    rule_out = rule_based_extraction(text)

    return model_out + rule_out


# -----------------------------
# PRETTY PRINT
# -----------------------------
def pretty_print(text):
    print("\nINPUT:", text)
    ents = extract(text)
    if not ents:
        print("No entities found.")
        return

    for e in ents:
        print(f"- {e['entity']:6} : '{e['text']}' (conf={e['confidence']})")


# -----------------------------
# TEST
# -----------------------------
if __name__ == "__main__":
    tests = [
        "I have fever and sore throat since 2 days.",
        "Severe chest pain and breathlessness.",
        "Mild headache today.",
        "Vomiting since last night and severe stomach pain for 1 hour."
    ]

    for t in tests:
        pretty_print(t)
