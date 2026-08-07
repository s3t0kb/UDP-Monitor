"""Side-by-side comparison of two or more monitoring sessions."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from udpmonitor.database import SessionRepository
from udpmonitor.models import SessionSummary
from udpmonitor.translations.translator import Translator

_ROW_KEYS = ("compare_host", "compare_sample_count", "compare_success_rate", "compare_avg_rtt", "compare_avg_jitter", "compare_avg_loss", "compare_duration")


class SessionComparisonDialog(QDialog):
    """Show aggregate UDP quality statistics for several sessions side by side."""

    def __init__(self, repository: SessionRepository, session_ids: list[int], translator: Translator, parent: QWidget | None = None) -> None:
        """Load summaries for the given sessions and render a comparison table."""
        super().__init__(parent)
        self._translator = translator
        self.resize(680, 380)
        summaries = [repository.session_summary(session_id) for session_id in session_ids]

        self._table = QTableWidget(len(_ROW_KEYS), len(summaries))
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for column, summary in enumerate(summaries):
            self._table.setHorizontalHeaderItem(column, QTableWidgetItem(f"#{summary.session_id}"))
            for row, value in enumerate(self._row_values(summary)):
                self._table.setItem(row, column, QTableWidgetItem(value))

        self._close_button = QPushButton()
        self._close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addWidget(self._close_button)
        self.retranslate()

    def retranslate(self) -> None:
        """Refresh localized labels."""
        self.setWindowTitle(self._translator.text("compare_sessions"))
        self._table.setVerticalHeaderLabels([self._translator.text(key) for key in _ROW_KEYS])
        self._close_button.setText(self._translator.text("close"))

    @staticmethod
    def _row_values(summary: SessionSummary) -> list[str]:
        """Format one summary's statistics as display strings, in _ROW_KEYS order."""
        success_rate = summary.success_rate_percent
        return [
            f"{summary.host}:{summary.port}",
            str(summary.sample_count),
            "--" if success_rate is None else f"{success_rate:.1f} %",
            "--" if summary.average_rtt_milliseconds is None else f"{summary.average_rtt_milliseconds:.1f} ms",
            "--" if summary.average_jitter_milliseconds is None else f"{summary.average_jitter_milliseconds:.1f} ms",
            "--" if summary.average_loss_percent is None else f"{summary.average_loss_percent:.1f} %",
            summary.duration_text,
        ]
