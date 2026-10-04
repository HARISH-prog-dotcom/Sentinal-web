"""Shared detection types: severities, event categories and findings."""
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """How serious an event is. Stored as plain text in the event log."""

    HIGH = "HIGH"      # a fixed rule matched a known attack pattern
    MEDIUM = "MEDIUM"  # model-only detection or a rate limit
    LOW = "LOW"        # a single failed login
    SAFE = "SAFE"      # nothing matched (shown as "Normal" in the UI)


class Category:
    """Event categories. These exact strings are stored in the log and shown in the UI."""

    SQL_INJECTION = "SQL Injection pattern"
    SQL_INJECTION_ML = "SQL Injection pattern (ML)"
    XSS = "XSS pattern"
    REPEATED_FAILED_LOGINS = "Repeated failed logins"
    FAILED_LOGIN = "Failed login"
    API_FLOOD = "Suspicious API activity"
    NORMAL = "Normal request"


@dataclass(frozen=True)
class Finding:
    """One suspicious thing a detector found in one input value."""

    category: str
    severity: Severity
    evidence: str
