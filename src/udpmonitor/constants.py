"""Application-wide constants."""

from pathlib import Path

APPLICATION_NAME = "UDP Monitor"
DEFAULT_LANGUAGE = "ja"

# Keys must match udpmonitor.services.monitor_service._PROBE_FACTORIES.
PROBE_TYPES = ("udp_echo", "tcp_connect", "icmp_ping")
DEFAULT_PROBE_TYPE = "udp_echo"


def application_data_directory() -> Path:
    """Return the per-user directory for settings and logs."""
    return Path.home() / "AppData" / "Local" / APPLICATION_NAME
