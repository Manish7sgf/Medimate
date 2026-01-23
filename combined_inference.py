# combined_inference.py
"""
Combined inference pipeline:
 - run NER to extract symptom spans (type, text, confidence)
 - run disease classifier on full text
 - apply simple rule-engine (emergency / doctor suggestion)
 - print friendly output

Usage:
  python combined_inference.py
"""

from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import re

NER_DIR = "medimate-ner-output"
CLS_DIR = "medimate-disease-model"

# Load models
ner_tokenizer = AutoTokenizer.from_pretrained(NER_DIR, use_fast=True)
ner_model = AutoModelForTokenClassification.from_pretrained(NER_DIR)
ner_id2label = ner_model.config.id2label

cls_tokenizer = AutoTokenizer.from_pretrained(CLS_DIR, use_fast=True)
cls_model = AutoModelForSequenceClassification.from_pretrained(CLS_DIR)
cls_id2label = cls_model.config.id2label

device = "cuda" if torch.cuda.is_available() else "cpu"
ner_model.to(device)
cls_model.to(device)

def normalize_label_map(cfg_map):
    """Convert model.config.id2label to int->str dict safely"""
    if all(isinstance(k, int) for k in cfg_map.keys()):
        return {int(k): v for k, v in cfg_map.items()}
    new = {}
    for i, (k, v) in enumerate(cfg_map.items()):
        try:
            new[int(k)] = v
        except:
            new[i] = v
    return new

ner_id2label = normalize_label_map(ner_id2label)
cls_id2label = normalize_label_map(cls_id2label)

# NER extraction (works with fast tokenizer)
def ner_extract(text, topk=None):
    # Tokenize (fast tokenizer). Keep BatchEncoding so we can use .word_ids() and offsets,
    # but remove offset_mapping before calling the model.
    enc = ner_tokenizer(text, return_offsets_mapping=True, return_tensors="pt", truncation=True, max_length=256)

    # Save offsets and word_ids for later (these are NOT passed to model)
    offsets = enc["offset_mapping"][0].cpu().tolist() if "offset_mapping" in enc else None
    # word_ids() works on BatchEncoding (fast tokenizer)
    try:
        word_ids = enc.word_ids(batch_index=0)
    except Exception:
        # fallback: build word_ids as None (shouldn't normally happen with fast tokenizer)
        word_ids = None

    # Prepare input dict for the model: only move tensor values to device and remove helper keys
    model_inputs = {}
    for k, v in enc.items():
        if k == "offset_mapping":
            continue
        # some items might be lists/ints; only move tensors
        if isinstance(v, torch.Tensor):
            model_inputs[k] = v.to(device)
        else:
            # skip non-tensor helpers
            continue

    # Run model (no offset_mapping passed)
    with torch.no_grad():
        logits = ner_model(**model_inputs).logits[0]  # (seq_len, num_labels)
        probs = F.softmax(logits, dim=-1)

    preds = probs.argmax(-1).cpu().tolist()

    # get tokens (string form) from the model_inputs input_ids (on CPU)
    input_ids_cpu = model_inputs["input_ids"].cpu()[0].tolist()
    tokens = ner_tokenizer.convert_ids_to_tokens(input_ids_cpu)

    # Build spans by merging B-/I- tags using preds and word_ids
    spans = []
    cur = None  # [start_word_index, end_word_index, label_type, max_conf, token_indices]
    for i, wid in enumerate(word_ids if word_ids else [None]*len(preds)):
        if wid is None:
            if cur:
                spans.append(cur); cur = None
            continue
        label = ner_id2label.get(preds[i], "O")
        conf = float(probs[i, preds[i]].cpu().item())
        if label == "O":
            if cur:
                spans.append(cur); cur = None
            continue
        if "-" in label:
            prefix, typ = label.split("-", 1)
        else:
            prefix, typ = "B", label
        if prefix == "B" or cur is None or cur[2] != typ:
            if cur:
                spans.append(cur)
            cur = [wid, wid, typ, conf, [i]]
        else:
            cur[1] = wid
            cur[3] = max(cur[3], conf)
            cur[4].append(i)
    if cur:
        spans.append(cur)

    # group token indices by word id to extract original text spans using offsets
    grouped = {}
    for ti, wid in enumerate(word_ids if word_ids else []):
        if wid is None:
            continue
        grouped.setdefault(wid, []).append(ti)

    # reconstruct word_texts from offsets (use original text)
    original = text
    max_word = max([w for w in (word_ids or []) if w is not None], default=-1)
    word_texts = []
    for wid in range(max_word + 1):
        if wid not in grouped:
            word_texts.append("")
            continue
        idxs = grouped[wid]
        if offsets and len(offsets) > 0:
            s = offsets[idxs[0]][0]
            e = offsets[idxs[-1]][1]
            piece = original[s:e].strip()
            if not piece:
                piece = ner_tokenizer.convert_tokens_to_string([tokens[t] for t in idxs]).strip()
        else:
            piece = ner_tokenizer.convert_tokens_to_string([tokens[t] for t in idxs]).strip()
        word_texts.append(piece)

    out = []
    for s, e, typ, conf, token_idxs in spans:
        s = max(0, s); e = min(e, len(word_texts) - 1)
        ent_text = " ".join([w for w in word_texts[s:e+1] if w]).strip()
        ent_text = re.sub(r"\s+", " ", ent_text)
        out.append({"type": typ, "text": ent_text, "conf": round(conf, 3)})

    out = sorted(out, key=lambda x: x["conf"], reverse=True)
    if topk:
        out = out[:topk]
    return out

COMMON_SYMPTOMS = ["fever","cough","chest pain","breathlessness","vomiting","diarrhea",
                   "headache","loss of smell","abdominal pain","nausea","rash","dizziness"]

def fallback_simple_symptoms(text):
    found = []
    t = text.lower()
    for s in COMMON_SYMPTOMS:
        if s in t:
            found.append({"type":"SYM","text":s,"conf":0.25})
    return found



def classify_text(text, conf_threshold=0.20):
    enc = cls_tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
    enc = {k: v.to(device) for k, v in enc.items()}
    with torch.no_grad():
        logits = cls_model(**enc).logits
        probs = F.softmax(logits, dim=-1).cpu().numpy()[0]

    top_idx = int(probs.argmax())
    top_conf = float(probs[top_idx])

    # robust mapping for id2label
    label = None
    # 1) try model.config.id2label
    try:
        cfg = cls_model.config.id2label
        # cfg might have string keys - normalize
        if all(isinstance(k, str) for k in cfg.keys()):
            # pick the value at the string of idx or fallback on ordering
            label = cfg.get(str(top_idx), None)
            if label is None:
                # fallback: try ordering
                ordered_vals = [cfg[k] for k in sorted(cfg.keys(), key=lambda x: int(x) if x.isdigit() else x)]
                label = ordered_vals[top_idx] if top_idx < len(ordered_vals) else None
        else:
            label = cfg.get(top_idx, None)
    except Exception:
        label = None

    # final fallback: try cls_id2label dict we computed earlier
    if label is None:
        label = cls_id2label.get(top_idx, None)
    # final fallback: use index
    if label is None:
        label = f"Label_{top_idx}"

    # if confidence too low return Uncertain
    if top_conf < conf_threshold:
        return {"label": "Uncertain", "confidence": top_conf, "raw_label": label}

    return {"label": label, "confidence": top_conf}
# Simple rule engine for recommendations (extend as needed)
# ---------- add this (rule engine) ----------
EMERGENCY_KEYWORDS = {"chest pain", "breathlessness", "severe bleeding", "loss of consciousness", "sudden weakness", "sudden slurred speech"}
DOCTOR_RECOMMEND_KEYWORDS = {"high fever", "severe", "prolonged", "persistent", "worsening", "blood in stool", "hemoptysis", "vision change", "pregnancy", "severe abdominal pain"}

def rule_decision(ner_entities, predicted, full_text):
    text_low = full_text.lower()
    ent_texts = " ".join([e["text"].lower() for e in ner_entities]) if ner_entities else ""
    emergency = False
    reason = []

    for kw in EMERGENCY_KEYWORDS:
        if kw in text_low or kw in ent_texts:
            emergency = True
            reason.append(f"keyword '{kw}'")

    if predicted.get("confidence", 0) >= 0.7 and any(x in (predicted.get("label") or "").lower() for x in ["suspected", "acute", "severe"]):
        emergency = True
        reason.append("high-confidence acute/suspected diagnosis")

    doctor_needed = False
    for kw in DOCTOR_RECOMMEND_KEYWORDS:
        if kw in text_low or kw in ent_texts:
            doctor_needed = True
            reason.append(f"keyword '{kw}'")

    if predicted.get("label") == "Uncertain" or predicted.get("confidence", 0) < 0.35:
        doctor_needed = True
        reason.append("low prediction confidence")

    return {"emergency": emergency, "doctor_recommend": doctor_needed, "reasons": reason}
# ---------- end add ----------

# Pretty print helper
def pretty_print(text):
    print("\nINPUT:", text)
    ner_out = ner_extract(text)
    if not ner_out or len(ner_out) == 0:
        ner_out = fallback_simple_symptoms(text)
    if ner_out:
        print("NER:")
        for e in ner_out:
            print(f" - {e['type']}: '{e['text']}' (conf={e['conf']})")
    else:
        print("NER: none")

    cls_out = classify_text(text)
    print("Disease prediction:")
    print(f" - {cls_out['label']} (conf={round(cls_out['confidence'],3)})")

    decision = rule_decision(ner_out, cls_out, text)
    if decision["emergency"]:
        print("\n!! EMERGENCY FLAGGED !!")
    if decision["doctor_recommend"]:
        print("Doctor visit recommended.")
    print("Reasons:", "; ".join(decision["reasons"]) if decision["reasons"] else "none")
    print("-" * 40)

if __name__ == "__main__":
    tests = [
        "Patient presents with persistent dry cough and mild fever for 2 days.",
        "Patient reports severe chest pain and breathlessness since 3 hours.",
        "Patient has vomiting and lower abdominal pain for 12 hours.",
        "I have fever, loss of smell and dry cough for 2 days."
    ]
    for t in tests:
        pretty_print(t)
