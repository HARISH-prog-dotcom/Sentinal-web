"""Scenario model and validation.

A scenario is plain JSON, so new ones can be added from the UI, imported, or dropped into scenarios/packs/:

    {
      "id": "sqli-rule", "title": "SQL injection", "group": "Injection attacks",
      "description": "Why this request is interesting", "expect": "HIGH",
      "steps": [
        {"method": "GET", "path": "/demo/search", "query": {"q": "' OR '1'='1"}},
        {"method": "POST", "path": "/demo/login", "body_type": "json",
         "body": {"username": "alice", "password": "guess{n}"}, "repeat": 6}
      ]
    }

"{n}" inside any query or body value is replaced by the repetition number (1, 2, 3, ...).
Safety: paths must stay under /demo/, so scenarios can only reach SentinelWeb's demo app.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
BODY_TYPES = ("none", "json", "form", "text")
EXPECTATIONS = ("SAFE", "LOW", "MEDIUM", "HIGH", "ANY")
SEVERITY_LABELS = {"SAFE": "Normal", "LOW": "Low", "MEDIUM": "Medium", "HIGH": "High", "ANY": "Any result"}
MAX_STEPS, MAX_REPEAT, MAX_TOTAL_REQUESTS = 10, 50, 100
MAX_TEXT, MAX_FIELDS = 2000, 30
SAFE_PATH = re.compile(r"^/demo(/[A-Za-z0-9._~!$&'()*+,;=:@%\-<>\"{}\[\] ]*)*$")
SECRET_FIELDS = {"password", "token", "session", "secret"}


class ScenarioError(ValueError):
    """A scenario that cannot be accepted, with a message meant for the user."""


def _clean_text(value: Any, name: str, max_length: int = MAX_TEXT) -> str:
    text = "" if value is None else str(value)
    if len(text) > max_length:
        raise ScenarioError(f"{name} is too long (max {max_length} characters).")
    return text


def _clean_mapping(value: Any, name: str) -> Dict[str, str]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ScenarioError(f"{name} must be an object of field: value pairs.")
    if len(value) > MAX_FIELDS:
        raise ScenarioError(f"{name} has too many fields (max {MAX_FIELDS}).")
    return {_clean_text(k, f"{name} field name", 100): _clean_text(v, f"{name} value") for k, v in value.items()}


def _fill_placeholder(value: Any, number: int) -> Any:
    """Replace {n} with the repetition number inside strings, lists and objects."""
    if isinstance(value, str):
        return value.replace("{n}", str(number))
    if isinstance(value, dict):
        return {key: _fill_placeholder(item, number) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill_placeholder(item, number) for item in value]
    return value


def _readable_pairs(pairs: Dict[str, Any]) -> str:
    """'q=1 OR 1=1&page=2' for display (not URL-encoded, so people can read it)."""
    return "&".join(f"{key}={value}" for key, value in pairs.items())


def _mask_secrets(value: Any) -> Any:
    """Hide password-like values when a scenario is described in the UI."""
    if isinstance(value, dict):
        return {k: ("•••" if k.lower() in SECRET_FIELDS else _mask_secrets(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_secrets(item) for item in value]
    return value


@dataclass
class RequestStep:
    """One request (optionally repeated) that a scenario sends."""

    method: str = "GET"
    path: str = "/demo/search"
    query: Dict[str, str] = field(default_factory=dict)
    body_type: str = "none"
    body: Any = None
    repeat: int = 1

    @classmethod
    def from_dict(cls, data: dict) -> "RequestStep":
        if not isinstance(data, dict):
            raise ScenarioError("Each step must be an object.")
        method = str(data.get("method", "GET")).upper()
        if method not in ALLOWED_METHODS:
            raise ScenarioError(f"Method must be one of {', '.join(ALLOWED_METHODS)}.")
        path = _clean_text(data.get("path", ""), "Path", 200).strip()
        if not path.startswith("/demo") or ".." in path or "//" in path or not SAFE_PATH.match(path):
            raise ScenarioError("Path must start with /demo/ (scenarios can only reach the SentinelWeb demo app).")
        body_type = str(data.get("body_type") or ("json" if data.get("body") not in (None, "") else "none")).lower()
        if body_type not in BODY_TYPES:
            raise ScenarioError(f"Body type must be one of {', '.join(BODY_TYPES)}.")
        body = data.get("body")
        if body_type == "none":
            body = None
        elif body_type == "form":
            body = _clean_mapping(body, "Form body")
        elif body_type == "text":
            body = _clean_text(body, "Text body")
        elif isinstance(body, str):                         # JSON typed in a text box
            try:
                body = json.loads(body) if body.strip() else {}
            except ValueError:
                raise ScenarioError("JSON body is not valid JSON.") from None
        if body_type == "json" and len(json.dumps(body)) > MAX_TEXT:
            raise ScenarioError(f"JSON body is too long (max {MAX_TEXT} characters).")
        try:
            repeat = int(data.get("repeat", 1))
        except (TypeError, ValueError):
            raise ScenarioError("Repeat must be a whole number.") from None
        if not 1 <= repeat <= MAX_REPEAT:
            raise ScenarioError(f"Repeat must be between 1 and {MAX_REPEAT}.")
        return cls(method, path, _clean_mapping(data.get("query"), "Query"), body_type, body, repeat)

    def expand(self) -> List[dict]:
        """The concrete requests this step sends, with {n} filled in."""
        return [{"method": self.method, "path": self.path, "query": _fill_placeholder(self.query, number),
                 "body_type": self.body_type, "body": _fill_placeholder(self.body, number)}
                for number in range(1, self.repeat + 1)]

    def describe(self) -> str:
        """Human-readable summary, e.g. '6 × POST /demo/login (JSON: {"username": "alice", "password": "•••"})'."""
        text = f"{self.method} {self.path}"
        if self.query:
            text += "?" + _readable_pairs(self.query)
        if self.body_type == "json":
            text += f" (JSON: {json.dumps(_mask_secrets(self.body), ensure_ascii=False)})"
        elif self.body_type == "form":
            text += f" (form: {_readable_pairs(_mask_secrets(self.body))})"
        elif self.body_type == "text":
            text += f" (text: {self.body})"
        return (f"{self.repeat} × " if self.repeat > 1 else "") + text

    def to_dict(self) -> dict:
        data = {"method": self.method, "path": self.path}
        if self.query:
            data["query"] = self.query
        if self.body_type != "none":
            data["body_type"], data["body"] = self.body_type, self.body
        if self.repeat != 1:
            data["repeat"] = self.repeat
        return data


@dataclass
class Scenario:
    id: str
    title: str
    group: str
    description: str
    expect: str
    steps: List[RequestStep]
    expect_text: str = ""
    source: str = "custom"          # builtin | pack:<file> | custom

    @classmethod
    def from_dict(cls, data: dict, source: str = "custom", scenario_id: Optional[str] = None) -> "Scenario":
        if not isinstance(data, dict):
            raise ScenarioError("A scenario must be a JSON object.")
        title = _clean_text(data.get("title"), "Title", 80).strip()
        if not title:
            raise ScenarioError("Give the scenario a title.")
        expect = str(data.get("expect", "ANY")).upper()
        if expect not in EXPECTATIONS:
            raise ScenarioError(f"Expected result must be one of {', '.join(EXPECTATIONS)}.")
        raw_steps = data.get("steps") or []
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ScenarioError("Add at least one request step.")
        if len(raw_steps) > MAX_STEPS:
            raise ScenarioError(f"A scenario can have at most {MAX_STEPS} steps.")
        steps = [RequestStep.from_dict(step) for step in raw_steps]
        if sum(step.repeat for step in steps) > MAX_TOTAL_REQUESTS:
            raise ScenarioError(f"A scenario can send at most {MAX_TOTAL_REQUESTS} requests in total.")
        return cls(id=scenario_id or str(data.get("id") or ""), title=title,
                   group=_clean_text(data.get("group"), "Group", 40).strip() or "Custom scenarios",
                   description=_clean_text(data.get("description"), "Description", 400).strip(),
                   expect=expect, steps=steps, expect_text=_clean_text(data.get("expect_text"), "Expected text", 80).strip(),
                   source=source)

    def total_requests(self) -> int:
        return sum(step.repeat for step in self.steps)

    def describe(self) -> str:
        return " → ".join(step.describe() for step in self.steps)

    def to_dict(self) -> dict:
        """Storage format (what custom.json and exported files contain)."""
        data = {"id": self.id, "title": self.title, "group": self.group, "description": self.description,
                "expect": self.expect, "steps": [step.to_dict() for step in self.steps]}
        if self.expect_text:
            data["expect_text"] = self.expect_text
        return data

    def to_public_dict(self) -> dict:
        """What the UI receives: the stored fields plus display helpers."""
        return {**self.to_dict(), "source": self.source, "editable": self.source == "custom",
                "sends": self.describe(), "total_requests": self.total_requests(),
                "expect_text": self.expect_text or SEVERITY_LABELS[self.expect]}
