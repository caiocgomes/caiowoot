import random

from app.services.rewarm_engine import next_delay


def test_rate_limit_stays_in_window():
    random.seed(42)
    samples = [next_delay() for _ in range(2000)]
    assert all(40.0 <= s <= 100.0 for s in samples)
    mean = sum(samples) / len(samples)
    # Mean should be ~70 (60 + mean of uniform(-20, 40) = 60 + 10 = 70)
    assert 65.0 <= mean <= 75.0


def test_rate_limit_is_randomized():
    random.seed(0)
    first = [next_delay() for _ in range(20)]
    random.seed(0)
    second = [next_delay() for _ in range(20)]
    # Deterministic under same seed
    assert first == second
    # And varies across samples
    assert len(set(first)) > 10
