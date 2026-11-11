"""Curseur entre deux boutons « - » / « + », avec sa valeur affichée."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QWidget


class SliderWithButtons(QWidget):
    """Curseur horizontal, boutons « - » / « + » d'un pas `step`, et valeur
    affichée à droite (mise en forme par `formatter`, str par défaut).

        row = SliderWithButtons(-100, 100, 0)
        row.value_changed.connect(self.update_image_processing)

    Le curseur reste accessible (`slider`) pour lire ou régler la valeur.
    """

    value_changed = pyqtSignal(int)

    def __init__(
        self, minimum, maximum, value, step=5, formatter=None, parent=None
    ):
        super().__init__(parent)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self.value_changed)
        self._formatter = formatter or str

        minus = QPushButton("-")
        minus.setFixedWidth(30)
        minus.clicked.connect(
            lambda: self.slider.setValue(self.slider.value() - step)
        )
        plus = QPushButton("+")
        plus.setFixedWidth(30)
        plus.clicked.connect(
            lambda: self.slider.setValue(self.slider.value() + step)
        )
        self._value_label = QLabel()
        self._value_label.setFixedWidth(45)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider.valueChanged.connect(self._show_value)
        self._show_value(self.slider.value())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(minus)
        layout.addWidget(self.slider)
        layout.addWidget(plus)
        layout.addWidget(self._value_label)

    def _show_value(self, value):
        self._value_label.setText(self._formatter(value))
