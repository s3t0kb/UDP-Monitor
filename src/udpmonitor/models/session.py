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
