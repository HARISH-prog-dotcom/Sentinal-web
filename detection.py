"""Detection rules for SentinelWeb. Plain, readable rules - no magic."""
import re
import time
from collections import defaultdict, deque

import ml

# (rule name, compiled pattern). Add your own harmless test patterns here.
SQLI_RULES = [
    ("Boolean tautology (OR 1=1)", re.compile(r"(?i)\b(or|and)\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+")),
    ("Quote-based tautology", re.compile(r"(?i)'\s*(or|and)\s+'[^']*'\s*=\s*'")),
    ("UNION SELECT", re.compile(r"(?i)\bunion\b\s+(all\s+)?select\b")),
    ("Quote followed by SQL comment", re.compile(r"'\s*(--|#|/\*)")),
    ("Stacked query", re.compile(r"(?i);\s*(drop|delete|insert|update)\b")),
]

XSS_RULES = [
    ("<script> tag", re.compile(r"(?i)<\s*script")),
    ("Inline event handler", re.compile(r"(?i)\bon(error|load|click|mouseover|focus)\s*=")),
    ("javascript: URL", re.compile(r"(?i)javascript\s*:")),
    ("Embedded HTML element", re.compile(r"(?i)<\s*(img|svg|iframe)\b")),
]

# Plain-language text shown on the dashboard. An AI model could replace
# this later, but treat its output as advice, not as the security decision.
EXPLAIN = {
    "SQL Injection pattern": "The input contains text shaped like SQL code. Attackers use this to try to change a database query. This is a pattern match, so a human should review it.",
    "SQL Injection pattern (ML)": "No fixed rule matched, but the trained model scored this input as very similar to known SQL injection examples. This is a statistical guess, so it is flagged for human review and not blocked.",
    "XSS pattern": "The input contains HTML or script-like text. If a page displayed it unsafely, a browser might run it as code. This is a pattern match, so review it.",
    "Repeated failed logins": "Many failed login attempts hit one account in a short time. This can mean password guessing, so the account was temporarily rate-limited.",
    "Failed login": "A single failed login is normal. It is recorded so repeated attempts can be counted.",
    "Suspicious API activity": "One client sent far more requests than normal in a short window, so it was temporarily rate-limited.",
    "Normal request": "No detection rule matched this request.",
}


def sqli_rule_match(value):
    """Name of the first SQLi rule that matches, or None."""
    for rule_name, pattern in SQLI_RULES:
        if pattern.search(value):
            return rule_name
    return None


def scan_text(field, value):
    """Return a list of findings for one input value (rules first, then the ML model)."""
    findings = []

    # --- SQL injection: rules + trained model ---
    rule = sqli_rule_match(value)
    ml_score = ml.score(value)                      # None when no model is loaded
    ml_hit = ml_score is not None and ml_score >= ml.ML_THRESHOLD
    ml_text = f", ML score {ml_score:.2f}" if ml_score is not None else ""
    if rule:
        # A fixed rule matched: high confidence. The model score is shown as extra evidence.
        findings.append({
            "category": "SQL Injection pattern", "severity": "HIGH",
            "evidence": f"Rule '{rule}' matched in field '{field}'{ml_text}: {value[:60]}",
        })
    elif ml_hit:
        # Only the model flagged it: lower severity, review needed, never auto-blocked.
        findings.append({
            "category": "SQL Injection pattern (ML)", "severity": "MEDIUM",
            "evidence": f"No rule matched, but ML score {ml_score:.2f} >= {ml.ML_THRESHOLD} in field '{field}': {value[:60]}",
        })

    # --- XSS: rules only (the SQLi dataset does not cover XSS) ---
    for rule_name, pattern in XSS_RULES:
        if pattern.search(value):
            findings.append({
                "category": "XSS pattern", "severity": "HIGH",
                "evidence": f"Rule '{rule_name}' matched in field '{field}': {value[:60]}",
            })
            break
    return findings


class SlidingWindow:
    """Counts events per key inside a time window (e.g. failed logins per minute)."""

    def __init__(self):
        self.hits = defaultdict(deque)

    def hit(self, key, window_seconds):
        now = time.time()
        q = self.hits[key]
        q.append(now)
        while q and now - q[0] > window_seconds:
            q.popleft()
        return len(q)

    def clear(self):
        self.hits.clear()
