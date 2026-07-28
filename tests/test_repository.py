"""Tests for SQLite session persistence and CSV export."""

from datetime import UTC, datetime

from udpmonitor.database import SessionRepository
from udpmonitor.models import MeasurementStatus, NetworkMetrics


def test_session_measurement_and_csv_export(tmp_path) -> None:
    """A measurement must round-trip from SQLite and export as CSV."""
    repository = SessionRepository(tmp_path / "monitor.sqlite3")
    session = repository.start_session("127.0.0.1", 7, datetime(2026, 1, 1, tzinfo=UTC))
    metrics = NetworkMetrics(MeasurementStatus.SUCCESS, 1, 1, 0.0, 12.5, 1.2, 0)
    repository.record_measurement(session.id, metrics, datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC))
    repository.end_session(session.id, datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC))

    restored = repository.measurements_for_session(session.id)
    output = tmp_path / "session.csv"

    assert restored[0].metrics == metrics
    assert repository.export_csv(session.id, output) == 1
    assert "rtt_milliseconds" in output.read_text(encoding="utf-8-sig")
    repository.close()
