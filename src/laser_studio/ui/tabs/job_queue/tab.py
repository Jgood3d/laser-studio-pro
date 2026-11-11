"""Onglet « File d'attente »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.tabs.job_queue.sent_gcode_log import SentGcodeLog


class JobQueueTab(QWidget):
    """File d'attente des jobs à gauche, G-Code envoyé à droite.

    Elle ne gère pas la file : ses boutons et le glisser-déposer émettent
    des signaux, auxquels la fenêtre (plus tard un contrôleur) s'abonne :

        tab = JobQueueTab()
        tab.run_requested.connect(queue.run)
        tab.reordered.connect(queue.on_reordered)

    Son état se règle par des méthodes : liste des jobs (add_job,
    remove_job, set_jobs...), texte d'état, bouton « Lancer », et suivi du
    G-Code envoyé (append_sent_gcode, mark_sent_end). Les éléments restent
    accessibles (queue_list, run_button, status_label, sent_gcode_edit).
    """

    add_current_requested = pyqtSignal()
    remove_selected_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    run_requested = pyqtSignal()
    # Les jobs ont été réordonnés par glisser-déposer dans la liste.
    reordered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        # Deux moitiés réglables : la file à gauche, le G-Code envoyé à droite.
        queue_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(queue_splitter)
        queue_left = self._queue_panel()
        queue_splitter.addWidget(queue_left)
        sent_box = self._sent_box()
        queue_splitter.addWidget(sent_box)
        # Moitié / moitié au départ, puis à chaque redimensionnement de la
        # fenêtre. Des tailles égales et grandes : Qt les ramène à la largeur
        # réelle en gardant la proportion.
        queue_splitter.setStretchFactor(0, 1)
        queue_splitter.setStretchFactor(1, 1)
        queue_splitter.setSizes([100000, 100000])

    # -- construction

    def _queue_panel(self):
        """Liste des jobs, réordonnable, et ses boutons."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.queue_list = QListWidget()
        self.queue_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.queue_list.model().rowsMoved.connect(self.reordered)
        layout.addWidget(self.queue_list)

        buttons = QHBoxLayout()
        for key, signal in (
            ("ui.queue_add_current", self.add_current_requested),
            ("ui.queue_remove_selected", self.remove_selected_requested),
            ("ui.queue_clear", self.clear_requested),
        ):
            button = QPushButton(tr(key))
            button.clicked.connect(signal)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.run_button = QPushButton(tr("ui.queue_run"))
        self.run_button.setStyleSheet(
            "background-color: #8e44ad; color: white; "
            "font-weight: bold; padding: 6px;"
        )
        self.run_button.clicked.connect(self.run_requested)
        layout.addWidget(self.run_button)

        self.status_label = QLabel(tr("ui.queue_empty"))
        layout.addWidget(self.status_label)
        return panel

    def _sent_box(self):
        """Suivi du G-Code envoyé (voir SentGcodeLog)."""
        self.sent_log = SentGcodeLog()
        self.sent_gcode_edit = self.sent_log.text_edit
        return self.sent_log

    # -- liste des jobs

    def add_job(self, name):
        self.queue_list.addItem(name)

    def remove_job(self, row):
        self.queue_list.takeItem(row)

    def set_jobs(self, names):
        """Remplace la liste par ces noms, dans cet ordre."""
        self.queue_list.clear()
        for name in names:
            self.queue_list.addItem(name)

    def job_names(self):
        """Noms des jobs, dans l'ordre affiché."""
        return [
            self.queue_list.item(row).text()
            for row in range(self.queue_list.count())
        ]

    def selected_row(self):
        """Ligne sélectionnée, ou -1."""
        return self.queue_list.currentRow()

    def select_job(self, row):
        self.queue_list.setCurrentRow(row)

    # -- état

    def set_status(self, text):
        self.status_label.setText(text)

    def set_run_enabled(self, enabled):
        self.run_button.setEnabled(enabled)

    # -- G-Code envoyé

    def clear_sent_gcode(self):
        self.sent_log.clear_lines()

    def append_sent_gcode(self, lines):
        """Ajoute des lignes au suivi d'envoi (lignes du G-Code au moment où
        elles partent vers la machine, ou repères de début et de fin)."""
        self.sent_log.append_lines(lines)

    def mark_sent_end(self, clean_finish):
        """Repère de fin d'envoi : terminé, ou interrompu."""
        self.sent_log.mark_end(clean_finish)
