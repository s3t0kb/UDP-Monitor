"""Qt-safe bridge between a heartbeat worker and application UI."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from udpmonitor.config import AppSettings
from udpmonitor.models import NetworkMetrics
from udpmonitor.network import HeartbeatMonitor, IcmpPingProbe, Probe, TcpConnectProbe, UdpEchoProbe

POLL_INTERVAL_MILLISECONDS = 100

# Maps AppSettings.probe_type to a factory building the matching Probe.
# ICMP ping only needs a host, so it ignores the configured ports.
_PROBE_FACTORIES: dict[str, Callable[[AppSettings], Probe]] = {
    "udp_echo": lambda settings: UdpEchoProbe(settings.udp_host, settings.udp_port),
    "tcp_connect": lambda settings: TcpConnectProbe(settings.udp_host, settings.tcp_port),
    "icmp_ping": lambda settings: IcmpPingProbe(settings.udp_host),
}


class MonitorService(QObject):
    """Own monitor lifetime and deliver worker results on Qt's main thread."""

    metrics_updated = Signal(object)
    running_changed = Signal(bool)

    def __init__(self, settings: AppSettings) -> None:
        """Create an inactive service using the current connection settings."""
        super().__init__()
        self._settings = settings
        self._monitor: HeartbeatMonitor | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MILLISECONDS)
        self._timer.timeout.connect(self._drain_updates)

    @property
    def is_running(self) -> bool:
        """Return whether the heartbeat worker is currently active."""
        return self._monitor is not None and self._monitor.is_running

    def start(self) -> None:
        """Start a monitor using the probe strategy chosen in settings."""
        if self.is_running:
            return
        factory = _PROBE_FACTORIES.get(self._settings.probe_type, _PROBE_FACTORIES["udp_echo"])
        probe = factory(self._settings)
        self._monitor = HeartbeatMonitor(
            probe=probe,
            interval_seconds=self._settings.heartbeat_interval_seconds,
            timeout_seconds=self._settings.timeout_seconds,
        )
        self._monitor.start()
        self._timer.start()
        self.running_changed.emit(True)

    def stop(self) -> None:
        """Stop active collection and UI polling."""
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
