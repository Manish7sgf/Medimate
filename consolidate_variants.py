# consolidate_variants.py
import json, re
IN = "medimate_dataset_top100.jsonl"
OUT = "medimate_dataset_collapsed.jsonl"

def collapse_label(label):
    # remove " - Variant ..." and similar suffixes, keep base disease
    # stops at first " - Variant" or " Variant - " pattern
    # also strip trailing spaces
    lab = re.split(r"\s*-\s*Variant\b", label, maxsplit=1)[0]
    return lab.strip()

count = {}
with open(IN, "r", encoding="utf-8") as fin:
    recs = [json.loads(l) for l in fin]

for r in recs:
    old = r["label"]
    new = collapse_label(old)
    r["label"] = new
    count[new] = count.get(new, 0) + 1

with open(OUT, "w", encoding="utf-8") as fo:
    for r in recs:
        fo.write(json.dumps(r, ensure_ascii=False) + "\n")

print("WROTE", OUT)
print("Unique labels after collapse:", len(count))
print("Top 20 labels after collapse:")
for k,v in sorted(count.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(k, v)
