"""Typed domain models for UDP network measurements."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MeasurementStatus(StrEnum):
    """State of the most recently completed UDP heartbeat."""

    IDLE = "idle"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class NetworkMetrics:
    """A point-in-time UDP quality summary for presentation and persistence."""

    status: MeasurementStatus = MeasurementStatus.IDLE
    sent_packets: int = 0
    received_packets: int = 0
    packet_loss_percent: float | None = None
    rtt_milliseconds: float | None = None
    jitter_milliseconds: float | None = None
    timeout_count: int = 0
    last_error: str | None = None

    @property
    def health_score(self) -> int | None:
        """Return a conservative 0-100 UDP health score when data exists."""
        if self.packet_loss_percent is None:
            return None
        loss_penalty = self.packet_loss_percent
        jitter_penalty = min((self.jitter_milliseconds or 0.0) * 2.0, 30.0)
        rtt_penalty = min(max((self.rtt_milliseconds or 0.0) - 50.0, 0.0) / 10.0, 20.0)
        return max(0, round(100.0 - loss_penalty - jitter_penalty - rtt_penalty))
