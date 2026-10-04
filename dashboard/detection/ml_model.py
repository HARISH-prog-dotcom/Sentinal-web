"""The trained SQL injection model: loading, scoring and its training metrics.

If the model file is missing or cannot be loaded, SentinelWeb runs with rules only.
"""
import json
import re
from pathlib import Path
from typing import Optional

from dashboard.config import PROJECT_ROOT

MODEL_PATH = PROJECT_ROOT / "models" / "sqli_model.joblib"
METRICS_PATH = PROJECT_ROOT / "models" / "metrics.json"
# Chosen from the threshold table in the README: high recall, about zero false positives on the test split.
ML_THRESHOLD = 0.70


def normalize_text(text) -> str:
    """Same cleaning for training data and live requests: collapse whitespace, cap the length."""
    return re.sub(r"\s+", " ", str(text)).strip()[:500]


class SqlInjectionModel:
    """Wraps the scikit-learn pipeline saved by scripts/train_model.py."""

    def __init__(self, model_path: Path = MODEL_PATH, metrics_path: Path = METRICS_PATH, threshold: float = ML_THRESHOLD):
        self.threshold = threshold
        self._metrics_path = metrics_path
        self._pipeline = None
        try:
            import joblib
            self._pipeline = joblib.load(model_path)
        except Exception as error:  # missing file, version mismatch, scikit-learn not installed
            print(f"[SentinelWeb] ML model not loaded ({type(error).__name__}); running with rules only. "
                  "Run 'python scripts/train_model.py' to build it.")

    @property
    def is_available(self) -> bool:
        return self._pipeline is not None

    def score(self, text: str) -> Optional[float]:
        """0-1 score for 'looks like SQL injection', or None without a model.

        This is a model score, NOT the probability that an attack is happening.
        """
        if self._pipeline is None:
            return None
        text = normalize_text(text)
        if len(text) < 3:
            return 0.0
        return float(self._pipeline.predict_proba([text])[0][1])

    def training_metrics(self) -> dict:
        """Metrics written by the training script (empty if the file is missing)."""
        try:
            return json.loads(self._metrics_path.read_text())
        except Exception:
            return {}
