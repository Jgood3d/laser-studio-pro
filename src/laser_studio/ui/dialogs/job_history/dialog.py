"""Fenêtre « Historique des gravures » : une ligne par job envoyé, du plus récent au plus ancien (date,
issue, durée réelle et estimée, écart, distance gravée, lignes, profil machine), export CSV et effacement.
Elle suit le modèle (JobHistory.changed) : une gravure qui se termine apparaît aussitôt."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from laser_studio.i18n import tr
from laser_studio.i18n.durations import duration_text

COLUMNS = ("history.col_date", "history.col_result", "history.col_duration", "history.col_estimate",
           "history.col_gap", "history.col_burn", "history.col_lines", "history.col_profile")


def gap_text(entry):
    """Écart entre la durée estimée et la durée réelle, en % de la réelle (« +12 % » : estimation trop
    longue), pour une gravure terminée ; "" sinon (arrêtée en cours de route, ou une durée manque)."""
    real, estimate = entry.get("duration_s"), entry.get("estimated_s")
    if entry.get("result") != "done" or not real or estimate is None:
        return ""
    return f"{(estimate - real) / real * 100:+.0f} %"


class JobHistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("history.title"))
        self.setModal(False)                      # consultée à côté de la fenêtre principale
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(980, 520)
        self.history = history
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(key) for key in COLUMNS])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.summary = QLabel()
        export = QPushButton(tr("history.export"))
        export.clicked.connect(self._export)
        clear = QPushButton(tr("history.clear"))
        clear.clicked.connect(self._clear)
        close = QPushButton(tr("history.close"))
        close.clicked.connect(self.close)
        row = QHBoxLayout()
        row.addWidget(self.summary, 1)
        row.addWidget(export)
        row.addWidget(clear)
        row.addWidget(close)
        layout = QVBoxLayout(self)
        intro = QLabel(tr("history.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addWidget(self.table, 1)
        layout.addLayout(row)
        history.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        entries = list(reversed(self.history.entries()))
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            estimate = entry.get("estimated_s")
            burn = entry.get("burn_mm")
            values = (entry.get("started_at", ""), tr(f"history.result.{entry.get('result', 'interrupted')}"),
                      duration_text(entry.get("duration_s") or 0),
                      duration_text(estimate) if estimate is not None else "—", gap_text(entry),
                      f"{burn / 1000:.2f} m" if burn else "", str(entry.get("lines") or ""), entry.get("profile") or "")
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (2, 3, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        total = sum(e.get("duration_s") or 0 for e in entries if e.get("result") == "done")
        self.summary.setText(tr("history.summary").format(count=len(entries), total=duration_text(total)))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("history.export"), "historique-gravures.csv",
                                              tr("history.csv_filter"))
        if not path:
            return
        try:
            self.history.export_csv(path)
        except OSError as error:
            QMessageBox.warning(self, tr("history.title"), str(error))

    def _clear(self):
        answer = QMessageBox.question(self, tr("history.title"), tr("history.clear_question"),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.history.clear()
