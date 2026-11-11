"""Onglet « Console / G-Code »."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.widgets import TabToolBar

# Extensions proposées à l'export, une par bouton.
EXPORT_EXTENSIONS = (".gcode", ".nc", ".gc")


class ConsoleTab(QWidget):
    """Statistiques du job, export du G-Code et console.

    La console (`console_edit`) affiche le G-Code généré, et les messages
    de l'application et du graveur. Les boutons émettent des signaux :

        tab = ConsoleTab()
        tab.export_requested.connect(self.export_gcode_with_ext)
        tab.set_stats("Lignes : 4", "Puissance : 12 %", "Temps : 1 min")
    """

    # Extension du fichier à exporter (".gcode", ".nc" ou ".gc").
    export_requested = pyqtSignal(str)
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self._toolbar())
        layout.addWidget(self._stats_box())
        layout.addWidget(self._export_box())
        layout.addWidget(QLabel(tr("ui.generated_console_label")))
        self.console_edit = QTextEdit()
        self.console_edit.setFontFamily("Courier")
        layout.addWidget(self.console_edit)

    # -- construction

    def _toolbar(self):
        toolbar = TabToolBar(self)
        toolbar.fullscreen_requested.connect(self.fullscreen_requested)
        self._fullscreen_control = toolbar.fullscreen_action
        return toolbar

    def _stats_box(self):
        """Nombre de lignes, puissance moyenne et temps estimé du job."""
        box = QGroupBox(tr("ui.job_stats_box"))
        layout = QVBoxLayout()
        self._lines_label = QLabel(tr("ui.job_lines"))
        self._power_label = QLabel(tr("ui.job_avg_power"))
        self._time_label = QLabel(tr("ui.job_estimated_time"))
        layout.addWidget(self._lines_label)
        layout.addWidget(self._power_label)
        layout.addWidget(self._time_label)
        box.setLayout(layout)
        return box

    def _export_box(self):
        """Un bouton d'export par extension."""
        box = QGroupBox(tr("ui.gcode_export_box"))
        layout = QHBoxLayout()
        for extension in EXPORT_EXTENSIONS:
            button = QPushButton(f"Export {extension}")
            button.setStyleSheet(
                "background-color: #27ae60; color: white; "
                "font-weight: bold; padding: 6px;"
            )
            button.clicked.connect(
                lambda _checked, ext=extension: self.export_requested.emit(ext)
            )
            layout.addWidget(button)
        box.setLayout(layout)
        return box

    # -- état

    def set_stats(self, lines, power, time):
        """Textes des statistiques du job : lignes, puissance, temps."""
        self._lines_label.setText(lines)
        self._power_label.setText(power)
        self._time_label.setText(time)
