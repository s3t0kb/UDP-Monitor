"""Main window and presentation-level navigation."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget

from udpmonitor.config import AppSettings
from udpmonitor.constants import PROBE_TYPES
from udpmonitor.database import SessionRepository
from udpmonitor.models import NetworkMetrics
from udpmonitor.network.heartbeat import MIN_INTERVAL_SECONDS
from udpmonitor.translations.translator import Translator
from udpmonitor.ui.events_page import EventsPage
from udpmonitor.ui.metrics_chart import MetricsChart
from udpmonitor.ui.sessions_page import SessionsPage


class MetricCard(QFrame):
    """Reusable placeholder for a future measured network metric."""

    def __init__(self, title: str, value: str, translator: Translator) -> None:
        """Create a localized metric card."""
        super().__init__()
        self.setObjectName("card")
        self._title_key, self._translator = title, translator
        self._title, self._value, self._detail = QLabel(), QLabel(value), QLabel()
        self._title.setObjectName("metricTitle")
        self._value.setObjectName("metricValue")
        self._detail.setObjectName("subtitle")
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addWidget(self._detail)
        self.retranslate()
        translator.subscribe(self.retranslate)

    def retranslate(self) -> None:
        """Refresh localized card text."""
        self._title.setText(self._translator.text(self._title_key))
        self._detail.setText(self._translator.text("waiting"))

    def set_value(self, value: str) -> None:
        """Update the displayed metric value without exposing internals."""
        self._value.setText(value)


class InformationPage(QWidget):
    """Dashboard and temporary feature pages."""

    def __init__(self, key: str, translator: Translator, dashboard: bool = False, on_action: Callable[[], None] | None = None) -> None:
        """Build either the dashboard or a future-feature placeholder."""
        super().__init__()
        self._key, self._translator, self._dashboard = key, translator, dashboard
        self._running = False
        self._title, self._subtitle = QLabel(), QLabel()
        self._title.setObjectName("pageTitle")
        self._subtitle.setObjectName("subtitle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 30)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        if dashboard:
            grid = QGridLayout()
            self._cards: dict[str, MetricCard] = {}
            for index, args in enumerate((("health", "--"), ("rtt", "-- ms"), ("loss", "-- %"), ("jitter", "-- ms"))):
                card = MetricCard(*args, translator); self._cards[args[0]] = card
                grid.addWidget(card, index // 2, index % 2)
            layout.addLayout(grid)
            self._chart = MetricsChart()
            layout.addWidget(self._chart, 1)
        else:
            card = QFrame(); card.setObjectName("notice")
            card_layout = QVBoxLayout(card)
            self._future, self._future_body = QLabel(), QLabel()
            self._future_body.setObjectName("subtitle")
            card_layout.addWidget(self._future); card_layout.addWidget(self._future_body)
            layout.addWidget(card)
            if key == "monitor" and on_action is not None:
                self._action = QPushButton(self._translator.text("start")); self._action.clicked.connect(on_action)
                layout.addWidget(self._action)
        layout.addStretch()
        self.retranslate()
        translator.subscribe(self.retranslate)

    def update_metrics(self, metrics: NetworkMetrics) -> None:
        """Render a fresh measurement on the dashboard."""
        if not self._dashboard:
            return
        values = {"health": "--" if metrics.health_score is None else str(metrics.health_score), "rtt": "-- ms" if metrics.rtt_milliseconds is None else f"{metrics.rtt_milliseconds:.1f} ms", "loss": "-- %" if metrics.packet_loss_percent is None else f"{metrics.packet_loss_percent:.1f} %", "jitter": "-- ms" if metrics.jitter_milliseconds is None else f"{metrics.jitter_milliseconds:.1f} ms"}
        for key, value in values.items():
            self._cards[key].set_value(value)
        self._chart.append(metrics)

    def set_active(self, running: bool) -> None:
        """Reflect the monitor's running state on the start/stop button."""
        self._running = running
        if not self._dashboard and self._key == "monitor":
            self._action.setText(self._translator.text("stop" if running else "start"))

    def retranslate(self) -> None:
        """Refresh localized page labels."""
        self._title.setText(self._translator.text(self._key))
        self._subtitle.setText(self._translator.text("overview") if self._dashboard else "")
        if not self._dashboard:
            self._future.setText(self._translator.text("future"))
            self._future_body.setText(self._translator.text("future_body"))
            if self._key == "monitor":
                self._action.setText(self._translator.text("stop" if self._running else "start"))


class SettingsPage(QWidget):
    """Presentation and connection settings owned by the settings service."""

    def __init__(self, settings: AppSettings, translator: Translator, save: Callable[[], None], repository: SessionRepository) -> None:
        """Build settings controls bound to an AppSettings object."""
        super().__init__()
        self._settings, self._translator, self._save = settings, translator, save
        self._title = QLabel(); self._title.setObjectName("pageTitle")

        self._language_label = QLabel(); self._language = QComboBox()
        self._restore = QCheckBox()
        self._probe_label = QLabel(); self._probe_type = QComboBox()
        general_card = QFrame(); general_card.setObjectName("card")
        general_layout = QVBoxLayout(general_card)
        for widget in (self._language_label, self._language, self._restore, self._probe_label, self._probe_type):
            general_layout.addWidget(widget)

        self._connection_label = QLabel(); self._connection_label.setObjectName("pageTitle")
        self._host_label = QLabel(); self._host = QLineEdit()
        self._udp_port_label = QLabel(); self._udp_port = QSpinBox(); self._udp_port.setRange(1, 65535)
        self._tcp_port_label = QLabel(); self._tcp_port = QSpinBox(); self._tcp_port.setRange(1, 65535)
        self._interval_label = QLabel(); self._interval = QDoubleSpinBox(); self._interval.setRange(MIN_INTERVAL_SECONDS, 60.0); self._interval.setSingleStep(0.1); self._interval.setDecimals(1)
        self._timeout_label = QLabel(); self._timeout = QDoubleSpinBox(); self._timeout.setRange(0.1, 60.0); self._timeout.setSingleStep(0.1); self._timeout.setDecimals(1)
        connection_card = QFrame(); connection_card.setObjectName("card")
        connection_layout = QVBoxLayout(connection_card)
        for widget in (self._host_label, self._host, self._udp_port_label, self._udp_port, self._tcp_port_label, self._tcp_port, self._interval_label, self._interval, self._timeout_label, self._timeout):
            connection_layout.addWidget(widget)

        layout = QVBoxLayout(self); layout.setContentsMargins(30, 28, 30, 30)
        layout.addWidget(self._title)
        layout.addWidget(general_card)
        layout.addWidget(self._connection_label)
        layout.addWidget(connection_card)
        layout.addStretch()

        self._language.currentIndexChanged.connect(self._change_language)
        self._restore.toggled.connect(self._change_restore)
        self._probe_type.currentIndexChanged.connect(self._change_probe_type)
        self._host.editingFinished.connect(self._change_host)
        self._udp_port.editingFinished.connect(self._change_udp_port)
        self._tcp_port.editingFinished.connect(self._change_tcp_port)
        self._interval.editingFinished.connect(self._change_interval)
        self._timeout.editingFinished.connect(self._change_timeout)

        self.retranslate(); translator.subscribe(self.retranslate)

    def retranslate(self) -> None:
        """Refresh controls without triggering persistence changes."""
        self._language.blockSignals(True); self._language.clear()
        self._language.addItem(self._translator.text("ja_name"), "ja"); self._language.addItem(self._translator.text("en_name"), "en")
        self._language.setCurrentIndex(self._language.findData(self._translator.language)); self._language.blockSignals(False)
        self._restore.blockSignals(True); self._restore.setChecked(self._settings.restore_last_page); self._restore.blockSignals(False)
        self._probe_type.blockSignals(True); self._probe_type.clear()
        for probe_type in PROBE_TYPES:
            self._probe_type.addItem(self._translator.text(f"probe_{probe_type}"), probe_type)
        self._probe_type.setCurrentIndex(self._probe_type.findData(self._settings.probe_type)); self._probe_type.blockSignals(False)

        self._host.blockSignals(True); self._host.setText(self._settings.udp_host); self._host.blockSignals(False)
        self._udp_port.blockSignals(True); self._udp_port.setValue(self._settings.udp_port); self._udp_port.blockSignals(False)
        self._tcp_port.blockSignals(True); self._tcp_port.setValue(self._settings.tcp_port); self._tcp_port.blockSignals(False)
        self._interval.blockSignals(True); self._interval.setValue(self._settings.heartbeat_interval_seconds); self._interval.blockSignals(False)
        self._timeout.blockSignals(True); self._timeout.setValue(self._settings.timeout_seconds); self._timeout.blockSignals(False)

        self._title.setText(self._translator.text("settings"))
        self._language_label.setText(self._translator.text("language")); self._restore.setText(self._translator.text("restore")); self._probe_label.setText(self._translator.text("probe_type"))
        self._connection_label.setText(self._translator.text("connection_settings"))
        self._host_label.setText(self._translator.text("host")); self._udp_port_label.setText(self._translator.text("udp_port")); self._tcp_port_label.setText(self._translator.text("tcp_port"))
        self._interval_label.setText(self._translator.text("interval_seconds")); self._timeout_label.setText(self._translator.text("timeout_seconds"))

    def _change_language(self) -> None:
        """Persist a user-selected language."""
        self._settings.language = str(self._language.currentData()); self._save(); self._translator.set_language(self._settings.language)

    def _change_restore(self, checked: bool) -> None:
        """Persist last-page restoration preference."""
        self._settings.restore_last_page = checked; self._save()

    def _change_probe_type(self) -> None:
        """Persist a user-selected probe strategy."""
        self._settings.probe_type = str(self._probe_type.currentData()); self._save()

    def _change_host(self) -> None:
        """Persist an edited target host, ignoring blank input."""
        host = self._host.text().strip()
        if host:
            self._settings.udp_host = host; self._save()
        else:
            self._host.setText(self._settings.udp_host)

    def _change_udp_port(self) -> None:
        """Persist the UDP Echo target port."""
        self._settings.udp_port = self._udp_port.value(); self._save()

    def _change_tcp_port(self) -> None:
        """Persist the TCP connect-probe target port."""
        self._settings.tcp_port = self._tcp_port.value(); self._save()

    def _change_interval(self) -> None:
        """Persist the measurement interval."""
        self._settings.heartbeat_interval_seconds = self._interval.value(); self._save()

    def _change_timeout(self) -> None:
        """Persist the per-measurement timeout."""
        self._settings.timeout_seconds = self._timeout.value(); self._save()


class MainWindow(QMainWindow):
    """Main shell with persistent page navigation."""

    _pages = ("dashboard", "monitor", "events", "sessions", "settings")
    monitor_toggled = Signal()

    def __init__(self, settings: AppSettings, translator: Translator, save: Callable[[], None], repository: SessionRepository) -> None:
        """Create the application shell."""
        super().__init__()
        self._settings, self._translator, self._save = settings, translator, save
        self._buttons: dict[str, QPushButton] = {}
        self.setMinimumSize(960, 620); self.resize(1180, 740)

        self._stack = QStackedWidget()
        self._dashboard = InformationPage("dashboard", translator, True)
        self._monitor_page = InformationPage("monitor", translator, on_action=self.monitor_toggled.emit)
        self._events = EventsPage(repository, translator)
        self._sessions = SessionsPage(repository, translator)
        for page in (self._dashboard, self._monitor_page, self._events, self._sessions, SettingsPage(settings, translator, save, repository)):
            self._stack.addWidget(page)

        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(214)
        side = QVBoxLayout(sidebar); side.addWidget(self._label("appTitle", "app")); side.addSpacing(28)
        group = QButtonGroup(self); group.setExclusive(True)
        for name in self._pages:
            button = QPushButton(); button.setObjectName("navigationButton"); button.setCheckable(True); button.clicked.connect(partial(self.open_page, name)); group.addButton(button); side.addWidget(button); self._buttons[name] = button
        side.addStretch()

        central = QWidget()
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(sidebar); root.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        translator.subscribe(self.retranslate); self.retranslate()
        self.open_page(settings.last_page if settings.restore_last_page and settings.last_page in self._pages else "dashboard")

    def _label(self, object_name: str, key: str) -> QLabel:
        """Create a styled label."""
        label = QLabel(self._translator.text(key)); label.setObjectName(object_name); return label

    def open_page(self, name: str) -> None:
        """Open and retain the named page."""
        self._stack.setCurrentIndex(self._pages.index(name)); self._buttons[name].setChecked(True); self._settings.last_page = name; self._save()
        if name == "sessions":
            self._sessions.refresh()
        elif name == "events":
            self._events.reload_sessions()

    def retranslate(self) -> None:
        """Refresh navigation labels."""
        self.setWindowTitle(self._translator.text("app"))
        for name, button in self._buttons.items(): button.setText(self._translator.text(name))

    def update_metrics(self, metrics: NetworkMetrics) -> None:
        """Forward latest metrics to the dashboard."""
        self._dashboard.update_metrics(metrics)

    def set_monitoring_active(self, running: bool) -> None:
        """Forward the monitor's running state to the monitor page's button."""
        self._monitor_page.set_active(running)

    def set_active_session(self, session_id: int | None) -> None:
        """Forward the active session id so the events page can log against it."""
        self._events.set_active_session(session_id)
