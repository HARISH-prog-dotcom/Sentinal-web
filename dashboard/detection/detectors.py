"""Detectors (strategy pattern): each one checks an input value for one kind of attack.

InputScanner runs every detector over every input, so adding a new attack type means
adding one detector class and passing it to the scanner in app.py.
"""
from typing import Iterable, List, Protocol, Tuple

from dashboard.detection.ml_model import SqlInjectionModel
from dashboard.detection.models import Category, Finding, Severity
from dashboard.detection.rules import SQL_INJECTION_RULES, XSS_RULES, find_first_rule_match


class Detector(Protocol):
    """Interface every detector implements."""

    def scan(self, field: str, value: str) -> List[Finding]:
        ...


class SqlInjectionDetector:
    """Fixed rules first (HIGH, blockable); the ML model catches what the rules miss (MEDIUM, review only)."""

    def __init__(self, model: SqlInjectionModel):
        self._model = model

    def scan(self, field: str, value: str) -> List[Finding]:
        rule_name = find_first_rule_match(SQL_INJECTION_RULES, value)
        score = self._model.score(value)                        # None when no model is loaded
        score_text = f", ML score {score:.2f}" if score is not None else ""
        if rule_name:
            # A fixed rule matched: high confidence. The model score is extra evidence.
            return [Finding(Category.SQL_INJECTION, Severity.HIGH,
                            f"Rule '{rule_name}' matched in field '{field}'{score_text}: {value[:60]}")]
        if score is not None and score >= self._model.threshold:
            # Only the model flagged it: lower severity, never auto-blocked.
            return [Finding(Category.SQL_INJECTION_ML, Severity.MEDIUM,
                            f"No rule matched, but ML score {score:.2f} >= {self._model.threshold} in field '{field}': {value[:60]}")]
        return []


class XssDetector:
    """Rules only: the training dataset covers SQL injection, not XSS."""

    def scan(self, field: str, value: str) -> List[Finding]:
        rule_name = find_first_rule_match(XSS_RULES, value)
        if not rule_name:
            return []
        return [Finding(Category.XSS, Severity.HIGH, f"Rule '{rule_name}' matched in field '{field}': {value[:60]}")]


class InputScanner:
    """Runs every detector over a list of (field, value) inputs."""

    def __init__(self, detectors: Iterable[Detector]):
        self._detectors = list(detectors)

    def scan_inputs(self, inputs: Iterable[Tuple[str, str]]) -> List[Finding]:
        return [finding for field, value in inputs for detector in self._detectors for finding in detector.scan(field, value)]
