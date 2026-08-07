"""Session history, CSV export, and cross-session comparison."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from udpmonitor.database import SessionRepository
from udpmonitor.translations.translator import Translator
from udpmonitor.ui.comparison_dialog import SessionComparisonDialog


class SessionsPage(QWidget):
    """Show saved monitor sessions, export a session to CSV, and compare several."""

    def __init__(self, repository: SessionRepository, translator: Translator) -> None:
        """Build the history page."""
        super().__init__()
        self._repository, self._translator = repository, translator
        self._title, self._empty = QLabel(), QLabel()
        self._title.setObjectName("pageTitle"); self._empty.setObjectName("subtitle")
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ID", "Started", "Endpoint", "Ended"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._refresh, self._export, self._compare = QPushButton(), QPushButton(), QPushButton()
        self._refresh.clicked.connect(self.refresh)
        self._export.clicked.connect(self._export_selected)
        self._compare.clicked.connect(self._compare_selected)
        actions = QHBoxLayout(); actions.addWidget(self._refresh); actions.addWidget(self._export); actions.addWidget(self._compare); actions.addStretch()
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
        self._title.setText(self._translator.text("sessions")); self._refresh.setText(self._translator.text("refresh")); self._export.setText(self._translator.text("export_csv")); self._compare.setText(self._translator.text("compare")); self._empty.setText(self._translator.text("session_empty"))

    def _selected_session_ids(self) -> list[int]:
        """Return the unique session IDs behind the currently selected rows."""
        rows = {index.row() for index in self._table.selectionModel().selectedRows()}
        return [int(self._table.item(row, 0).text()) for row in sorted(rows)]

    def _export_selected(self) -> None:
        """Choose an output path and export the first selected session."""
        session_ids = self._selected_session_ids()
        if not session_ids:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"udp-session-{session_ids[0]}.csv", "CSV (*.csv)")
        if filename:
            self._repository.export_csv(session_ids[0], Path(filename))

    def _compare_selected(self) -> None:
        """Open a comparison dialog for two or more selected sessions."""
        session_ids = self._selected_session_ids()
        if len(session_ids) < 2:
            QMessageBox.information(self, self._translator.text("compare_sessions"), self._translator.text("compare_need_two"))
            return
        dialog = SessionComparisonDialog(self._repository, session_ids, self._translator, self)
        dialog.exec()
