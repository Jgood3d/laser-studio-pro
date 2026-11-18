"""Onglet « Visualisation 2D G-Code »."""

import pyqtgraph as pg
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QComboBox, QLabel, QSplitter, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.tabs.preview_2d.job_stats_panel import JobStatsPanel
from laser_studio.ui.widgets import FloatingToolBar

# Écart entre la poignée du séparateur et les cadres de la colonne de droite.
SIDE_PANEL_LEFT_MARGIN = 6
# Presets matière de l'aperçu (clés partagées avec gcode_generation_mixin).
_PREVIEW_MATERIAL_KEYS = ("light", "wood", "bamboo", "slate", "acrylic_black")


class Preview2DTab(QWidget):
    """Aperçu 2D du G-Code, avec ses options dans une barre flottante en
    haut du graphique (options_toolbar). À sa
    droite, de l'autre côté d'un séparateur réglable, une colonne étroite :
    la position du job sur le plateau, puis les statistiques du job
    (job_stats_panel).

    Il ne dessine pas le G-Code lui-même : la génération dessine dans
    `plot_widget`, et place la tête du laser avec `position_marker`. Les
    options et les clics émettent des signaux :

        tab = Preview2DTab(job_position_box)
        tab.display_options_changed.connect(self.redraw_preview)
        tab.plot_clicked.connect(self._on_plot_clicked)

    Les cases restent lisibles directement (flip_check, negative_check,
    hide_rapid_check, optimize_path_check). « Optimiser le chemin »
    s'applique à la prochaine génération, pas à l'aperçu affiché.

    `job_position_box` : cadre « Position du job sur le plateau »
    (JobPositionBox), construit avec l'onglet image, placé en haut de la
    colonne de droite.
    """

    # Une option d'affichage a changé (inverser, négatif, déplacements
    # rapides) : l'aperçu est à redessiner.
    display_options_changed = pyqtSignal()
    # Clic sur l'aperçu, en mm dans le repère du lit.
    plot_clicked = pyqtSignal(float, float)

    def __init__(self, job_position_box, parent=None):
        super().__init__(parent)
        self.job_position_box = job_position_box
        self.job_stats_panel = JobStatsPanel()
        self.side_panel = self._side_panel()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self._plot())
        self.splitter.addWidget(self.side_panel)
        # Colonne de droite aussi étroite que possible : Qt la ramène à sa
        # largeur minimale. Elle garde sa largeur quand la fenêtre change de
        # taille ; le séparateur reste réglable.
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([100000, 1])
        layout = QVBoxLayout(self)
        self._create_options()
        layout.addWidget(self.splitter)
        # Options de l'aperçu : barre flottante sous le titre du graphique.
        self.options_toolbar = FloatingToolBar(
            [
                self.material_label,
                self.material_combo,
                None,
                self.flip_check,
                self.negative_check,
                self.hide_rapid_check,
                None,
                self.optimize_path_check,
            ],
            self.plot_widget,
            top_margin=30,
        )

    # -- construction

    def _side_panel(self):
        """Position du job sur le plateau, puis statistiques du job."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        # Marge à gauche : les cadres ne touchent pas la poignée du séparateur.
        layout.setContentsMargins(SIDE_PANEL_LEFT_MARGIN, 0, 0, 0)
        layout.addWidget(self.job_position_box)
        layout.addWidget(self.job_stats_panel)
        layout.addStretch()
        return panel

    def _create_options(self):
        """Options de l'aperçu, affichées dans la barre flottante
        (options_toolbar)."""
        self.material_label = QLabel(tr("preview.material_label"))
        self.material_combo = QComboBox()
        self.material_combo.setToolTip(tr("preview.material_tip"))
        for key in _PREVIEW_MATERIAL_KEYS:
            self.material_combo.addItem(tr(f"preview.material.{key}"), key)
        # Dernier choix mémorisé (sinon fond clair, comme avant).
        saved = QSettings().value("preview_material", "light")
        idx = self.material_combo.findData(saved)
        self.material_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.material_combo.currentIndexChanged.connect(self._on_material_changed)

        self.flip_check = self._option(
            "preview.flip", "preview.flip_tip", checked=False
        )
        # Décochée : aperçu réaliste (brûlure de la matière choisie sur les zones gravées).
        # Cochée, elle inverse zones gravées et non gravées : une gravure de texte en réserve
        # semblait alors inversée.
        self.negative_check = self._option(
            "preview.negative", "preview.negative_tip", checked=False
        )
        self.hide_rapid_check = self._option(
            "preview.hide_rapid", "preview.hide_rapid_tip"
        )
        for check in (
            self.flip_check,
            self.negative_check,
            self.hide_rapid_check,
        ):
            check.stateChanged.connect(self.display_options_changed)
        self.optimize_path_check = self._option(
            "ui.optimize_path", "ui.optimize_path_tip"
        )

    def _on_material_changed(self, *_args):
        """Mémorise le preset et redessine l'aperçu."""
        key = self.material_combo.currentData() or "light"
        QSettings().setValue("preview_material", key)
        self.display_options_changed.emit()

    @staticmethod
    def _option(key, tip_key, checked=True):
        check = QCheckBox(tr(key))
        check.setToolTip(tr(tip_key))
        check.setChecked(checked)
        return check

    def _plot(self):
        """Zone de dessin, avec le point rouge de la tête et le texte
        affiché tant qu'aucun G-Code n'est généré."""
        self.plot_widget = pg.PlotWidget(title=tr("ui.plot_title"))
        self.plot_widget.setBackground("#111111")
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", tr("ui.plot_x"), color="#ffffff")
        self.plot_widget.setLabel("left", tr("ui.plot_y"), color="#ffffff")
        self.plot_widget.scene().sigMouseClicked.connect(self._on_clicked)

        self.position_marker = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#ff2d55"),
            symbol="o",
        )
        self.position_marker.setZValue(1000)
        self.plot_widget.addItem(self.position_marker)

        # Remplacé par la légende au premier aperçu dessiné.
        self.info_text_item = pg.TextItem(
            html=(
                '<div style="color: #cccccc;">'
                f'{tr("ui.plot_empty_state")}</div>'
            ),
            anchor=(0, 0),
        )
        self.plot_widget.addItem(self.info_text_item)
        return self.plot_widget

    # -- événements

    def _on_clicked(self, event):
        """Convertit la position du clic en mm, dans le repère du lit."""
        view_box = self.plot_widget.getPlotItem().vb
        pos = view_box.mapSceneToView(event.scenePos())
        self.plot_clicked.emit(pos.x(), pos.y())
