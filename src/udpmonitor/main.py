"""Executable entry point and logging setup."""

import logging
from logging.handlers import RotatingFileHandler
import sys

from PySide6.QtWidgets import QApplication

from udpmonitor.app import UdpMonitorApplication
from udpmonitor.constants import APPLICATION_NAME, application_data_directory


def configure_logging() -> None:
    """Configure bounded file and console logging."""
    directory = application_data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[RotatingFileHandler(directory / "udp-monitor.log", encoding="utf-8", maxBytes=1_000_000, backupCount=3), logging.StreamHandler()])


def main() -> None:
    """Run UDP Monitor."""
    configure_logging()
    application = QApplication(sys.argv)
    application.setApplicationName(APPLICATION_NAME)
    sys.exit(UdpMonitorApplication(application).run())
