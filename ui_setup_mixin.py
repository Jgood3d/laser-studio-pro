"""Onglet « Éditeur vectoriel ».

L'assemblage de la fenêtre (init_ui) est dans main_window.py. Cet onglet
partira dans ui/tabs/ quand Julien aura fini son travail sur le vectoriel.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QDoubleSpinBox, QGroupBox, QCheckBox)
from vector_layers import VectorCanvasView
from i18n import tr
from ui.utils import fullscreen_icon


class UiSetupMixin:
    def _build_vector_editor_tab(self):
        """Onglet « Éditeur vectoriel »."""
        tab_vector_editor = QWidget()
        layout_vector_editor = QVBoxLayout(tab_vector_editor)

        toolbar_vector = QHBoxLayout()
        btn_add_text = QPushButton(tr("ui.vector_add_text"))
        btn_add_text.clicked.connect(self.insert_text_object)
        btn_add_shape = QPushButton(tr("ui.vector_add_shape"))
        btn_add_shape.clicked.connect(self.insert_shape_object)
        btn_import_svg_vector = QPushButton(tr("ui.vector_import_svg"))
        btn_import_svg_vector.setStyleSheet("background-color: #3a6b3a; color: white;")
        btn_import_svg_vector.clicked.connect(self.import_svg_to_vector_editor)
        btn_box_generator = QPushButton(tr("ui.vector_box_generator"))
        btn_box_generator.setToolTip(tr("ui.vector_box_generator_tip"))
        btn_box_generator.clicked.connect(self.open_box_generator)
        btn_nesting = QPushButton(tr("ui.vector_nesting"))
        btn_nesting.setToolTip(tr("ui.vector_nesting_tip"))
        btn_nesting.clicked.connect(self.open_nesting)
        btn_edit_selected = QPushButton(tr("ui.vector_edit_selection"))
        btn_edit_selected.clicked.connect(self.edit_selected_vector_object)
        btn_rotate_selected = QPushButton(tr("ui.vector_rotate_90"))
        btn_rotate_selected.clicked.connect(self.rotate_selected_vector_object)
        btn_dup_selected = QPushButton(tr("ui.vector_duplicate"))
        btn_dup_selected.clicked.connect(self.duplicate_selected_vector_object)
        btn_del_selected = QPushButton(tr("ui.vector_delete"))
        btn_del_selected.clicked.connect(self.delete_selected_vector_object)
        btn_explode_path = QPushButton(tr("vector.explode_path"))
        btn_explode_path.clicked.connect(lambda: self.vector_canvas.explode_selected())
        btn_edit_nodes = QPushButton(tr("vector.edit_nodes"))
        btn_edit_nodes.clicked.connect(lambda: self.vector_canvas.enter_node_edit())
        btn_undo_vector = QPushButton(tr("ui.vector_undo"))
        btn_undo_vector.clicked.connect(lambda: self.vector_canvas.undo())
        btn_redo_vector = QPushButton(tr("ui.vector_redo"))
        btn_redo_vector.clicked.connect(lambda: self.vector_canvas.redo())
        btn_fullscreen_vector = QPushButton(tr("ui.vector_fullscreen"))
        btn_fullscreen_vector.setIcon(fullscreen_icon(self))
        btn_fullscreen_vector.clicked.connect(self.toggle_fullscreen_vector_editor)
        tab_vector_editor._fullscreen_control = btn_fullscreen_vector   # voir _show_fullscreen_control
        # Outils de dessin à la souris (ligne / rectangle / ellipse) + sélection
        self._vector_draw_buttons = {}
        btn_draw_select = QPushButton(tr("ui.vector_tool_select"))
        btn_draw_select.setCheckable(True)
        btn_draw_select.setChecked(True)
        btn_draw_select.setToolTip(tr("ui.vector_tool_select_tip"))
        btn_draw_select.clicked.connect(lambda: self.set_vector_draw_tool(None))
        btn_draw_line = QPushButton(tr("ui.vector_tool_line"))
        btn_draw_line.setCheckable(True)
        btn_draw_line.setToolTip(tr("ui.vector_tool_line_tip"))
        btn_draw_line.clicked.connect(lambda: self.set_vector_draw_tool("line"))
        btn_draw_rect = QPushButton(tr("ui.vector_tool_rect"))
        btn_draw_rect.setCheckable(True)
        btn_draw_rect.setToolTip(tr("ui.vector_tool_rect_tip"))
        btn_draw_rect.clicked.connect(lambda: self.set_vector_draw_tool("rect"))
        btn_draw_ellipse = QPushButton(tr("ui.vector_tool_ellipse"))
        btn_draw_ellipse.setCheckable(True)
        btn_draw_ellipse.setToolTip(tr("ui.vector_tool_ellipse_tip"))
        btn_draw_ellipse.clicked.connect(lambda: self.set_vector_draw_tool("ellipse"))
        btn_draw_measure = QPushButton(tr("ui.vector_tool_measure"))
        btn_draw_measure.setCheckable(True)
        btn_draw_measure.setToolTip(tr("ui.vector_tool_measure_tip"))
        btn_draw_measure.clicked.connect(lambda: self.set_vector_draw_tool("measure"))
        self._vector_draw_buttons = {
            None: btn_draw_select,
            "line": btn_draw_line,
            "rect": btn_draw_rect,
            "ellipse": btn_draw_ellipse,
            "measure": btn_draw_measure,
        }

        # Barres compactes : 2 rangées au lieu de 3 + marges réduites pour le canevas
        layout_vector_editor.setContentsMargins(4, 4, 4, 4)
        layout_vector_editor.setSpacing(4)

        # Rangée 1 : créer / importer / outils spéciaux + plein écran
        toolbar_vector = QHBoxLayout()
        toolbar_vector.setSpacing(4)
        toolbar_vector.addWidget(btn_add_text)
        toolbar_vector.addWidget(btn_add_shape)
        toolbar_vector.addWidget(btn_import_svg_vector)
        toolbar_vector.addWidget(btn_box_generator)
        toolbar_vector.addWidget(btn_nesting)
        toolbar_vector.addStretch()
        toolbar_vector.addWidget(btn_fullscreen_vector)
        layout_vector_editor.addLayout(toolbar_vector)

        # Rangée 2 : dessin + édition (une seule ligne)
        toolbar_vector_tools = QHBoxLayout()
        toolbar_vector_tools.setSpacing(4)
        for w in (
            btn_draw_select, btn_draw_line, btn_draw_rect, btn_draw_ellipse, btn_draw_measure,
        ):
            toolbar_vector_tools.addWidget(w)
        sep = QWidget()
        sep.setFixedWidth(8)
        toolbar_vector_tools.addWidget(sep)
        for w in (
            btn_edit_selected, btn_rotate_selected, btn_dup_selected, btn_del_selected,
            btn_explode_path, btn_edit_nodes, btn_undo_vector, btn_redo_vector,
        ):
            toolbar_vector_tools.addWidget(w)
        toolbar_vector_tools.addStretch()
        layout_vector_editor.addLayout(toolbar_vector_tools)


        align_box = QGroupBox(tr("ui.vector_align_box"))
        align_layout = QHBoxLayout()

        btn_align_left = QPushButton(tr("ui.vector_align_left"))
        btn_align_left.clicked.connect(lambda: self.align_vector_selection("left"))
        btn_align_center_h = QPushButton(tr("ui.vector_align_center_h"))
        btn_align_center_h.clicked.connect(lambda: self.align_vector_selection("center_h"))
        btn_align_right = QPushButton(tr("ui.vector_align_right"))
        btn_align_right.clicked.connect(lambda: self.align_vector_selection("right"))
        btn_align_top = QPushButton(tr("ui.vector_align_top"))
        btn_align_top.clicked.connect(lambda: self.align_vector_selection("top"))
        btn_align_middle_v = QPushButton(tr("ui.vector_align_middle_v"))
        btn_align_middle_v.clicked.connect(lambda: self.align_vector_selection("middle_v"))
        btn_align_bottom = QPushButton(tr("ui.vector_align_bottom"))
        btn_align_bottom.clicked.connect(lambda: self.align_vector_selection("bottom"))
        btn_distribute_h = QPushButton(tr("ui.vector_distribute_h"))
        btn_distribute_h.clicked.connect(lambda: self.distribute_vector_selection("h"))
        btn_distribute_v = QPushButton(tr("ui.vector_distribute_v"))
        btn_distribute_v.clicked.connect(lambda: self.distribute_vector_selection("v"))

        for b in (btn_align_left, btn_align_center_h, btn_align_right,
                  btn_align_top, btn_align_middle_v, btn_align_bottom,
                  btn_distribute_h, btn_distribute_v):
            align_layout.addWidget(b)

        align_layout.addStretch()

        self.chk_vector_snap = QCheckBox(tr("ui.vector_snap_enable"))
        self.chk_vector_snap.toggled.connect(self.set_vector_snap_enabled)
        align_layout.addWidget(self.chk_vector_snap)
        self.spin_vector_snap_step = QDoubleSpinBox()
        self.spin_vector_snap_step.setRange(0.1, 100.0)
        self.spin_vector_snap_step.setValue(5.0)
        self.spin_vector_snap_step.setSuffix(" mm")
        self.spin_vector_snap_step.valueChanged.connect(self.set_vector_snap_step)
        align_layout.addWidget(self.spin_vector_snap_step)

        align_box.setLayout(align_layout)
        align_box.setStyleSheet("QGroupBox { padding-top: 8px; margin-top: 4px; }")
        layout_vector_editor.addWidget(align_box)


        self.vector_canvas = VectorCanvasView(self.layer_manager)
        layout_vector_editor.addWidget(self.vector_canvas, 1)  # stretch: occupe l'espace restant

        # Propriétés compactes : 1 rangée position+calque ; 1 rangée taille/ancrage (formes uniquement)
        pos_box = QGroupBox(tr("ui.selection_props_box"))
        pos_form = QVBoxLayout(pos_box)
        pos_form.setContentsMargins(8, 6, 8, 6)
        pos_form.setSpacing(4)

        pos_row1 = QHBoxLayout()
        pos_row1.setSpacing(6)
        pos_row1.addWidget(QLabel(tr("ui.vector_x_mm")))
        self.spin_vec_x = QDoubleSpinBox(); self.spin_vec_x.setRange(-1000.0, 1000.0); self.spin_vec_x.setDecimals(2)
        self.spin_vec_x.setMaximumWidth(90)
        self.spin_vec_x.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_x)
        pos_row1.addWidget(QLabel(tr("ui.vector_y_mm")))
        self.spin_vec_y = QDoubleSpinBox(); self.spin_vec_y.setRange(-1000.0, 1000.0); self.spin_vec_y.setDecimals(2)
        self.spin_vec_y.setMaximumWidth(90)
        self.spin_vec_y.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_y)
        pos_row1.addWidget(QLabel(tr("ui.vector_rotation_deg")))
        self.spin_vec_rot = QDoubleSpinBox(); self.spin_vec_rot.setRange(-360.0, 360.0); self.spin_vec_rot.setDecimals(1)
        self.spin_vec_rot.setMaximumWidth(70)
        self.spin_vec_rot.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_rot)
        pos_row1.addWidget(QLabel(tr("ui.vector_layer")))
        self.combo_vec_layer = QComboBox()
        self.combo_vec_layer.setMinimumWidth(120)
        self.combo_vec_layer.currentIndexChanged.connect(self.on_vector_layer_spin_changed)
        pos_row1.addWidget(self.combo_vec_layer, 1)
        pos_form.addLayout(pos_row1)

        # Rangée taille + ancrage (masquée pour texte / SVG)
        self.pos_size_anchor_widget = QWidget()
        pos_row_size = QHBoxLayout(self.pos_size_anchor_widget)
        pos_row_size.setContentsMargins(0, 0, 0, 0)
        pos_row_size.setSpacing(6)
        pos_row_size.addWidget(QLabel(tr("ui.vector_width_mm")))
        self.spin_vec_w = QDoubleSpinBox()
        self.spin_vec_w.setRange(0.05, 5000.0)
        self.spin_vec_w.setDecimals(2)
        self.spin_vec_w.setSuffix(" mm")
        self.spin_vec_w.setMaximumWidth(100)
        self.spin_vec_w.valueChanged.connect(self.on_vector_size_spin_changed)
        pos_row_size.addWidget(self.spin_vec_w)
        pos_row_size.addWidget(QLabel(tr("ui.vector_height_mm")))
        self.spin_vec_h = QDoubleSpinBox()
        self.spin_vec_h.setRange(0.05, 5000.0)
        self.spin_vec_h.setDecimals(2)
        self.spin_vec_h.setSuffix(" mm")
        self.spin_vec_h.setMaximumWidth(100)
        self.spin_vec_h.valueChanged.connect(self.on_vector_size_spin_changed)
        pos_row_size.addWidget(self.spin_vec_h)
        self.chk_vec_anchor_lock = QCheckBox(tr("ui.vector_anchor_lock"))
        self.chk_vec_anchor_lock.setChecked(True)
        self.chk_vec_anchor_lock.setToolTip(tr("ui.vector_anchor_lock_tip"))
        pos_row_size.addWidget(self.chk_vec_anchor_lock)
        pos_row_size.addWidget(QLabel(tr("ui.vector_anchor")))
        self.combo_vec_anchor = QComboBox()
        for aid, key in (
            ("origin", "ui.vector_anchor_origin"),
            ("bl", "ui.vector_anchor_bl"),
            ("br", "ui.vector_anchor_br"),
            ("tl", "ui.vector_anchor_tl"),
            ("tr", "ui.vector_anchor_tr"),
        ):
            self.combo_vec_anchor.addItem(tr(key), aid)
        self.combo_vec_anchor.setCurrentIndex(0)
        self.combo_vec_anchor.setToolTip(tr("ui.vector_anchor_tip"))
        pos_row_size.addWidget(self.combo_vec_anchor)
        pos_row_size.addStretch()
        self.pos_size_anchor_widget.setVisible(False)
        pos_form.addWidget(self.pos_size_anchor_widget)

        self.lbl_vector_selection = QLabel(tr("ui.no_selection_label"))
        self.lbl_vector_selection.setStyleSheet("color: #9aa3b5; font-size: 12px;")
        pos_form.addWidget(self.lbl_vector_selection)

        pos_box.setEnabled(False)
        pos_box.setVisible(False)
        self.pos_box_vector = pos_box
        layout_vector_editor.addWidget(pos_box)
        # Le canevas prend tout l'espace vertical restant
        self.vector_canvas.selection_changed.connect(self.on_vector_selection_changed)
        self.vector_canvas.object_moved.connect(self.on_vector_object_moved)
        self.vector_canvas.edit_requested.connect(self.edit_vector_object)

        self.main_tabs_view.addTab(tab_vector_editor, tr("ui.tab_vector_editor"))
        self.tab_vector_editor = tab_vector_editor
