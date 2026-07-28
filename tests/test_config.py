"""Tests for settings persistence."""

from pathlib import Path

from udpmonitor.config import AppSettings, SettingsStore


def test_settings_round_trip(tmp_path: Path) -> None:
    """Settings should persist without loss."""
    store = SettingsStore(tmp_path)
    expected = AppSettings(language="en", restore_last_page=False, last_page="sessions")
    store.save(expected)
    assert store.load() == expected
