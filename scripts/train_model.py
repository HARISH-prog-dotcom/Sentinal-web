"""Train the SQL injection classifier from data/SQLiV3.csv.

Run from the project folder:  python scripts/train_model.py
Writes models/sqli_model.joblib and models/metrics.json.
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))   # lets this script import the dashboard package

import joblib  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, precision_score, recall_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402

from dashboard.detection.ml_model import METRICS_PATH, ML_THRESHOLD, MODEL_PATH, normalize_text  # noqa: E402

DATASET_PATH = PROJECT_ROOT / "data" / "SQLiV3.csv"


def load_clean_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    """Load SQLiV3.csv and clean it. Label 1 = SQL injection, 0 = normal."""
    df = pd.read_csv(path, dtype=str)
    # A few hundred rows are corrupted (a comma inside the text shifted the columns).
    df = df[df["Label"].isin(["0", "1"])].dropna(subset=["Sentence"]).copy()
    df["text"] = df["Sentence"].map(normalize_text)
    df["y"] = df["Label"].astype(int)
    df = df[df["text"].str.len() > 0]
    df = df[df.groupby("text")["y"].transform("nunique") == 1]   # drop contradictory duplicates
    return df.drop_duplicates("text").reset_index(drop=True)


def split_dataset(df: pd.DataFrame):
    """Fixed 80/20 split (same seed everywhere, so evaluate.py uses the same test rows)."""
    return train_test_split(df["text"], df["y"], test_size=0.2, random_state=42, stratify=df["y"])


def build_pipeline():
    """Character n-grams catch punctuation and keyword fragments typical of injection."""
    return make_pipeline(
        TfidfVectorizer(analyzer="char", ngram_range=(2, 5), lowercase=True, sublinear_tf=True, max_features=200_000),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )


def main() -> None:
    df = load_clean_dataset()
    x_train, x_test, y_train, y_test = split_dataset(df)
    print(f"Clean rows: {len(df)}  (normal {int((df.y == 0).sum())}, SQL injection {int((df.y == 1).sum())})")

    pipeline = build_pipeline()
    started = time.time()
    pipeline.fit(x_train, y_train)
    print(f"Trained in {time.time() - started:.1f}s")

    scores = pipeline.predict_proba(x_test)[:, 1]
    predictions = (scores >= ML_THRESHOLD).astype(int)
    is_benign = (y_test == 0)
    metrics = {
        "dataset": "SQLiV3.csv (Kaggle)",
        "rows_clean": len(df), "train_rows": len(x_train), "test_rows": len(x_test),
        "threshold": ML_THRESHOLD,
        "accuracy": round(accuracy_score(y_test, predictions), 4),
        "precision": round(precision_score(y_test, predictions), 4),
        "recall": round(recall_score(y_test, predictions), 4),
        "false_positive_rate": round(float(((predictions == 1) & is_benign).sum() / is_benign.sum()), 4),
    }
    print(json.dumps(metrics, indent=2))

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print("Saved", MODEL_PATH)


if __name__ == "__main__":
    main()
