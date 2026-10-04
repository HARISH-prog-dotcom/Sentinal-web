"""Gateway to SentinelWeb (adapter): the only code that sends HTTP requests to the target server."""
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, List, Optional, Tuple

USER_AGENT = "SentinelWeb-Lab/2.0"


class SentinelUnreachable(Exception):
    """SentinelWeb did not answer at all (not running, wrong address, firewall)."""


class SentinelGateway:
    def __init__(self, base_url: str, timeout_seconds: int = 10):
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    # ---------- low level ----------
    def send(self, method: str, path: str, query: Optional[dict] = None, body_type: str = "none", body: Any = None) -> Tuple[int, bytes]:
        """Send one request. HTTP error codes (403, 429...) are results, not failures."""
        url = self.base_url + urllib.parse.quote(path, safe="/")
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers, data = {"User-Agent": USER_AGENT}, None
        if body_type == "json":
            headers["Content-Type"], data = "application/json", json.dumps(body).encode()
        elif body_type == "form":
            headers["Content-Type"], data = "application/x-www-form-urlencoded", urllib.parse.urlencode(body or {}).encode()
        elif body_type == "text":
            headers["Content-Type"], data = "text/plain; charset=utf-8", str(body or "").encode()
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()
        except (urllib.error.URLError, OSError):
            raise SentinelUnreachable(f"SentinelWeb is not reachable at {self.base_url}. Is it running?") from None

    def _get_json(self, path: str, default, query: Optional[dict] = None):
        status, raw = self.send("GET", path, query)
        try:
            return json.loads(raw) if status == 200 else default
        except ValueError:
            return default

    # ---------- SentinelWeb API ----------
    def latest_event_id(self) -> int:
        rows = self._get_json("/api/events", [], {"limit": 1})
        return rows[0]["id"] if rows else 0

    def events_after(self, event_id: int) -> List[dict]:
        """Events logged after event_id, oldest first. /api calls are not monitored, so these come from our requests."""
        rows = self._get_json("/api/events", [], {"limit": 200})
        return sorted((event for event in rows if event["id"] > event_id), key=lambda event: event["id"])

    def model_info(self) -> dict:
        return self._get_json("/api/model", {})

    def demo_endpoints(self) -> dict:
        """What the demo app offers (served by SentinelWeb 2.x; empty for older versions)."""
        return self._get_json("/api/demo/endpoints", {})

    def reset(self) -> bool:
        status, _ = self.send("POST", "/api/reset")
        return status == 200
