from app.core.rate_limit import LoginRateLimiter, SlidingWindowLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_sliding_window_blocks_then_expires() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10, clock=clock)
    assert limiter.retry_after("k") == 0
    limiter.hit("k")
    clock.now += 3
    limiter.hit("k")
    assert limiter.retry_after("k") == 7
    clock.now += 7
    assert limiter.retry_after("k") == 0  # first hit left the window
    limiter.reset("k")
    assert limiter.retry_after("k") == 0


def test_login_limiter_has_per_client_ceiling() -> None:
    limiter = LoginRateLimiter(attempts=2, window_seconds=60)
    for i in range(8):
        limiter.record_failure("1.2.3.4", f"user{i}@edupulse.example")
    assert limiter.retry_after("1.2.3.4", "fresh@edupulse.example") > 0
    assert limiter.retry_after("5.6.7.8", "fresh@edupulse.example") == 0


def test_login_limiter_normalises_email() -> None:
    limiter = LoginRateLimiter(attempts=1, window_seconds=60)
    limiter.record_failure("c", " Admin@Edupulse.Example ")
    assert limiter.retry_after("c", "admin@edupulse.example") > 0
    limiter.record_success("c", "ADMIN@edupulse.example")
    assert limiter.retry_after("c", "admin@edupulse.example") == 0
