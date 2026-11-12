"""Position de la machine : X, Y et Z sur une ligne."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from laser_studio.i18n import tr

# Style des valeurs : chasse fixe, pour que les chiffres restent alignés.
VALUE_STYLE = "font-family: monospace; font-size: 13px;"
NO_VALUE = "—"
AXES = ("ui.dro_x", "ui.dro_y", "ui.dro_z")


class AxisPositionRow(QWidget):
    """X, Y et Z côte à côte, répartis à parts égales sur la largeur.

    Simple affichage : la fenêtre lui transmet chaque position reçue du
    graveur, en mm, ou None quand la position n'est plus connue :

        row = AxisPositionRow()
        row.set_position(12.5, 30.0, 0.0)
        row.set_position(None)          # « X : — mm »…
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_label, self.y_label, self.z_label = (QLabel() for _ in AXES)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for label in self._labels():
            label.setStyleSheet(VALUE_STYLE)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label, 1)
        self.set_position(None)

    def set_position(self, x, y=0.0, z=0.0):
        """Position en mm, trois décimales ; `x` à None : des tirets."""
        values = (NO_VALUE,) * 3 if x is None else (f"{v:.3f}" for v in (x, y, z))
        for label, key, value in zip(self._labels(), AXES, values):
            label.setText(tr(key).format(value=value))

    def _labels(self):
        return (self.x_label, self.y_label, self.z_label)
