"""Theme helpers."""

from pathlib import Path


def load_dark_theme() -> str:
    """Load the bundled dark Qt Style Sheet."""
    return (Path(__file__).parent / "dark.qss").read_text(encoding="utf-8")
