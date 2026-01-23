# inspect_counts.py
import json, collections
P="medimate_dataset_collapsed.jsonl"
c=collections.Counter()
with open(P,"r",encoding="utf-8") as f:
    for l in f:
        d=json.loads(l); c[d['label']]+=1
print("Total labels:", len(c))
print("Top 30:")
for k,v in c.most_common(30):
    print(k, v)
with open("collapsed_label_counts.json","w",encoding="utf-8") as fo:
    import json
    json.dump(c.most_common(), fo, indent=2)
print("Wrote collapsed_label_counts.json")
