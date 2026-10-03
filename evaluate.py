"""Compare rules-only, ML-only and combined detection on the held-out test split.
Run: python evaluate.py   (writes results.md - use the table in your slides)"""
import joblib

import detection
import ml
from train_model import load_clean, split


def metrics(pred, truth):
    tp = sum(p and t for p, t in zip(pred, truth))
    fp = sum(p and not t for p, t in zip(pred, truth))
    fn = sum((not p) and t for p, t in zip(pred, truth))
    tn = sum((not p) and (not t) for p, t in zip(pred, truth))
    return {
        "accuracy": (tp + tn) / len(truth),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "fp": fp, "fn": fn,
    }


df = load_clean()
_, X_test, _, y_test = split(df)
texts, truth = list(X_test), [bool(v) for v in y_test]

model = joblib.load(ml.MODEL_PATH)
scores = model.predict_proba(texts)[:, 1]

rules = [detection.sqli_rule_match(t) is not None for t in texts]
mlp = [s >= ml.ML_THRESHOLD for s in scores]
both = [r or m for r, m in zip(rules, mlp)]

rows = [("Rules only", metrics(rules, truth)),
        (f"ML only (threshold {ml.ML_THRESHOLD})", metrics(mlp, truth)),
        ("Rules + ML (SentinelWeb)", metrics(both, truth))]

lines = [f"Evaluation on {len(texts)} held-out rows from SQLiV3.csv "
         f"({sum(truth)} SQL injection, {len(truth) - sum(truth)} normal)\n",
         "| Method | Accuracy | Precision | Recall | False alarms | Missed attacks |",
         "|---|---|---|---|---|---|"]
for name, m in rows:
    lines.append(f"| {name} | {m['accuracy']:.1%} | {m['precision']:.1%} | {m['recall']:.1%} | {m['fp']} | {m['fn']} |")

missed = [t for t, tr, b in zip(texts, truth, both) if tr and not b][:8]
fps = [t for t, tr, b in zip(texts, truth, both) if b and not tr][:8]
lines += ["", "Examples of attacks still missed:"] + [f"- `{t[:90]}`" for t in missed]
lines += ["", "Examples of false alarms:"] + ([f"- `{t[:90]}`" for t in fps] or ["- none in this split"])
lines += ["", "Caveat: the dataset repeats similar payloads, so scores here are optimistic. "
          "Real traffic will score lower."]

out = "\n".join(lines)
print(out)
open("results.md", "w").write(out + "\n")
