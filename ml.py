"""Loads the trained SQL injection model and scores text.
If the model file is missing or cannot be loaded, SentinelWeb falls back to rules only."""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
MODEL_PATH = BASE / "models" / "sqli_model.joblib"
METRICS_PATH = BASE / "models" / "metrics.json"

ML_THRESHOLD = 0.70   # chosen from the threshold table in README (high recall, ~0 false positives on the test split)

_model = None
try:
    import joblib
    _model = joblib.load(MODEL_PATH)
except Exception as e:  # missing file, version mismatch, scikit-learn not installed
    print(f"[SentinelWeb] ML model not loaded ({type(e).__name__}); running with rules only. "
          "Run 'python train_model.py' to build it.")


def normalize(text):
    """Same cleaning for training and live requests: collapse whitespace."""
    return re.sub(r"\s+", " ", str(text)).strip()[:500]


def available():
    return _model is not None


def score(text):
    """Return a 0-1 score for 'looks like SQL injection', or None if no model.
    This is a model score, NOT a probability that an attack is happening."""
    if _model is None:
        return None
    text = normalize(text)
    if len(text) < 3:
        return 0.0
    return float(_model.predict_proba([text])[0][1])


def info():
    try:
        return json.loads(METRICS_PATH.read_text())
    except Exception:
        return {}
