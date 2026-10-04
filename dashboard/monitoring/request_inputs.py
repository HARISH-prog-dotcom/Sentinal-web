"""Collect every user-controlled string from a request so the detectors can scan it.

Supported: query parameters, JSON bodies (nested objects and lists), form-encoded bodies,
plain-text bodies, and the URL path when it contains unusual characters. This lets custom
scenarios from SentinelWeb Lab send input in any of these shapes.
"""
import json
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, unquote

MAX_BODY_CHARS = 20_000      # longer bodies are truncated before scanning
MAX_FIELDS = 200             # stop collecting after this many values
# Paths made only of these characters are ordinary routes and are not scanned.
PLAIN_PATH = re.compile(r"^[A-Za-z0-9/_.\-]*$")


@dataclass
class RequestInputs:
    """Strings to scan as (field name, value) pairs, plus the login username if one was sent."""

    fields: List[Tuple[str, str]]
    username: Optional[str]


def _flatten_json(value, prefix: str = "") -> Iterable[Tuple[str, str]]:
    """Yield (dotted.field.name, text) for every string or number inside a JSON value."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _flatten_json(item, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten_json(item, f"{prefix}[{index}]")
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        yield prefix or "body", str(value)


def _leaf_name(field: str) -> str:
    """'user.password' -> 'password', 'items[2].token' -> 'token' (used for the secret-field check)."""
    return re.split(r"[.\[]", field.replace("]", ""))[-1].lower()


def _body_fields(content_type: str, body_text: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """Fields from the request body, plus a username if the body has one."""
    content_type = content_type.lower()
    if not body_text:
        return [], None
    if "application/x-www-form-urlencoded" in content_type:
        pairs = parse_qsl(body_text, keep_blank_values=True)
        username = next((v for k, v in pairs if k == "username"), None)
        return pairs, username or None
    try:
        data = json.loads(body_text)
    except ValueError:
        return [("body", body_text)], None   # plain text or anything else: scan it as one value
    username = None
    if isinstance(data, dict) and data.get("username"):
        username = str(data["username"])
    return list(_flatten_json(data)), username


def extract_request_inputs(path: str, query_items: Iterable[Tuple[str, str]], content_type: str,
                           body: bytes, skip_fields: frozenset) -> RequestInputs:
    """Gather everything worth scanning. Secret fields (password, token, session) are dropped."""
    fields: List[Tuple[str, str]] = []
    decoded_path = unquote(path)
    if not PLAIN_PATH.match(decoded_path):
        fields.append(("path", decoded_path))
    fields += list(query_items)
    body_fields, username = _body_fields(content_type, body.decode("utf-8", errors="replace")[:MAX_BODY_CHARS])
    fields += body_fields
    safe_fields = [(name, value) for name, value in fields if _leaf_name(name) not in skip_fields]
    return RequestInputs(fields=safe_fields[:MAX_FIELDS], username=username)
