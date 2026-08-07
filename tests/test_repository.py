"""Tests for SQLite session persistence and CSV export."""

from datetime import UTC, datetime

import pytest

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


def test_session_summary_aggregates_measurements(tmp_path) -> None:
    """Summary statistics must average successes and count timeouts correctly."""
    repository = SessionRepository(tmp_path / "monitor.sqlite3")
    session = repository.start_session("127.0.0.1", 7, datetime(2026, 1, 1, tzinfo=UTC))
    repository.record_measurement(session.id, NetworkMetrics(MeasurementStatus.SUCCESS, 1, 1, 0.0, 10.0, None, 0), datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC))
    repository.record_measurement(session.id, NetworkMetrics(MeasurementStatus.SUCCESS, 2, 2, 0.0, 20.0, 5.0, 0), datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC))
    repository.record_measurement(session.id, NetworkMetrics(MeasurementStatus.TIMEOUT, 3, 2, 33.3, None, 5.0, 1), datetime(2026, 1, 1, 0, 0, 3, tzinfo=UTC))
    repository.end_session(session.id, datetime(2026, 1, 1, 0, 1, 3, tzinfo=UTC))

    summary = repository.session_summary(session.id)

    assert summary.sample_count == 3
    assert summary.success_count == 2
    assert summary.success_rate_percent == pytest.approx(2 / 3 * 100)
    assert summary.average_rtt_milliseconds == pytest.approx(15.0)
    assert summary.duration_text == "1m 3s"
    repository.close()
