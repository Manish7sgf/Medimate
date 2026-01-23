# oversample_min.py
import json, random, collections
IN="medimate_dataset_collapsed.jsonl"
OUT="medimate_dataset_balanced.jsonl"
min_count=20

recs_by_label = {}
with open(IN,"r",encoding="utf-8") as f:
    recs=[json.loads(l) for l in f]
for r in recs:
    recs_by_label.setdefault(r['label'], []).append(r)

new_recs=[]
for lab, items in recs_by_label.items():
    n = len(items)
    if n >= min_count:
        new_recs.extend(items)
    else:
        # sample with replacement
        needed = min_count - n
        new_recs.extend(items)
        for _ in range(needed):
            new_recs.append(random.choice(items))
print("Original total:", len(recs), "New total:", len(new_recs))
import random
random.shuffle(new_recs)
with open(OUT,"w",encoding="utf-8") as fo:
    for r in new_recs:
        fo.write(json.dumps(r, ensure_ascii=False) + "\n")
print("WROTE", OUT)
