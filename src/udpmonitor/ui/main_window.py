"""Main window and presentation-level navigation."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QMainWindow

from udpmonitor.config import AppSettings
from udpmonitor.database import SessionRepository
from udpmonitor.models import NetworkMetrics
from udpmonitor.translations.translator import Translator
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


class InformationPage(QMainWindow):
    """Dashboard and temporary feature pages."""

    def __init__(self, key: str, translator: Translator, dashboard: bool = False, on_action: Callable[[], None] | None = None) -> None:
        """Build either the dashboard or a future-feature placeholder."""
        super().__init__()
        self._key, self._translator, self._dashboard = key, translator, dashboard
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
        for key, value in values.items(): self._cards[key]._value.setText(value)
        self._chart.append(metrics)

    def retranslate(self) -> None:
        """Refresh localized page labels."""
        self._title.setText(self._translator.text(self._key))
        self._subtitle.setText(self._translator.text("overview") if self._dashboard else "")
        if not self._dashboard:
            self._future.setText(self._translator.text("future"))
            self._future_body.setText(self._translator.text("future_body"))


class SettingsPage(QMainWindow):
    """Presentation settings owned by the settings service."""

    def __init__(self, settings: AppSettings, translator: Translator, save: Callable[[], None], repository: SessionRepository) -> None:
        """Build settings controls bound to an AppSettings object."""
        super().__init__()
        self._settings, self._translator, self._save = settings, translator, save
        self._title, self._language_label = QLabel(), QLabel()
        self._title.setObjectName("pageTitle")
        self._language = QComboBox(); self._restore = QCheckBox()
        card = QFrame(); card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(self._language_label); card_layout.addWidget(self._language); card_layout.addWidget(self._restore)
        layout = QVBoxLayout(self); layout.setContentsMargins(30, 28, 30, 30)
        layout.addWidget(self._title); layout.addWidget(card); layout.addStretch()
        self._language.currentIndexChanged.connect(self._change_language)
        self._restore.toggled.connect(self._change_restore)
        self.retranslate(); translator.subscribe(self.retranslate)

    def retranslate(self) -> None:
        """Refresh controls without triggering persistence changes."""
        self._language.blockSignals(True); self._language.clear()
        self._language.addItem(self._translator.text("ja_name"), "ja"); self._language.addItem(self._translator.text("en_name"), "en")
        self._language.setCurrentIndex(self._language.findData(self._translator.language)); self._language.blockSignals(False)
        self._restore.blockSignals(True); self._restore.setChecked(self._settings.restore_last_page); self._restore.blockSignals(False)
        self._title.setText(self._translator.text("settings")); self._language_label.setText(self._translator.text("language")); self._restore.setText(self._translator.text("restore"))

    def _change_language(self) -> None:
        """Persist a user-selected language."""
        self._settings.language = str(self._language.currentData()); self._save(); self._translator.set_language(self._settings.language)

    def _change_restore(self, checked: bool) -> None:
        """Persist last-page restoration preference."""
        self._settings.restore_last_page = checked; self._save()


class MainWindow(QMainWindow):
    """Main shell with persistent page navigation."""

    _pages = ("dashboard", "monitor", "sessions", "settings")
    monitor_toggled = Signal()

    def __init__(self, settings: AppSettings, translator: Translator, save: Callable[[], None], repository: SessionRepository) -> None:
        """Create the application shell."""
        super().__init__(); self._settings, self._translator, self._save = settings, translator, save; self._buttons: dict[str, QPushButton] = {}
        self.setMinimumSize(960, 620); self.resize(1180, 740)
        self._stack = QStackedWidget(); self._dashboard = InformationPage("dashboard", translator, True); self._sessions = SessionsPage(repository, translator); self._stack.addWidget(self._dashboard); self._stack.addWidget(InformationPage("monitor", translator, on_action=self.monitor_toggled.emit)); self._stack.addWidget(self._sessions); self._stack.addWidget(SettingsPage(settings, translator, save, repository))
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(214)
        side = QVBoxLayout(sidebar); side.addWidget(self._label("appTitle", "app")); side.addSpacing(28)
        group = QButtonGroup(self); group.setExclusive(True)
        for name in self._pages:
            button = QPushButton(); button.setObjectName("navigationButton"); button.setCheckable(True); button.clicked.connect(partial(self.open_page, name)); group.addButton(button); side.addWidget(button); self._buttons[name] = button
        side.addStretch(); root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.addWidget(sidebar); root.addWidget(self._stack, 1)
        translator.subscribe(self.retranslate); self.retranslate(); self.open_page(settings.last_page if settings.restore_last_page and settings.last_page in self._pages else "dashboard")

    def _label(self, object_name: str, key: str) -> QLabel:
        """Create a styled label."""
        label = QLabel(self._translator.text(key)); label.setObjectName(object_name); return label

    def open_page(self, name: str) -> None:
        """Open and retain the named page."""
        self._stack.setCurrentIndex(self._pages.index(name)); self._buttons[name].setChecked(True); self._settings.last_page = name; self._save()
        if name == "sessions":
            self._sessions.refresh()

    def retranslate(self) -> None:
        """Refresh navigation labels."""
        self.setWindowTitle(self._translator.text("app"))
        for name, button in self._buttons.items(): button.setText(self._translator.text(name))

    def update_metrics(self, metrics: NetworkMetrics) -> None:
        """Forward latest metrics to the dashboard."""
        self._dashboard.update_metrics(metrics)
