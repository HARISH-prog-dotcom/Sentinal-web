"""Sliding-window counters and temporary locks, used for request-rate and brute-force limits."""
import time
from collections import defaultdict, deque


class SlidingWindowCounter:
    """Counts events per key inside a moving time window (e.g. failed logins per minute)."""

    def __init__(self):
        self._hits = defaultdict(deque)

    def record_hit(self, key: str, window_seconds: int) -> int:
        """Record one event for key and return how many happened in the last window_seconds."""
        now = time.time()
        hits = self._hits[key]
        hits.append(now)
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        return len(hits)

    def clear(self) -> None:
        self._hits.clear()


class LockRegistry:
    """Keys (an IP or an account) that are temporarily rate-limited."""

    def __init__(self):
        self._locked_until = {}

    def lock(self, key: str, seconds: int) -> None:
        self._locked_until[key] = time.time() + seconds

    def is_locked(self, key: str) -> bool:
        return self._locked_until.get(key, 0) > time.time()

    def clear(self) -> None:
        self._locked_until.clear()
