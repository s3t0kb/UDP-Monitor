"""Persistence models for monitoring sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from udpmonitor.models.metrics import NetworkMetrics


@dataclass(frozen=True, slots=True)
class MonitorSession:
    """A named interval of UDP measurement collection."""

    id: int
    started_at: datetime
    ended_at: datetime | None
    host: str
    port: int


@dataclass(frozen=True, slots=True)
class StoredMeasurement:
    """One persisted network-metrics snapshot."""

    id: int
    session_id: int
    observed_at: datetime
    metrics: NetworkMetrics


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Aggregate UDP quality statistics for one monitoring session."""

    session_id: int
    host: str
    port: int
    started_at: datetime
    ended_at: datetime | None
    sample_count: int
    success_count: int
    average_rtt_milliseconds: float | None
    average_jitter_milliseconds: float | None
    average_loss_percent: float | None

    @property
    def success_rate_percent(self) -> float | None:
        """Return the share of measurements that received a reply, or None if no samples exist."""
        if self.sample_count == 0:
            return None
        return self.success_count / self.sample_count * 100.0

    @property
    def duration_text(self) -> str:
        """Return a human-readable duration, or an em dash if the session is still running."""
        if self.ended_at is None:
            return "—"
        total_seconds = int((self.ended_at - self.started_at).total_seconds())
        minutes, seconds = divmod(max(total_seconds, 0), 60)
        return f"{minutes}m {seconds}s"
