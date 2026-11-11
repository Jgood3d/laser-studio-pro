"""Onglet « Visualisation 2D G-Code »."""

import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.widgets import TabToolBar


class Preview2DTab(QWidget):
    """Aperçu 2D du G-Code, avec ses options dans la barre d'outils.

    Il ne dessine pas le G-Code lui-même : la génération dessine dans
    `plot_widget`, et place la tête du laser avec `position_marker`. Les
    options et les clics émettent des signaux :

        tab = Preview2DTab()
        tab.display_options_changed.connect(self.redraw_preview)
        tab.plot_clicked.connect(self._on_plot_clicked)

    Les cases restent lisibles directement (flip_check, negative_check,
    hide_rapid_check, optimize_path_check). « Optimiser le chemin »
    s'applique à la prochaine génération, pas à l'aperçu affiché.
    """

    # Une option d'affichage a changé (inverser, négatif, déplacements
    # rapides) : l'aperçu est à redessiner.
    display_options_changed = pyqtSignal()
    # Clic sur l'aperçu, en mm dans le repère du lit.
    plot_clicked = pyqtSignal(float, float)
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(self._toolbar())
        layout.addWidget(self._plot())

    # -- construction

    def _toolbar(self):
        """Barre d'outils : les options de l'aperçu, et le plein écran."""
        self.flip_check = self._option(
            "preview.flip", "preview.flip_tip", checked=False
        )
        self.negative_check = self._option(
            "preview.negative", "preview.negative_tip"
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
        toolbar = TabToolBar(
            self,
            left_widgets=[
                self.flip_check,
                self.negative_check,
                self.hide_rapid_check,
                self.optimize_path_check,
            ],
        )
        toolbar.fullscreen_requested.connect(self.fullscreen_requested)
        self._fullscreen_control = toolbar.fullscreen_action
        return toolbar

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
