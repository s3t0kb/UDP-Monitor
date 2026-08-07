"""Manual event log entries attached to a monitoring session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EventCategory(StrEnum):
    """User-assigned category for a logged event.

    Automatic detection of Discord/VRChat disconnect events is not
    implemented yet; DISCORD and VRCHAT exist so a user can tag a
    manually-logged event as related to one of them while that
    detection is built in a later version.
    """

    MANUAL = "manual"
    DISCORD = "discord"
    VRCHAT = "vrchat"


@dataclass(frozen=True, slots=True)
class MonitoringEvent:
    """One timestamped note attached to a monitoring session's timeline."""

    id: int
    session_id: int
    occurred_at: datetime
    category: EventCategory
    description: str
