"""Fixed detection rules: plain, readable regular expressions. Add your own harmless test patterns here."""
import re
from typing import Optional

# (rule name, compiled pattern)
SQL_INJECTION_RULES = [
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


def find_first_rule_match(rules, text: str) -> Optional[str]:
    """Name of the first rule whose pattern matches the text, or None."""
    for rule_name, pattern in rules:
        if pattern.search(text):
            return rule_name
    return None
