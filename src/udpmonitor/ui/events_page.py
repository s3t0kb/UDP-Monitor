"""Manual event log and per-session timeline.

Automatic detection of Discord/VRChat disconnect events is not
implemented yet. Users tag a manually-logged event as Discord- or
VRChat-related themselves; the category is stored so a future automatic
detector can write the same kind of row without changing this page.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from udpmonitor.database import SessionRepository
from udpmonitor.models import EventCategory
from udpmonitor.translations.translator import Translator

_CATEGORIES = (EventCategory.MANUAL, EventCategory.DISCORD, EventCategory.VRCHAT)


class EventsPage(QWidget):
    """Log events during a live session and browse any session's timeline."""

    def __init__(self, repository: SessionRepository, translator: Translator) -> None:
        """Build the event log and timeline controls."""
        super().__init__()
        self._repository, self._translator = repository, translator
        self._active_session_id: int | None = None

        self._title, self._hint = QLabel(), QLabel()
        self._title.setObjectName("pageTitle"); self._hint.setObjectName("subtitle")

        self._session_selector = QComboBox()
        self._session_selector.currentIndexChanged.connect(self._refresh_timeline)

        self._category = QComboBox()
        self._description = QLineEdit()
        self._record = QPushButton()
        self._record.clicked.connect(self._record_event)

        self._timeline = QTableWidget(0, 3)
        self._timeline.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        form = QHBoxLayout()
        form.addWidget(self._category)
        form.addWidget(self._description, 1)
        form.addWidget(self._record)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 30)
        layout.addWidget(self._title)
        layout.addWidget(self._hint)
        layout.addWidget(self._session_selector)
        layout.addLayout(form)
        layout.addWidget(self._timeline)

        self.retranslate(); translator.subscribe(self.retranslate)
        self.reload_sessions()

    def retranslate(self) -> None:
        """Refresh localized labels, including the category dropdown."""
        self._title.setText(self._translator.text("events"))
        self._record.setText(self._translator.text("record_event"))
        self._description.setPlaceholderText(self._translator.text("event_description_placeholder"))
        self._timeline.setHorizontalHeaderLabels([self._translator.text("event_time"), self._translator.text("event_category"), self._translator.text("event_description")])
        self._category.blockSignals(True); self._category.clear()
        for category in _CATEGORIES:
            self._category.addItem(self._translator.text(f"event_category_{category.value}"), category)
        self._category.blockSignals(False)
        self._update_hint()

    def reload_sessions(self) -> None:
        """Repopulate the session selector, preferring the active session."""
        self._session_selector.blockSignals(True)
        self._session_selector.clear()
        for session in self._repository.list_sessions():
            self._session_selector.addItem(f"#{session.id}  {session.host}:{session.port}", session.id)
        if self._active_session_id is not None:
            index = self._session_selector.findData(self._active_session_id)
            if index >= 0:
                self._session_selector.setCurrentIndex(index)
        self._session_selector.blockSignals(False)
        self._refresh_timeline()

    def set_active_session(self, session_id: int | None) -> None:
        """Track the currently monitored session so recording targets it."""
        self._active_session_id = session_id
        self.reload_sessions()
        self._update_hint()

    def _refresh_timeline(self) -> None:
        """Reload the timeline table for the session chosen in the selector."""
        session_id = self._session_selector.currentData()
        events = self._repository.events_for_session(session_id) if session_id is not None else []
        self._timeline.setRowCount(len(events))
        for row, event in enumerate(events):
            category_label = self._translator.text(f"event_category_{event.category.value}")
            for column, value in enumerate((event.occurred_at.isoformat(sep=" ", timespec="seconds"), category_label, event.description)):
                self._timeline.setItem(row, column, QTableWidgetItem(value))

    def _update_hint(self) -> None:
        """Enable recording only while a session is actively running."""
        active = self._active_session_id is not None
        self._record.setEnabled(active)
        self._description.setEnabled(active)
        self._category.setEnabled(active)
        self._hint.setText(self._translator.text("event_hint_active" if active else "event_hint_inactive"))

    def _record_event(self) -> None:
        """Persist the entered description under the active session and refresh."""
        description = self._description.text().strip()
        if self._active_session_id is None or not description:
            return
        category = self._category.currentData()
        self._repository.record_event(self._active_session_id, category, description)
        self._description.clear()
        self.reload_sessions()
