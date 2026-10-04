"""Compare rules-only, ML-only and combined detection on the held-out test split.

Run from the project folder:  python scripts/evaluate.py   (writes results.md)
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import joblib  # noqa: E402

from dashboard.detection.ml_model import ML_THRESHOLD, MODEL_PATH  # noqa: E402
from dashboard.detection.rules import SQL_INJECTION_RULES, find_first_rule_match  # noqa: E402
from train_model import load_clean_dataset, split_dataset  # noqa: E402

RESULTS_PATH = PROJECT_ROOT / "results.md"


def compute_metrics(predictions, truth) -> dict:
    """Accuracy, precision, recall, false alarms (fp) and missed attacks (fn)."""
    tp = sum(p and t for p, t in zip(predictions, truth))
    fp = sum(p and not t for p, t in zip(predictions, truth))
    fn = sum((not p) and t for p, t in zip(predictions, truth))
    tn = sum((not p) and (not t) for p, t in zip(predictions, truth))
    return {"accuracy": (tp + tn) / len(truth),
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "fp": fp, "fn": fn}


def build_report(texts, truth, rule_hits, model_hits) -> str:
    combined = [r or m for r, m in zip(rule_hits, model_hits)]
    rows = [("Rules only", compute_metrics(rule_hits, truth)),
            (f"ML only (threshold {ML_THRESHOLD})", compute_metrics(model_hits, truth)),
            ("Rules + ML (SentinelWeb)", compute_metrics(combined, truth))]
    lines = [f"Evaluation on {len(texts)} held-out rows from SQLiV3.csv "
             f"({sum(truth)} SQL injection, {len(truth) - sum(truth)} normal)\n",
             "| Method | Accuracy | Precision | Recall | False alarms | Missed attacks |",
             "|---|---|---|---|---|---|"]
    lines += [f"| {name} | {m['accuracy']:.1%} | {m['precision']:.1%} | {m['recall']:.1%} | {m['fp']} | {m['fn']} |" for name, m in rows]
    missed = [t for t, tr, c in zip(texts, truth, combined) if tr and not c][:8]
    false_alarms = [t for t, tr, c in zip(texts, truth, combined) if c and not tr][:8]
    lines += ["", "Examples of attacks still missed:"] + [f"- `{t[:90]}`" for t in missed]
    lines += ["", "Examples of false alarms:"] + ([f"- `{t[:90]}`" for t in false_alarms] or ["- none in this split"])
    lines += ["", "Caveat: the dataset repeats similar payloads, so scores here are optimistic. Real traffic will score lower."]
    return "\n".join(lines)


def main() -> None:
    _, x_test, _, y_test = split_dataset(load_clean_dataset())
    texts, truth = list(x_test), [bool(v) for v in y_test]
    scores = joblib.load(MODEL_PATH).predict_proba(texts)[:, 1]
    rule_hits = [find_first_rule_match(SQL_INJECTION_RULES, t) is not None for t in texts]
    model_hits = [s >= ML_THRESHOLD for s in scores]
    report = build_report(texts, truth, rule_hits, model_hits)
    print(report)
    RESULTS_PATH.write_text(report + "\n")


if __name__ == "__main__":
    main()
