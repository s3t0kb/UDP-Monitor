"""Backward-compatible UDP-Echo-only heartbeat monitor.

Kept so existing callers and tests do not need to change. New code
should build whichever Probe fits the target (see
udpmonitor.network.probes) and drive it with HeartbeatMonitor directly,
since the measurement strategy is no longer tied to this class name.
"""

from __future__ import annotations

from udpmonitor.network.heartbeat import HeartbeatMonitor
from udpmonitor.network.probes import UdpEchoProbe


class UdpHeartbeatMonitor(HeartbeatMonitor):
    """Convenience constructor preserving the original UDP-Echo-only API."""

    def __init__(
        self,
        host: str,
        port: int,
        interval_seconds: float = 1.0,
        timeout_seconds: float = 2.0,
        window_size: int = 60,
    ) -> None:
        """Configure a monitor that measures RTT via UDP Echo."""
        super().__init__(UdpEchoProbe(host, port), interval_seconds, timeout_seconds, window_size)
