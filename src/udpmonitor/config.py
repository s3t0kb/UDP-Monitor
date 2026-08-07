"""Persistent JSON settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Any

import orjson

from udpmonitor.constants import DEFAULT_LANGUAGE, DEFAULT_PROBE_TYPE, PROBE_TYPES, application_data_directory

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AppSettings:
    """User preferences independent from the UI."""

    language: str = DEFAULT_LANGUAGE
    restore_last_page: bool = True
    last_page: str = "dashboard"
    udp_host: str = "127.0.0.1"
    udp_port: int = 7
    tcp_port: int = 443
    probe_type: str = DEFAULT_PROBE_TYPE
    heartbeat_interval_seconds: float = 1.0
    timeout_seconds: float = 2.0


class SettingsStore:
    """Load and atomically persist application settings."""

    def __init__(self, data_directory: Path | None = None) -> None:
        """Create a store, optionally with a test-specific directory."""
        self._directory = data_directory or application_data_directory()
        self._path = self._directory / "settings.json"

    def load(self) -> AppSettings:
        """Load saved settings or return safe defaults."""
        if not self._path.exists():
            return AppSettings()
        try:
            data: Any = orjson.loads(self._path.read_bytes())
            if not isinstance(data, dict):
                raise ValueError("Settings must be a JSON object.")
            known = set(AppSettings.__dataclass_fields__)
            settings = AppSettings(**{key: value for key, value in data.items() if key in known})
            if settings.probe_type not in PROBE_TYPES:
                LOGGER.warning("Unknown probe_type %r in settings; using default.", settings.probe_type)
                settings.probe_type = DEFAULT_PROBE_TYPE
            return settings
        except (OSError, ValueError, TypeError, orjson.JSONDecodeError) as error:
            LOGGER.warning("Unable to load settings: %s", error)
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        """Atomically save the supplied settings."""
        self._directory.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        try:
            temporary.write_bytes(orjson.dumps(asdict(settings), option=orjson.OPT_INDENT_2))
            temporary.replace(self._path)
        except OSError as error:
            LOGGER.error("Unable to save settings: %s", error)
            temporary.unlink(missing_ok=True)
