"""Tests for bounded live-chart history."""

from udpmonitor.models import NetworkMetrics
from udpmonitor.ui.metrics_chart import MetricsChart


def test_chart_keeps_a_bounded_history(qtbot: object) -> None:
    """Rendering many updates must retain only the configured sample count."""
    chart = MetricsChart(max_samples=2)
    qtbot.addWidget(chart)
    for value in range(3):
        chart.append(NetworkMetrics(rtt_milliseconds=float(value)))

    assert len(chart._timestamps) == 2
