"""Application-wide constants."""

from pathlib import Path

APPLICATION_NAME = "UDP Monitor"
DEFAULT_LANGUAGE = "ja"


def application_data_directory() -> Path:
    """Return the per-user directory for settings and logs."""
    return Path.home() / "AppData" / "Local" / APPLICATION_NAME
