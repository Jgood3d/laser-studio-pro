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

from laser_studio.i18n import tr
from laser_studio.image.resolution import (
    WARN_BELOW_RATIO, clamp, dpi_to_lmm, focal_to_lmm, lmm_to_dpi, resolution_quality,
)
from laser_studio.ui.widgets import AutoHideLabel

# Modes de saisie, dans l'ordre de la liste (et des pages de `stack`).
RESOLUTION_LMM, RESOLUTION_DPI, RESOLUTION_FOCAL = 0, 1, 2


class ResolutionBox(QWidget):
    """Mode de saisie, puis la page du mode (lignes/mm, DPI ou focale), et
    l'avis sur l'écart entre les lignes (`quality_label`, masqué s'il est
    vide).

    Les champs restent d'accord entre eux : des DPI saisis donnent les
    lignes/mm, des lignes/mm saisies donnent les DPI, et en mode focale les
    lignes/mm suivent la taille du spot (set_focal, apply_focal). Chaque
    changement de la résolution réelle émet resolution_changed :

        box = ResolutionBox()
        box.set_focal(machine.focal)
        box.resolution_changed.connect(image.schedule_processing)

    `lines_per_mm_spin` fait foi : c'est la résolution utilisée par le
    tramage, quel que soit le mode. Démarre calée sur la focale.
    """

    # Résolution réellement utilisée (lignes/mm), quel que soit le mode de saisie.
    resolution_changed = pyqtSignal(float)
    configure_focal_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._focal = None  # taille du spot laser (mm), voir set_focal
        self.lines_per_mm_spin = self._spin(1.0, 50.0, 10.0)
        self.lines_per_mm_spin.valueChanged.connect(self._on_lines_per_mm_typed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [tr("img.mode_lmm"), "DPI", tr("img.mode_focal")]
        )

        self.dpi_spin = self._spin(10.0, 2000.0, 254.0)
        self.dpi_spin.setDecimals(0)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.valueChanged.connect(self._on_dpi_typed)

        self.focal_info_label = QLabel()
        self.focal_info_label.setStyleSheet("color: #888888;")
        configure_button = QPushButton(tr("img.configure_focal"))
        configure_button.clicked.connect(self.configure_focal_requested)

        self.stack = QStackedWidget()
        # Hauteur de son contenu, sans s'étirer : sinon la place libre de
        # l'onglet allait dans la pile et écartait la liste « Résolution »
        # et le champ DPI.
        self.stack.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.stack.addWidget(self._page(self.lines_per_mm_spin))
        self.stack.addWidget(self._page(self.dpi_spin))
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
        # Branché après le choix du mode de départ : refresh() fait le premier calcul.
        self.mode_combo.currentIndexChanged.connect(self.apply_mode)

    # -- résolution

    def lines_per_mm(self):
        return self.lines_per_mm_spin.value()

    def set_focal(self, focal):
        """Taille du spot laser (mm) : sert au mode focale et à l'avis sur
        l'écart entre les lignes. Ne recalcule rien (voir apply_focal)."""
        self._focal = focal

    def refresh(self):
        """Recalcule tout d'après le mode affiché (démarrage, réglages restaurés)."""
        self.apply_mode(self.mode_combo.currentIndex())

    def apply_mode(self, index):
        """Mode de saisie choisi : sa page s'affiche, et les lignes/mm sont
        recalculées d'après lui (DPI affichés, focale) ; en mode lignes/mm,
        la valeur saisie fait foi."""
        self.stack.setCurrentIndex(index)
        if index == RESOLUTION_DPI:
            self._on_dpi_typed(self.dpi_spin.value())
        elif index == RESOLUTION_FOCAL:
            self.apply_focal()
        else:
            self._sync_dpi(self.lines_per_mm())
            self._resolution_updated()

    def apply_focal(self):
        """Lignes/mm calées sur la taille du spot (lignes/mm = 1 / focale), DPI
        équivalents, et rappel de la focale sur la page du mode focale. La
        focale est une caractéristique du laser : elle s'applique quel que
        soit le mode affiché."""
        focal = self._focal if self._focal and self._focal > 0 else 0.1
        lmm = self._set_lines_per_mm(focal_to_lmm(focal))
        self._sync_dpi(lmm)
        self.focal_info_label.setText(
            tr("image.focal_info").format(focal=focal, lmm=lmm, dpi=lmm_to_dpi(lmm)))
        self._resolution_updated()

    def _on_dpi_typed(self, dpi):
        """DPI saisis : lignes/mm correspondants (voir image.resolution)."""
        self._set_lines_per_mm(dpi_to_lmm(dpi))
        self._resolution_updated()

    def _on_lines_per_mm_typed(self, lmm):
        self._sync_dpi(lmm)
        self._resolution_updated()

    def _set_lines_per_mm(self, lmm):
        """Lignes/mm (bornées au champ), sans signal du champ. Renvoie la valeur posée."""
        spin = self.lines_per_mm_spin
        lmm = clamp(lmm, spin.minimum(), spin.maximum())
        spin.blockSignals(True)
        spin.setValue(lmm)
        spin.blockSignals(False)
        return lmm

    def _sync_dpi(self, lmm):
        self.dpi_spin.blockSignals(True)
        self.dpi_spin.setValue(lmm_to_dpi(lmm))
        self.dpi_spin.blockSignals(False)

    def _resolution_updated(self):
        """Avis sur l'écart entre les lignes, puis resolution_changed."""
        self._update_quality()
        self.resolution_changed.emit(self.lines_per_mm())

    def _update_quality(self):
        """Avis affiché seulement pour un écart trop fin par rapport au spot
        (risque de surgravure ou de brûlure), en multiples de la focale (seuils
        dans image.resolution) ; rien tant que la focale n'est pas connue."""
        quality = resolution_quality(self._focal, self.lines_per_mm()) if self._focal else None
        if quality is None or quality[1] >= WARN_BELOW_RATIO:
            self.quality_label.setText("")
            return
        spacing, ratio, key, color = quality
        self.quality_label.setText(
            tr("image.quality_result").format(spacing=spacing, ratio=ratio, quality=tr(key)))
        self.quality_label.setStyleSheet(f"color: {color};")

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
