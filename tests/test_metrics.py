"""Tests for rolling UDP quality calculations."""

import pytest

from udpmonitor.models import MeasurementStatus
from udpmonitor.network.metrics import MetricsAccumulator


def test_metrics_calculates_loss_and_jitter() -> None:
    """Successful and timed-out packets should produce correct rolling values."""
    accumulator = MetricsAccumulator(window_size=3)
    accumulator.record_success(10.0)
    accumulator.record_success(14.0)
    metrics = accumulator.record_timeout()

    assert metrics.status is MeasurementStatus.TIMEOUT
    assert metrics.sent_packets == 3
    assert metrics.received_packets == 2
    assert metrics.packet_loss_percent == pytest.approx(100 / 3)
    assert metrics.jitter_milliseconds == 4.0


def test_health_score_is_unavailable_without_measurements() -> None:
    """An idle monitor should not imply a quality score."""
    assert MetricsAccumulator().snapshot().health_score is None
