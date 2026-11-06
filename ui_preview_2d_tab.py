"""Onglet d'aperçu 2D du G-Code."""

import pyqtgraph as pg
from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QWidget
from i18n import tr


class Preview2DTabMixin:
    def _build_2d_preview_tab(self):
        """Onglet d'aperçu 2D du G-Code."""
        tab_vector_2d = QWidget()
        layout_vector_2d = QVBoxLayout(tab_vector_2d)

        # Options de l'aperçu (anciennes cases du bas de la colonne de gauche).
        # « Optimiser le chemin », elle, s'applique à la prochaine génération
        # du G-Code.
        self.chk_flip_raster_preview = QCheckBox(tr("preview.flip"))
        self.chk_flip_raster_preview.setToolTip(tr("preview.flip_tip"))
        self.chk_flip_raster_preview.stateChanged.connect(
            self.on_flip_raster_preview_changed
        )
        self.chk_negative_raster_preview = QCheckBox(tr("preview.negative"))
        self.chk_negative_raster_preview.setToolTip(tr("preview.negative_tip"))
        self.chk_negative_raster_preview.setChecked(True)
        self.chk_negative_raster_preview.stateChanged.connect(
            self.on_flip_raster_preview_changed
        )
        self.chk_hide_rapid_moves = QCheckBox(tr("preview.hide_rapid"))
        self.chk_hide_rapid_moves.setToolTip(tr("preview.hide_rapid_tip"))
        self.chk_hide_rapid_moves.setChecked(True)
        self.chk_hide_rapid_moves.stateChanged.connect(
            self.on_flip_raster_preview_changed
        )
        self.chk_optimize_path = QCheckBox(tr("ui.optimize_path"))
        self.chk_optimize_path.setToolTip(tr("ui.optimize_path_tip"))
        self.chk_optimize_path.setChecked(True)
        toolbar_vector_2d = self._build_tab_toolbar(
            tab_vector_2d,
            lambda: self._toggle_fullscreen_tab(
                "tab_vector_2d", "ui.tab_2d_preview"
            ),
            left_widgets=[
                self.chk_flip_raster_preview,
                self.chk_negative_raster_preview,
                self.chk_hide_rapid_moves,
                self.chk_optimize_path,
            ],
            right_widgets=[self._build_support_button()],
        )
        layout_vector_2d.addWidget(toolbar_vector_2d)

        self.plot_widget = pg.PlotWidget(title=tr("ui.plot_title"))
        self.plot_widget.setBackground("#111111")
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", tr("ui.plot_x"), color="#ffffff")
        self.plot_widget.setLabel("left", tr("ui.plot_y"), color="#ffffff")
        self.plot_widget.scene().sigMouseClicked.connect(self._on_plot_clicked)

        self.gcode_position_marker = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen("#ffffff", width=2),
            brush=pg.mkBrush("#ff2d55"),
            symbol="o",
        )
        self.gcode_position_marker.setZValue(1000)
        self.plot_widget.addItem(self.gcode_position_marker)

        self.info_text_item = pg.TextItem(
            html=(
                '<div style="color: #cccccc;">'
                f'{tr("ui.plot_empty_state")}</div>'
            ),
            anchor=(0, 0),
        )
        self.plot_widget.addItem(self.info_text_item)

        layout_vector_2d.addWidget(self.plot_widget)

        self.main_tabs_view.addTab(tab_vector_2d, tr("ui.tab_2d_preview"))
        self.tab_vector_2d = tab_vector_2d
