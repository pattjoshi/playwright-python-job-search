"""Slows down password guessing: too many failed sign-ins in a short time are refused for a while."""

import threading
import time


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_s: float = 300.0, clock=time.monotonic):
        self.max_failures, self.window_s, self.clock = max_failures, window_s, clock
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """Seconds to wait before trying again (0 = allowed now)."""
        with self._lock:
            recent = self._recent(key)
            if len(recent) < self.max_failures:
                return 0
            return max(1, int(recent[0] + self.window_s - self.clock()) + 1)

    def failed(self, key: str) -> None:
        with self._lock:
            self._failures[key] = [*self._recent(key), self.clock()]

    def succeeded(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _recent(self, key: str) -> list[float]:
        cutoff = self.clock() - self.window_s
        return [t for t in self._failures.get(key, []) if t > cutoff]
