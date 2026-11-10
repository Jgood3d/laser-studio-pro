"""Suivi du G-Code envoyé au graveur (onglet « File d'attente »)."""

from PyQt6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout

from i18n import tr

# Lignes gardées : les plus anciennes disparaissent au-delà.
MAX_LINES = 20000


class SentGcodeLog(QGroupBox):
    """Chaque ligne de G-Code s'ajoute ici au moment où elle part vers la
    machine, pour la file comme pour « Envoyer au laser », avec des repères
    de début et de fin d'envoi. Le texte reste accessible (`text_edit`).
    """

    def __init__(self, parent=None):
        super().__init__(tr("queue.sent_log_title"), parent)
        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(MAX_LINES)
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setStyleSheet("font-family: monospace;")
        self.text_edit.setPlaceholderText(tr("queue.sent_log_placeholder"))
        layout.addWidget(self.text_edit)

    def clear_lines(self):
        self.text_edit.clear()

    def append_lines(self, lines):
        """Ajoute des lignes (G-Code envoyé, ou repères)."""
        if lines:
            self.text_edit.appendPlainText("\n".join(lines))

    def mark_end(self, clean_finish):
        """Repère de fin d'envoi : terminé, ou interrompu."""
        key = (
            "queue.sent_log_done" if clean_finish else "queue.sent_log_stopped"
        )
        self.append_lines([tr(key)])
