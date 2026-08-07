"""Application composition root."""

from PySide6.QtWidgets import QApplication

from udpmonitor.config import SettingsStore
from udpmonitor.constants import application_data_directory
from udpmonitor.database import DATABASE_FILE_NAME, SessionRepository
from udpmonitor.models import NetworkMetrics
from udpmonitor.themes import load_dark_theme
from udpmonitor.services import MonitorService
from udpmonitor.translations.translator import Translator
from udpmonitor.ui.main_window import MainWindow


class UdpMonitorApplication:
    """Compose UI and infrastructure services."""

    def __init__(self, qt_application: QApplication) -> None:
        """Initialize services for an existing Qt application."""
        self._store = SettingsStore()
        self._settings = self._store.load()
        self._repository = SessionRepository(application_data_directory() / DATABASE_FILE_NAME)
        self._active_session_id: int | None = None
        self._translator = Translator(self._settings.language)
        qt_application.setStyleSheet(load_dark_theme())
        self.window = MainWindow(self._settings, self._translator, self.save_settings, self._repository)
        self.monitor_service = MonitorService(self._settings)
        self.monitor_service.metrics_updated.connect(self.window.update_metrics)
        self.monitor_service.metrics_updated.connect(self._record_metrics)
        self.monitor_service.running_changed.connect(self._update_session)
        self.monitor_service.running_changed.connect(self.window.set_monitoring_active)
        self.window.monitor_toggled.connect(self.monitor_service.toggle)
        qt_application.aboutToQuit.connect(self.shutdown)

    def save_settings(self) -> None:
        """Persist the current settings."""
        self._store.save(self._settings)

    def _update_session(self, running: bool) -> None:
        """Open or close persistent storage with the monitor lifecycle."""
        if running:
            session = self._repository.start_session(self._settings.udp_host, self._settings.udp_port)
            self._active_session_id = session.id
        elif self._active_session_id is not None:
            self._repository.end_session(self._active_session_id)
            self._active_session_id = None
        self.window.set_active_session(self._active_session_id)

    def _record_metrics(self, metrics: NetworkMetrics) -> None:
        """Persist each UI-delivered measurement in the active session."""
        if self._active_session_id is not None:
            self._repository.record_measurement(self._active_session_id, metrics)

    def run(self) -> int:
        """Show the window and enter Qt's event loop."""
        self.window.show()
        return QApplication.instance().exec()

    def shutdown(self) -> None:
        """Stop the UDP worker and close the database before the app exits."""
        if self.monitor_service.is_running:
            self.monitor_service.stop()
        self._repository.close()
