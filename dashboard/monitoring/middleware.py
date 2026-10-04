"""The monitoring pipeline that runs in front of the demo app.

Only requests to /demo/* are monitored (use it on YOUR OWN demo app only). Each request passes
four checks in order; each check can stop the request:
    1. already locked?   2. request rate   3. input scan   4. failed-login tracking
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from dashboard.config import Settings
from dashboard.detection import Category, InputScanner, Severity
from dashboard.detection.explanations import explain
from dashboard.monitoring.rate_limiter import LockRegistry, SlidingWindowCounter
from dashboard.monitoring.request_inputs import extract_request_inputs
from dashboard.storage import EventRepository

MONITORED_PREFIX = "/demo"
LOGIN_PATH = "/demo/login"


class RequestMonitor:
    """ASGI middleware callable: register with app.middleware("http")(monitor)."""

    def __init__(self, settings: Settings, scanner: InputScanner, repository: EventRepository):
        self._settings = settings
        self._scanner = scanner
        self._repository = repository
        self._request_counter = SlidingWindowCounter()
        self._failed_login_counter = SlidingWindowCounter()
        self._locks = LockRegistry()

    def reset(self) -> None:
        """Forget all counters and locks (used by the dashboard's reset button)."""
        self._request_counter.clear()
        self._failed_login_counter.clear()
        self._locks.clear()

    async def __call__(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(MONITORED_PREFIX):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        inputs = extract_request_inputs(path, request.query_params.multi_items(), request.headers.get("content-type", ""),
                                        await request.body(), self._settings.skip_fields)

        def log_event(category: str, severity: Severity, evidence: str, action: str) -> None:
            self._repository.add_event(ip, request.method, path, category, severity.value, evidence, action, explain(category))

        # 1. Already rate-limited? Rejected without logging again, so the log cannot be flooded.
        if self._locks.is_locked(f"ip:{ip}") or (inputs.username and self._locks.is_locked(f"user:{inputs.username}")):
            return JSONResponse({"error": "Rate-limited. Try again later."}, status_code=429)

        # 2. Too many requests from one IP?
        recent_requests = self._request_counter.record_hit(ip, self._settings.request_window_seconds)
        if recent_requests > self._settings.request_limit:
            self._locks.lock(f"ip:{ip}", self._settings.lock_seconds)
            log_event(Category.API_FLOOD, Severity.MEDIUM,
                      f"{recent_requests} requests in {self._settings.request_window_seconds}s (demo limit {self._settings.request_limit})",
                      "Rate-limited")
            return JSONResponse({"error": "Rate-limited."}, status_code=429)

        # 3. Suspicious input? Only HIGH findings are blocked (and only when blocking is on).
        findings = self._scanner.scan_inputs(inputs.fields)
        if findings:
            top = findings[0]
            should_block = self._settings.block_high_severity and top.severity == Severity.HIGH
            log_event(top.category, top.severity, top.evidence, "Blocked (demo)" if should_block else "Flagged")
            if should_block:
                return JSONResponse({"error": "Blocked by SentinelWeb (demo)."}, status_code=403)

        response = await call_next(request)

        # 4. Failed-login tracking (needs the app's response status).
        if path == LOGIN_PATH and response.status_code == 401 and inputs.username:
            self._track_failed_login(inputs.username, log_event)
        elif not findings:
            log_event(Category.NORMAL, Severity.SAFE, "No rule matched", "Allowed")
        return response

    def _track_failed_login(self, username: str, log_event) -> None:
        limit, window = self._settings.login_limit, self._settings.login_window_seconds
        failures = self._failed_login_counter.record_hit(username, window)
        if failures >= limit:
            self._locks.lock(f"user:{username}", self._settings.lock_seconds)
            log_event(Category.REPEATED_FAILED_LOGINS, Severity.MEDIUM,
                      f"{failures} failed attempts in {window}s for '{username[:30]}' (demo threshold {limit})", "Rate-limited account")
        else:
            log_event(Category.FAILED_LOGIN, Severity.LOW, f"Failed attempt {failures} of {limit} for '{username[:30]}'", "Allowed")
