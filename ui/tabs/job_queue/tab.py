"""Onglet « File d'attente »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from i18n import tr


class JobQueueTab(QWidget):
    """File d'attente des jobs à gauche, G-Code envoyé à droite.

    Elle ne gère pas la file : ses boutons et le glisser-déposer émettent
    des signaux, auxquels la fenêtre (plus tard un contrôleur) s'abonne :

        tab = JobQueueTab()
        tab.run_requested.connect(self.run_job_queue)
        tab.reordered.connect(self._on_queue_reordered)

    Les éléments restent accessibles directement (queue_list, run_button,
    status_label, sent_gcode_edit).
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
        """Suivi de l'envoi : chaque ligne de G-Code s'ajoute ici au moment
        où elle part vers la machine, pour la file comme pour « Envoyer au
        laser »."""
        sent_box = QGroupBox(tr("queue.sent_log_title"))
        sent_layout = QVBoxLayout(sent_box)
        self.sent_gcode_edit = QPlainTextEdit()
        self.sent_gcode_edit.setReadOnly(True)
        # Garde les 20 000 dernières lignes.
        self.sent_gcode_edit.setMaximumBlockCount(20000)
        self.sent_gcode_edit.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.sent_gcode_edit.setStyleSheet("font-family: monospace;")
        self.sent_gcode_edit.setPlaceholderText(
            tr("queue.sent_log_placeholder")
        )
        sent_layout.addWidget(self.sent_gcode_edit)
        return sent_box
