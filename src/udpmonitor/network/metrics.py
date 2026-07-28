"""Rolling calculations for UDP quality metrics."""

from __future__ import annotations

from collections import deque

from udpmonitor.models import MeasurementStatus, NetworkMetrics

DEFAULT_WINDOW_SIZE = 60


class MetricsAccumulator:
    """Maintain a bounded measurement window and derive UDP quality metrics."""

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        """Create a metric accumulator with a positive rolling-window size."""
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self._results: deque[float | None] = deque(maxlen=window_size)
        self._timeout_count = 0
        self._last_error: str | None = None
        self._status = MeasurementStatus.IDLE

    def record_success(self, rtt_milliseconds: float) -> NetworkMetrics:
        """Record a successful heartbeat and return the refreshed summary."""
        if rtt_milliseconds < 0:
            raise ValueError("rtt_milliseconds must not be negative")
        self._results.append(rtt_milliseconds)
        self._status = MeasurementStatus.SUCCESS
        self._last_error = None
        return self.snapshot()

    def record_timeout(self) -> NetworkMetrics:
        """Record an unanswered heartbeat and return the refreshed summary."""
        self._results.append(None)
        self._timeout_count += 1
        self._status = MeasurementStatus.TIMEOUT
        self._last_error = None
        return self.snapshot()

    def record_error(self, message: str) -> NetworkMetrics:
        """Record a transport error without treating it as a successful packet."""
        self._status = MeasurementStatus.ERROR
        self._last_error = message
        return self.snapshot()

    def snapshot(self) -> NetworkMetrics:
        """Return an immutable summary of the current rolling window."""
        sent = len(self._results)
        successful_rtts = [result for result in self._results if result is not None]
        received = len(successful_rtts)
        loss = ((sent - received) / sent * 100.0) if sent else None
        latest_rtt = successful_rtts[-1] if successful_rtts else None
        jitter = self._jitter(successful_rtts)
        return NetworkMetrics(
            status=self._status,
            sent_packets=sent,
            received_packets=received,
            packet_loss_percent=loss,
            rtt_milliseconds=latest_rtt,
            jitter_milliseconds=jitter,
            timeout_count=self._timeout_count,
            last_error=self._last_error,
        )

    @staticmethod
    def _jitter(rtts: list[float]) -> float | None:
        """Calculate mean absolute RTT delta, a stable practical jitter measure."""
        if len(rtts) < 2:
            return None
        deltas = [abs(current - previous) for previous, current in zip(rtts, rtts[1:])]
        return sum(deltas) / len(deltas)
