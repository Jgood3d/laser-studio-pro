"""Construction de l'interface graphique : layout principal et onglets."""
from PyQt6.QtWidgets import (QSizePolicy, QStyle, QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox, QCheckBox, QTabWidget, QLineEdit, QDialog, QScrollArea, QSplitter)
from PyQt6.QtCore import Qt, QSettings, QSize, QUrl, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QDesktopServices
from PIL import Image
from vector_layers import (
    LayerManagerWidget, VectorCanvasView
)
from app_utils import find_resource
from i18n import tr
from app_constants import KOFI_URL
from ui.machine import MachinePanel
from ui.statusbar import StatusBar
from settings_window import SettingsWindow


class UiSetupMixin:
    def _build_tab_toolbar(self, parent, on_fullscreen, left_actions=(), left_widgets=(), right_widgets=()):
        """Barre d'outils en tête d'un onglet : `left_actions` (icône, libellé, infobulle, slot) et
        `left_widgets` à gauche, puis, alignés à droite, `right_widgets` et le bouton « Plein écran »."""
        toolbar = QToolBar(parent)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        for icon, label, tooltip, slot in left_actions:
            action = toolbar.addAction(icon, label, slot)
            if tooltip:
                action.setToolTip(tooltip)
        for widget in left_widgets:
            toolbar.addWidget(widget)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        for widget in right_widgets:
            toolbar.addWidget(widget)
        parent._fullscreen_control = toolbar.addAction(self._fullscreen_icon(), tr("ui.vector_fullscreen"),
                                                       on_fullscreen)
        return toolbar

    @staticmethod
    def _show_fullscreen_control(tab_widget, visible):
        """Masque le bouton « Plein écran » d'un onglet pendant qu'il est affiché en plein écran,
        et le réaffiche quand il revient dans les onglets (voir les fonctions *fullscreen*)."""
        control = getattr(tab_widget, "_fullscreen_control", None)
        if control is not None:
            control.setVisible(visible)

    def _fullscreen_icon(self):
        """Icône « plein écran » standard du thème (repli : bouton d'agrandissement de Qt)."""
        return QIcon.fromTheme(QIcon.ThemeIcon.ViewFullscreen,
                               self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))

    def _build_support_button(self, icon_size=40, button_size=44):
        btn = QPushButton()
        btn.setFlat(True)
        btn.setFixedSize(button_size, button_size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tr("ui.support_button_tooltip"))
        btn.setStyleSheet(
            "QPushButton { border: none; border-radius: %dpx; background-color: transparent; }"
            "QPushButton:hover { background-color: rgba(255, 221, 0, 45); }"
            % (button_size // 2)
        )
        icon_path = find_resource("buy_me_a_coffee.png")
        if icon_path:
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(icon_size, icon_size))
        else:
            btn.setText("☕")
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(KOFI_URL)))
        return btn

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.load_image_from_path(file_path)
                break
            if file_path.lower().endswith(('.svg', '.dxf')) and hasattr(self, "_import_vector_file"):
                self._import_vector_file(file_path)
                break

    def _job_in_progress(self):
        streamer = getattr(self, "streamer", None)
        try:
            return bool(streamer is not None and streamer.isRunning())
        except RuntimeError:
            return False

    def _update_bottom_panel_visibility(self, *_args):
        panel = getattr(self, "center_bottom_widget", None)
        if panel is None:
            return
        current = self.main_tabs_view.currentWidget()
        tabs_with_panel = (self.tab_vector_2d, self.tab_console_gcode, self.tab_job_queue)
        show = self._job_in_progress() or any(current is t for t in tabs_with_panel)
        if show and panel.isHidden():
            panel.setVisible(True)
            sizes = getattr(self, "_bottom_panel_sizes", None)
            if sizes:
                QTimer.singleShot(0, lambda s=sizes: self.center_v_splitter.setSizes(s))
        elif not show and not panel.isHidden():
            sizes = self.center_v_splitter.sizes()
            if all(v > 0 for v in sizes):
                self._bottom_panel_sizes = sizes
            panel.setVisible(False)

    def _image_tab_kind(self):
        """Onglet courant s'il affiche une image transformable : "previews" (Images & Tramage),
        "png2svg", "separation", ou None pour les autres onglets."""
        tabs = getattr(self, "main_tabs_view", None)
        current = tabs.currentWidget() if tabs is not None else None
        for kind in ("previews", "png2svg", "separation"):
            if current is not None and current is getattr(self, f"tab_{kind}", None):
                return kind
        return None

    def _image_tab_has_image(self, kind):
        if kind == "previews":
            return self.raw_image is not None
        if kind == "png2svg":
            return bool(self.png2svg_widget.image_path)
        if kind == "separation":
            return self.sep_src is not None
        return False

    def update_image_actions_state(self, *_args):
        """Active les actions de la barre d'outils sur l'image seulement si l'onglet courant
        affiche une image chargée. Les miroirs (miroir de gravure) restent grisés dans PNG ⇒ SVG,
        dont la conversion ne les utilise pas. Appelée au changement d'onglet, au chargement et à
        la suppression d'une image."""
        actions = getattr(self, "app_actions", None)
        if actions is None:
            return
        kind = self._image_tab_kind()
        enabled = self._image_tab_has_image(kind)
        actions.set_image_actions_enabled(enabled)
        actions.set_mirrors_enabled(enabled and kind != "png2svg")

    def _on_toolbar_rotate_image(self, clockwise):
        kind = self._image_tab_kind()
        if kind == "previews":
            (self.rotate_image_right if clockwise else self.rotate_image_left)()
        elif kind == "png2svg":
            self.png2svg_widget.rotate_image(90 if clockwise else -90)
        elif kind == "separation":
            self.separation_rotate_image(-90 if clockwise else 90)

    def _on_toolbar_delete_image(self):
        kind = self._image_tab_kind()
        if kind == "previews":
            self.clear_image()           # demande elle-même confirmation
            return
        if kind not in ("png2svg", "separation"):
            return
        reply = QMessageBox.question(
            self, tr("image.delete_title"), tr("image.delete_question"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        if kind == "png2svg":
            self.png2svg_widget.clear_image()
        else:
            self.separation_clear_image()

    def save_splitter_sizes(self, *_args):
        settings = QSettings("LaserStudioPro", "UIConfig")
        if hasattr(self, "center_v_splitter"):
            panel = getattr(self, "center_bottom_widget", None)
            if panel is not None and panel.isHidden():
                sizes = getattr(self, "_bottom_panel_sizes", None)
            else:
                sizes = self.center_v_splitter.sizes()
            if sizes and all(v > 0 for v in sizes):
                settings.setValue("center_v_splitter_sizes", sizes)

    def load_splitter_sizes(self):
        settings = QSettings("LaserStudioPro", "UIConfig")
        # Tailles de l'ancienne colonne de gauche, supprimée : plus utilisées.
        settings.remove("main_splitter_sizes")
        settings.remove("left_v_splitter_sizes")
        center_v_sizes = settings.value("center_v_splitter_sizes", None)
        if center_v_sizes and hasattr(self, "center_v_splitter"):
            try:
                loaded_sizes = [int(s) for s in center_v_sizes]
                if all(v > 0 for v in loaded_sizes):
                    self._bottom_panel_sizes = loaded_sizes
                    self.center_v_splitter.setSizes(loaded_sizes)
            except (TypeError, ValueError):
                pass

    def _toggle_fullscreen_image_tab(self):
        """Plein écran de « Graver une image ». Ses réglages (ancien onglet Image & Filtres) sont
        maintenant dans l'onglet lui-même : le plein écran commun suffit."""
        self._toggle_fullscreen_tab("tab_previews", "ui.tab_image_tracing")

    def _toggle_fullscreen_tab(self, tab_attr, title_key):
        tab_widget = getattr(self, tab_attr, None)
        if tab_widget is None:
            return
        idx = self.main_tabs_view.indexOf(tab_widget)
        if idx == -1:
            return

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.WindowType.Window)
        dialog.setWindowTitle(tr(title_key))

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(4, 4, 4, 4)

        btn_close_fullscreen = QPushButton(tr("vector.close_fullscreen"))
        btn_close_fullscreen.setStyleSheet(
            "background-color: #8f2b2b; color: white; padding: 6px; font-weight: bold;"
        )
        btn_close_fullscreen.clicked.connect(dialog.close)
        dlg_layout.addWidget(btn_close_fullscreen)

        dlg_layout.addWidget(tab_widget)
        tab_widget.setVisible(True)
        self._show_fullscreen_control(tab_widget, False)

        def restore(_result=None):
            self._show_fullscreen_control(tab_widget, True)
            dlg_layout.removeWidget(tab_widget)
            tab_widget.setParent(None)
            self.main_tabs_view.insertTab(idx, tab_widget, tr(title_key))
            self.main_tabs_view.setCurrentWidget(tab_widget)
            tab_widget.updateGeometry()
            self.main_tabs_view.update()
            self.update()
            self.repaint()

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)

    def show_status_message(self, text, tooltip=None):
        """Raccourci vers StatusBar.show_info, utilisé par les mixins et Stencil Studio."""
        self.statusBar().show_info(text, tooltip)

    def closeEvent(self, event):
        if hasattr(self, "_stop_status_poll"):
            self._stop_status_poll()
        self.save_machine_settings()
        self.save_splitter_sizes()
        reply = QMessageBox.question(
            self,
            tr("ui.quit_title"),
            tr("ui.quit_save_prompt"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Enregistrement annulé ou en échec : on reste ouvert, rien n'est perdu.
            if not self.save_project():
                event.ignore()
                return
            self._flush_background_writes()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Fermeture volontaire sans enregistrer : la sauvegarde automatique ne
            # doit pas être proposée en récupération au prochain démarrage.
            self._clear_autosave()
            self._flush_background_writes()
            event.accept()
        else:
            event.ignore()

    def _flush_background_writes(self):
        """Attend (au plus quelques secondes) la fin des sauvegardes en
        arrière-plan — file d'attente, sauvegarde automatique — avant que le
        processus ne s'arrête, sinon une écriture en cours serait perdue."""
        try:
            from app_utils import get_background_writer
            get_background_writer().wait_idle(10)
        except Exception:
            pass

    def show_settings_window(self, kind):
        """Ouvre (ou ramène au premier plan) la fenêtre « Machine & Profils » (kind="machine") ou
        « Configuration GRBL » (kind="grbl"). Créée à la première demande, puis réutilisée."""
        windows = self.__dict__.setdefault("_settings_windows", {})
        if kind not in windows:
            page, title = {
                "machine": (getattr(self, "tab_machine_profiles", None), tr("tab.machine_profiles")),
                "grbl": (getattr(self, "tab_grbl_config", None), tr("tab.grbl_config")),
                "machine_params": (getattr(self, "tab_machine_params", None), tr("tab.machine_params")),
                "test_matrix": (getattr(self, "tab_matrix", None), tr("tab.test_matrix")),
            }[kind]
            if page is None:
                return
            windows[kind] = SettingsWindow(self, title, page, kind)
        windows[kind].bring_to_front()

    def init_ui(self):
        self._build_app_menus()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Plus de colonne de gauche : les pages de réglages s'ouvrent dans des fenêtres (menu
        # Paramètres), les réglages de l'image sont dans « Graver une image », la position du job
        # dans le panneau machine. Le centre occupe toute la largeur.
        layout_machine_params = self._build_machine_params_page()
        self._build_image_settings()
        self._build_machine_profiles_page()
        self._build_test_matrix_page()
        self._build_grbl_config_page()
        self._build_layers_tab(layout_machine_params)
        self._build_legacy_svg_box()
        self.setStatusBar(StatusBar(self))

        self._last_gcode_text = None

        center_widget = QWidget()
        center_panel = QVBoxLayout(center_widget)
        center_panel.setContentsMargins(0, 0, 0, 0)
        self.main_tabs_view = QTabWidget()
        self.main_tabs_view.setMovable(True)

        self._build_image_tab()

        tab_png2svg = self._init_png2svg_tab()
        self.main_tabs_view.addTab(tab_png2svg, tr("png2svg.tab_title"))

        # --- ONGLET SÉPARATION COULEUR ---
        self.main_tabs_view.addTab(self._init_separation_tab(), tr("sep.tab_title"))

        self._build_vector_editor_tab()
        self.main_tabs_view.addTab(self.tab_layers, tr("tab.layers"))

        self._build_2d_preview_tab()
        center_bottom_scroll = self._build_machine_panel()
        center_panel.addWidget(self.center_v_splitter)

        self._build_console_tab()
        self._build_job_queue_tab()

        self.center_bottom_widget = center_bottom_scroll     # masqué / affiché selon l'onglet
        self.main_tabs_view.currentChanged.connect(self._update_bottom_panel_visibility)
        self.main_tabs_view.currentChanged.connect(self._on_main_tab_changed)
        self.main_tabs_view.currentChanged.connect(self.update_image_actions_state)
        # Onglets masqués au démarrage, ouverts à la demande depuis le menu Outils (show_main_tab).
        for tab in (self.tab_separation, self.tab_png2svg):
            self.main_tabs_view.setTabVisible(self.main_tabs_view.indexOf(tab), False)
        self._update_bottom_panel_visibility()
        self.update_image_actions_state()

        # Largeur minimale EXPLICITE du centre. Sans elle, la largeur minimale serait calculée
        # d'après le contenu : la barre d'outils de l'éditeur vectoriel (11 boutons, ~1500 px) et la
        # rangée d'alignement imposeraient environ 1500 px à la fenêtre. Trop étroit, le centre se
        # contente de serrer ses boutons.
        center_widget.setMinimumWidth(480)
        self.center_v_splitter.splitterMoved.connect(self.save_splitter_sizes)

        main_layout.addWidget(center_widget)

    def _build_machine_panel(self):
        """Panneau machine sous les onglets, abonné à la logique de la machine.

        Les sous-panneaux émettent les demandes de l'utilisateur ; la fenêtre
        les transmet aux méthodes de LaserControlMixin. La vitesse maximale
        du graveur (`spin_machine_max_speed`, qui doit déjà exister) borne le
        curseur de vitesse du pilotage. Renvoie la zone de défilement qui
        contient le panneau, placée sous les onglets dans `center_v_splitter`.
        """
        self.machine_panel = MachinePanel(
            self.job_position_box, self.spin_machine_max_speed.value()
        )
        jog = self.machine_panel.jog_panel
        jog.jog_requested.connect(self.jog_move)
        jog.home_requested.connect(self.send_homing)
        jog.pause_requested.connect(self.send_pause)
        jog.resume_requested.connect(self.send_resume)
        jog.reset_requested.connect(self.send_reset)
        jog.emergency_stop_requested.connect(self.send_kill)
        jog.send_job_requested.connect(self.send_to_laser)
        self.spin_machine_max_speed.valueChanged.connect(jog.set_max_speed)

        job_actions = self.machine_panel.job_actions_panel
        job_actions.frame_requested.connect(self.run_frame)
        job_actions.set_work_zero_requested.connect(self.set_work_zero)
        job_actions.go_to_work_zero_requested.connect(self.go_to_work_zero)
        job_actions.repeat_job_requested.connect(self.repeat_last_job)

        self.machine_panel.dro_panel.unlock_requested.connect(
            self.unlock_alarm
        )
        self.machine_panel.console_panel.command_submitted.connect(
            self.send_manual_cmd
        )
        # Commandes verrouillées tant que non connecté
        self.update_connection_widgets()

        self.main_tabs_view.setMinimumHeight(150)
        # Le panneau machine (DRO, jog, console directe) demande ~400 px.
        # Réduit plus bas avec le séparateur, il défile au lieu d'écraser ses
        # cadres jusqu'à n'en laisser que les titres.
        center_bottom_scroll = QScrollArea()
        center_bottom_scroll.setWidget(self.machine_panel)
        center_bottom_scroll.setWidgetResizable(True)
        center_bottom_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        center_bottom_scroll.setMinimumHeight(100)
        self.center_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_v_splitter.addWidget(self.main_tabs_view)
        self.center_v_splitter.addWidget(center_bottom_scroll)
        self.center_v_splitter.setStretchFactor(0, 3)
        self.center_v_splitter.setStretchFactor(1, 1)
        return center_bottom_scroll

    def _build_layers_tab(self, layout_machine_params):
        """Onglet des calques ; le cadre laser va dans `layout_machine_params`."""
        tab_layers = QWidget()
        layout_layers = QVBoxLayout(tab_layers)
        self.layer_widget = LayerManagerWidget(
            self.layer_manager,
            focal_getter=lambda: self.spin_machine_focal.value(),
        )
        self.layer_widget.layers_changed.connect(self.on_layers_changed)
        # Mémorise les réglages des calques dans le profil de la machine active.
        self.layer_widget.layers_changed.connect(self._schedule_layer_persist)
        layout_layers.addWidget(self.layer_widget)
        # Onglet central, entre « Graver une image vectorielle » et la visualisation du G-Code.
        self.tab_layers = tab_layers

        laser_box = QGroupBox(tr("ui.laser_exec_box"))
        laser_layout = QFormLayout()
        self.spin_speed_engrave = QSpinBox(laser_box); self.spin_speed_engrave.setRange(10, 20000); self.spin_speed_engrave.setValue(2000)
        self.spin_power_engrave = QSpinBox(laser_box); self.spin_power_engrave.setValue(30)

        self.combo_engrave_layer = QComboBox()
        self.combo_engrave_layer.currentIndexChanged.connect(self._on_engrave_layer_selected)
        laser_layout.addRow(tr("ui.image_layer_label"), self.combo_engrave_layer)
        laser_box.setLayout(laser_layout)
        layout_machine_params.insertWidget(layout_machine_params.count() - 1, laser_box)
        laser_box.setVisible(False)

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
        btn_fullscreen_vector.setIcon(self._fullscreen_icon())
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

    def _on_main_tab_changed(self, idx):
      if hasattr(self, 'tab_separation') and self.main_tabs_view.widget(idx) == self.tab_separation:
          self.separation_refresh_if_dirty()