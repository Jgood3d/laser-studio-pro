"""Résolution de la gravure d'une image : en lignes/mm, en DPI, ou calée
sur la focale du laser."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from ui.widgets import AutoHideLabel

# Modes de saisie, dans l'ordre de la liste (et des pages de `stack`).
RESOLUTION_LMM, RESOLUTION_DPI, RESOLUTION_FOCAL = 0, 1, 2


class ResolutionBox(QWidget):
    """Mode de saisie, puis la page du mode (lignes/mm, DPI ou focale), et
    l'avis sur l'écart entre les lignes (`quality_label`, masqué s'il est
    vide).

    Le calcul est fait par la fenêtre, qui s'abonne aux signaux :

        box = ResolutionBox()
        box.mode_changed.connect(self.on_lmm_mode_changed)
        box.dpi_changed.connect(self.on_dpi_value_changed)

    `lines_per_mm_spin` fait foi : c'est la résolution utilisée par le
    tramage, quel que soit le mode. Démarre calée sur la focale.
    """

    # Mode de saisie (RESOLUTION_LMM, _DPI ou _FOCAL).
    mode_changed = pyqtSignal(int)
    # Résolution en lignes/mm, et en DPI.
    lines_per_mm_changed = pyqtSignal(float)
    dpi_changed = pyqtSignal(float)
    configure_focal_requested = pyqtSignal()
    save_as_focal_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines_per_mm_spin = self._spin(1.0, 50.0, 10.0)
        self.lines_per_mm_spin.valueChanged.connect(self.lines_per_mm_changed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [tr("img.mode_lmm"), "DPI", tr("img.mode_focal")]
        )
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)

        self.dpi_spin = self._spin(10.0, 2000.0, 254.0)
        self.dpi_spin.setDecimals(0)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.valueChanged.connect(self.dpi_changed)

        self.focal_info_label = QLabel()
        self.focal_info_label.setStyleSheet("color: #888888;")
        configure_button = QPushButton(tr("img.configure_focal"))
        configure_button.clicked.connect(self.configure_focal_requested)

        self.stack = QStackedWidget()
        # Hauteur de son contenu, sans s'étirer : sinon la place libre de
        # l'onglet allait dans la pile et écartait la liste « Résolution »,
        # le champ DPI et « Enregistrer comme focale ».
        self.stack.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.stack.addWidget(
            self._page(self.lines_per_mm_spin, self._save_as_focal_button())
        )
        self.stack.addWidget(
            self._page(self.dpi_spin, self._save_as_focal_button())
        )
        self.stack.addWidget(
            self._page(self.focal_info_label, configure_button)
        )

        self.quality_label = AutoHideLabel()
        self.quality_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.stack)
        layout.addWidget(self.quality_label)

        self.mode_combo.setCurrentIndex(RESOLUTION_FOCAL)
        self.stack.setCurrentIndex(RESOLUTION_FOCAL)

    def _save_as_focal_button(self):
        button = QPushButton(tr("img.save_as_focal"))
        button.clicked.connect(self.save_as_focal_requested)
        return button

    @staticmethod
    def _page(*widgets):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            layout.addWidget(widget)
        return page

    @staticmethod
    def _spin(minimum, maximum, value):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin
