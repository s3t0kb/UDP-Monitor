"""Qt-safe bridge between the UDP worker and application UI."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from udpmonitor.config import AppSettings
from udpmonitor.models import NetworkMetrics
from udpmonitor.network import UdpHeartbeatMonitor

POLL_INTERVAL_MILLISECONDS = 100


class MonitorService(QObject):
    """Own monitor lifetime and deliver worker results on Qt's main thread."""

    metrics_updated = Signal(object)
    running_changed = Signal(bool)

    def __init__(self, settings: AppSettings) -> None:
        """Create an inactive service using the current connection settings."""
        super().__init__()
        self._settings = settings
        self._monitor: UdpHeartbeatMonitor | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MILLISECONDS)
        self._timer.timeout.connect(self._drain_updates)

    @property
    def is_running(self) -> bool:
        """Return whether the UDP worker is currently active."""
        return self._monitor is not None and self._monitor.is_running

    def start(self) -> None:
        """Start a monitor created from the current persisted settings."""
        if self.is_running:
            return
        self._monitor = UdpHeartbeatMonitor(
            host=self._settings.udp_host,
            port=self._settings.udp_port,
            interval_seconds=self._settings.heartbeat_interval_seconds,
            timeout_seconds=self._settings.timeout_seconds,
        )
        self._monitor.start()
        self._timer.start()
        self.running_changed.emit(True)

    def stop(self) -> None:
        """Stop active UDP collection and UI polling."""
        if self._monitor is None:
            return
        self._monitor.stop()
        self._drain_updates()
        self._timer.stop()
        self._monitor = None
        self.running_changed.emit(False)

    def toggle(self) -> None:
        """Start or stop monitoring based on the current state."""
        if self.is_running:
            self.stop()
        else:
            self.start()

    def _drain_updates(self) -> None:
        """Emit all worker updates from the Qt event-loop thread."""
        if self._monitor is None:
            return
        for metrics in self._monitor.drain_updates():
            self.metrics_updated.emit(metrics)
