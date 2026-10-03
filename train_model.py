"""Train the SQL injection classifier from data/SQLiV3.csv. Run: python train_model.py"""
import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from ml import ML_THRESHOLD, METRICS_PATH, MODEL_PATH, normalize

CSV = Path(__file__).parent / "data" / "SQLiV3.csv"


def load_clean(path=CSV):
    """Load SQLiV3.csv and clean it. Label 1 = SQL injection, 0 = normal."""
    df = pd.read_csv(path, dtype=str)
    # A few hundred rows are corrupted (a comma inside the text shifted the columns).
    df = df[df["Label"].isin(["0", "1"])].dropna(subset=["Sentence"]).copy()
    df["text"] = df["Sentence"].map(normalize)
    df["y"] = df["Label"].astype(int)
    df = df[df["text"].str.len() > 0]
    df = df[df.groupby("text")["y"].transform("nunique") == 1]   # drop contradictory duplicates
    return df.drop_duplicates("text").reset_index(drop=True)


def split(df):
    return train_test_split(df["text"], df["y"], test_size=0.2, random_state=42, stratify=df["y"])


if __name__ == "__main__":
    df = load_clean()
    X_train, X_test, y_train, y_test = split(df)
    print(f"Clean rows: {len(df)}  (normal {int((df.y == 0).sum())}, SQL injection {int((df.y == 1).sum())})")

    model = make_pipeline(
        TfidfVectorizer(analyzer="char", ngram_range=(2, 5), lowercase=True, sublinear_tf=True, max_features=200_000),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )
    t = time.time()
    model.fit(X_train, y_train)
    print(f"Trained in {time.time() - t:.1f}s")

    scores = model.predict_proba(X_test)[:, 1]
    pred = (scores >= ML_THRESHOLD).astype(int)
    benign = (y_test == 0)
    metrics = {
        "dataset": "SQLiV3.csv (Kaggle)",
        "rows_clean": len(df), "train_rows": len(X_train), "test_rows": len(X_test),
        "threshold": ML_THRESHOLD,
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred), 4),
        "recall": round(recall_score(y_test, pred), 4),
        "false_positive_rate": round(float(((pred == 1) & benign).sum() / benign.sum()), 4),
    }
    print(json.dumps(metrics, indent=2))

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print("Saved", MODEL_PATH)
