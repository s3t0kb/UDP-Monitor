"""Live PyQtGraph visualisation for UDP measurements."""

from __future__ import annotations

from collections import deque
import time

import pyqtgraph as pg
from PySide6.QtWidgets import QFrame, QVBoxLayout

from udpmonitor.models import NetworkMetrics

MAX_HISTORY_SAMPLES = 300
PLOT_BACKGROUND = "#1A222B"
GRID_ALPHA = 0.2
RTT_COLOR = "#53E6FF"
JITTER_COLOR = "#42E8AF"
LOSS_COLOR = "#FFAA42"


class MetricsChart(QFrame):
    """Render bounded live histories for RTT, jitter, and packet loss."""

    def __init__(self, max_samples: int = MAX_HISTORY_SAMPLES) -> None:
        """Create an empty chart with a bounded memory footprint."""
        super().__init__()
        if max_samples <= 0:
            raise ValueError("max_samples must be positive")
        self.setObjectName("card")
        self._started_at: float | None = None
        self._timestamps: deque[float] = deque(maxlen=max_samples)
        self._rtts: deque[float] = deque(maxlen=max_samples)
        self._jitters: deque[float] = deque(maxlen=max_samples)
        self._losses: deque[float] = deque(maxlen=max_samples)
        self._plot = pg.PlotWidget(background=PLOT_BACKGROUND)
        self._plot.setMenuEnabled(False)
        self._plot.showGrid(x=True, y=True, alpha=GRID_ALPHA)
        self._plot.setLabel("left", "Milliseconds / Percent")
        self._plot.setLabel("bottom", "Elapsed", units="s")
        self._plot.addLegend(offset=(10, 10))
        self._rtt_curve = self._plot.plot(name="RTT", pen=pg.mkPen(RTT_COLOR, width=2))
        self._jitter_curve = self._plot.plot(name="Jitter", pen=pg.mkPen(JITTER_COLOR, width=2))
        self._loss_curve = self._plot.plot(name="Loss", pen=pg.mkPen(LOSS_COLOR, width=2))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._plot)

    def append(self, metrics: NetworkMetrics) -> None:
        """Add one monitor update and redraw the series efficiently."""
        now = time.monotonic()
        if self._started_at is None:
            self._started_at = now
        self._timestamps.append(now - self._started_at)
        self._rtts.append(metrics.rtt_milliseconds or 0.0)
        self._jitters.append(metrics.jitter_milliseconds or 0.0)
        self._losses.append(metrics.packet_loss_percent or 0.0)
        timestamps = list(self._timestamps)
        self._rtt_curve.setData(timestamps, list(self._rtts))
        self._jitter_curve.setData(timestamps, list(self._jitters))
        self._loss_curve.setData(timestamps, list(self._losses))

    def clear(self) -> None:
        """Clear the visible history and reset elapsed time."""
        self._started_at = None
        for series in (self._timestamps, self._rtts, self._jitters, self._losses):
            series.clear()
        self._rtt_curve.clear()
        self._jitter_curve.clear()
        self._loss_curve.clear()
