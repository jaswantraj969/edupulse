"""In-memory sliding-window limiters for failed login attempts and self sign-up requests.

State is per API process. With several workers or replicas the effective limit is multiplied;
a shared store (e.g. Redis) would be needed for a multi-instance deployment.
"""

import time
from collections import deque
from collections.abc import Callable
from threading import Lock


class SlidingWindowLimiter:
    def __init__(
        self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        while events and events[0] <= now - self.window:
            events.popleft()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until ``key`` may try again; 0 if it is not currently blocked."""
        with self._lock:
            now = self._clock()
            events = self._prune(key, now)
            if len(events) < self.limit:
                return 0
            return max(1, int(events[0] + self.window - now + 0.999))

    def hit(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


class LoginRateLimiter:
    """Blocks a (client, account) pair after N failures, and a client after 4N failures."""

    def __init__(self, attempts: int, window_seconds: float) -> None:
        self.per_account = SlidingWindowLimiter(attempts, window_seconds)
        self.per_client = SlidingWindowLimiter(attempts * 4, window_seconds)

    @staticmethod
    def _account_key(client: str, email: str) -> str:
        return f"{client}|{email.strip().lower()}"

    def retry_after(self, client: str, email: str) -> int:
        return max(
            self.per_account.retry_after(self._account_key(client, email)),
            self.per_client.retry_after(client),
        )

    def record_failure(self, client: str, email: str) -> None:
        self.per_account.hit(self._account_key(client, email))
        self.per_client.hit(client)

    def record_success(self, client: str, email: str) -> None:
        self.per_account.reset(self._account_key(client, email))
