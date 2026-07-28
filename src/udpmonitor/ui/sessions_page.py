"""Session history and CSV export interface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QMainWindow

from udpmonitor.database import SessionRepository
from udpmonitor.translations.translator import Translator


class SessionsPage(QMainWindow):
    """Show saved monitor sessions and export a selected session to CSV."""

    def __init__(self, repository: SessionRepository, translator: Translator) -> None:
        """Build the history page."""
        super().__init__()
        self._repository, self._translator = repository, translator
        self._title, self._empty = QLabel(), QLabel()
        self._title.setObjectName("pageTitle"); self._empty.setObjectName("subtitle")
        self._table = QTableWidget(0, 4); self._table.setHorizontalHeaderLabels(["ID", "Started", "Endpoint", "Ended"])
        self._refresh, self._export = QPushButton(), QPushButton()
        self._refresh.clicked.connect(self.refresh); self._export.clicked.connect(self._export_selected)
        actions = QHBoxLayout(); actions.addWidget(self._refresh); actions.addWidget(self._export); actions.addStretch()
        layout = QVBoxLayout(self); layout.setContentsMargins(30, 28, 30, 30); layout.addWidget(self._title); layout.addLayout(actions); layout.addWidget(self._table); layout.addWidget(self._empty)
        self.retranslate(); translator.subscribe(self.retranslate); self.refresh()

    def refresh(self) -> None:
        """Reload sessions from SQLite."""
        sessions = self._repository.list_sessions(); self._table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            for column, value in enumerate((session.id, session.started_at.isoformat(sep=" ", timespec="seconds"), f"{session.host}:{session.port}", session.ended_at.isoformat(sep=" ", timespec="seconds") if session.ended_at else "—")):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
        self._empty.setVisible(not sessions)

    def retranslate(self) -> None:
        """Refresh localized controls."""
        self._title.setText(self._translator.text("sessions")); self._refresh.setText(self._translator.text("refresh")); self._export.setText(self._translator.text("export_csv")); self._empty.setText(self._translator.text("session_empty"))

    def _export_selected(self) -> None:
        """Choose an output path and export the selected session."""
        row = self._table.currentRow()
        if row < 0:
            return
        session_id = int(self._table.item(row, 0).text())
        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"udp-session-{session_id}.csv", "CSV (*.csv)")
        if filename:
            self._repository.export_csv(session_id, Path(filename))
