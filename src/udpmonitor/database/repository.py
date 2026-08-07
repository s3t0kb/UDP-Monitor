"""SQLite repository for monitoring sessions and measurements."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from udpmonitor.models import EventCategory, MeasurementStatus, MonitorSession, MonitoringEvent, NetworkMetrics, SessionSummary, StoredMeasurement

SCHEMA_VERSION = 2
DATABASE_FILE_NAME = "udp-monitor.sqlite3"


class SessionRepository:
    """Provide transaction-safe storage without exposing SQLite to the UI."""

    def __init__(self, database_path: Path) -> None:
        """Open a SQLite database and create the initial schema if necessary."""
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._connection.close()

    def start_session(self, host: str, port: int, started_at: datetime | None = None) -> MonitorSession:
        """Create and return a new monitoring session."""
        timestamp = started_at or datetime.now(UTC)
        cursor = self._connection.execute(
            "INSERT INTO sessions (started_at, host, port) VALUES (?, ?, ?)",
            (timestamp.isoformat(), host, port),
        )
        self._connection.commit()
        return MonitorSession(cursor.lastrowid, timestamp, None, host, port)

    def end_session(self, session_id: int, ended_at: datetime | None = None) -> None:
        """Mark an active session as finished."""
        timestamp = ended_at or datetime.now(UTC)
        self._connection.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (timestamp.isoformat(), session_id))
        self._connection.commit()

    def record_measurement(self, session_id: int, metrics: NetworkMetrics, observed_at: datetime | None = None) -> StoredMeasurement:
        """Persist a network-metrics snapshot in the specified session."""
        timestamp = observed_at or datetime.now(UTC)
        cursor = self._connection.execute(
            """INSERT INTO measurements
            (session_id, observed_at, status, sent_packets, received_packets, packet_loss_percent,
             rtt_milliseconds, jitter_milliseconds, timeout_count, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, timestamp.isoformat(), metrics.status.value, metrics.sent_packets, metrics.received_packets,
             metrics.packet_loss_percent, metrics.rtt_milliseconds, metrics.jitter_milliseconds,
             metrics.timeout_count, metrics.last_error),
        )
        self._connection.commit()
        return StoredMeasurement(cursor.lastrowid, session_id, timestamp, metrics)

    def list_sessions(self) -> list[MonitorSession]:
        """Return sessions with newest first."""
        rows = self._connection.execute("SELECT * FROM sessions ORDER BY started_at DESC").fetchall()
        return [self._session_from_row(row) for row in rows]

    def measurements_for_session(self, session_id: int) -> list[StoredMeasurement]:
        """Return all measurements in chronological order."""
        rows = self._connection.execute("SELECT * FROM measurements WHERE session_id = ? ORDER BY observed_at", (session_id,)).fetchall()
        return [self._measurement_from_row(row) for row in rows]

    def session_summary(self, session_id: int) -> SessionSummary:
        """Compute aggregate UDP quality statistics for one session in SQL."""
        session_row = self._connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if session_row is None:
            raise ValueError(f"Unknown session id: {session_id}")
        stats_row = self._connection.execute(
            """SELECT
                COUNT(*) AS sample_count,
                SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS success_count,
                AVG(rtt_milliseconds) AS average_rtt,
                AVG(jitter_milliseconds) AS average_jitter,
                AVG(packet_loss_percent) AS average_loss
            FROM measurements WHERE session_id = ?""",
            (MeasurementStatus.SUCCESS.value, session_id),
        ).fetchone()
        session = self._session_from_row(session_row)
        return SessionSummary(
            session_id=session.id,
            host=session.host,
            port=session.port,
            started_at=session.started_at,
            ended_at=session.ended_at,
            sample_count=stats_row["sample_count"] or 0,
            success_count=stats_row["success_count"] or 0,
            average_rtt_milliseconds=stats_row["average_rtt"],
            average_jitter_milliseconds=stats_row["average_jitter"],
            average_loss_percent=stats_row["average_loss"],
        )

    def record_event(self, session_id: int, category: EventCategory, description: str, occurred_at: datetime | None = None) -> MonitoringEvent:
        """Persist one manually-logged timeline entry for a session."""
        timestamp = occurred_at or datetime.now(UTC)
        cursor = self._connection.execute(
            "INSERT INTO events (session_id, occurred_at, category, description) VALUES (?, ?, ?, ?)",
            (session_id, timestamp.isoformat(), category.value, description),
        )
        self._connection.commit()
        return MonitoringEvent(cursor.lastrowid, session_id, timestamp, category, description)

    def events_for_session(self, session_id: int) -> list[MonitoringEvent]:
        """Return a session's logged events in chronological order."""
        rows = self._connection.execute("SELECT * FROM events WHERE session_id = ? ORDER BY occurred_at", (session_id,)).fetchall()
        return [self._event_from_row(row) for row in rows]

    def export_csv(self, session_id: int, destination: Path) -> int:
        """Export a session as UTF-8 CSV and return the exported row count."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        measurements = self.measurements_for_session(session_id)
        with destination.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=["observed_at", "status", "sent_packets", "received_packets", "packet_loss_percent", "rtt_milliseconds", "jitter_milliseconds", "timeout_count", "last_error"])
            writer.writeheader()
            for item in measurements:
                writer.writerow({"observed_at": item.observed_at.isoformat(), "status": item.metrics.status.value, "sent_packets": item.metrics.sent_packets, "received_packets": item.metrics.received_packets, "packet_loss_percent": item.metrics.packet_loss_percent, "rtt_milliseconds": item.metrics.rtt_milliseconds, "jitter_milliseconds": item.metrics.jitter_milliseconds, "timeout_count": item.metrics.timeout_count, "last_error": item.metrics.last_error})
        return len(measurements)

    def _initialize(self) -> None:
        """Create the schema once and record its version."""
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT, host TEXT NOT NULL, port INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS measurements (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id), observed_at TEXT NOT NULL, status TEXT NOT NULL, sent_packets INTEGER NOT NULL, received_packets INTEGER NOT NULL, packet_loss_percent REAL, rtt_milliseconds REAL, jitter_milliseconds REAL, timeout_count INTEGER NOT NULL, last_error TEXT);
            CREATE INDEX IF NOT EXISTS idx_measurements_session_observed ON measurements(session_id, observed_at);
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id), occurred_at TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_events_session_occurred ON events(session_id, occurred_at);
            PRAGMA user_version = 2;
        """)
        self._connection.commit()

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> MonitorSession:
        return MonitorSession(row["id"], datetime.fromisoformat(row["started_at"]), datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None, row["host"], row["port"])

    @staticmethod
    def _measurement_from_row(row: sqlite3.Row) -> StoredMeasurement:
        metrics = NetworkMetrics(MeasurementStatus(row["status"]), row["sent_packets"], row["received_packets"], row["packet_loss_percent"], row["rtt_milliseconds"], row["jitter_milliseconds"], row["timeout_count"], row["last_error"])
        return StoredMeasurement(row["id"], row["session_id"], datetime.fromisoformat(row["observed_at"]), metrics)

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> MonitoringEvent:
        return MonitoringEvent(row["id"], row["session_id"], datetime.fromisoformat(row["occurred_at"]), EventCategory(row["category"]), row["description"])
