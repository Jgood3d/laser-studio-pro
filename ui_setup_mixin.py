"""Construction de l'interface graphique : layout principal, onglets, menu, boîtes de dialogue « À propos »."""
from PyQt6.QtWidgets import (QPlainTextEdit, QSizePolicy, QStyle, QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QFormLayout, QMessageBox, QCheckBox, QSlider, QTabWidget, QGridLayout, QLineEdit, QProgressBar, QStackedWidget, QSplitter, QDialog, QDialogButtonBox, QListWidget, QScrollArea)
from PyQt6.QtCore import Qt, QSettings, QSize, QUrl, QTimer
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QShortcut, QKeySequence, QIcon, QDesktopServices, QPalette, QColor, QPainter, QPen
import pyqtgraph as pg
from PIL import Image
import os
from vector_layers import (
    LayerManagerWidget, VectorCanvasView
)
from graphics_view import ZoomableGraphicsView
from app_utils import get_app_dir
from app_utils import get_bundle_dir
from app_utils import find_resource
from app_utils import APP_VERSION
from i18n import tr, SUPPORTED_LANGUAGES, get_current_language, set_language
from settings_window import SettingsWindow
from widgets_extra import HistoryLineEdit, AutoHideLabel
from stencil_studio.studio_dialog import open_stencil_studio

SUPPORT_LINK_URL = "https://ko-fi.com/jb3dlaser"


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

    @staticmethod
    def _side_settings_panel(content, width=360):
        """Panneau de réglages sur le côté d'un onglet central (« Graver une image ») : largeur fixe,
        comme le panneau de l'onglet Séparation, et défilement vertical si la hauteur manque. La
        largeur s'élargit au besoin pour que le contenu tienne sans défilement horizontal."""
        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        needed = (content.minimumSizeHint().width() + scroll.verticalScrollBar().sizeHint().width()
                  + 2 * scroll.frameWidth())
        scroll.setFixedWidth(max(width, needed))
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return scroll

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
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(SUPPORT_LINK_URL)))
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
        if not getattr(self, "_image_actions", ()):
            return
        kind = self._image_tab_kind()
        enabled = self._image_tab_has_image(kind)
        for action in self._image_actions:
            action.setEnabled(enabled)
        for action in self._mirror_actions:
            action.setEnabled(enabled and kind != "png2svg")

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

    def create_slider_with_buttons(self, slider, step=5, value_formatter=None):
        layout = QHBoxLayout()
        btn_minus = QPushButton("-")
        btn_minus.setFixedWidth(30)
        btn_plus = QPushButton("+")
        btn_plus.setFixedWidth(30)

        btn_minus.clicked.connect(lambda: slider.setValue(slider.value() - step))
        btn_plus.clicked.connect(lambda: slider.setValue(slider.value() + step))

        lbl_value = QLabel()
        lbl_value.setFixedWidth(45)
        lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formatter = value_formatter or (lambda v: str(v))

        def refresh_label(v, _lbl=lbl_value, _fmt=formatter):
            _lbl.setText(_fmt(v))

        slider.valueChanged.connect(refresh_label)
        refresh_label(slider.value())

        layout.addWidget(btn_minus)
        layout.addWidget(slider)
        layout.addWidget(btn_plus)
        layout.addWidget(lbl_value)
        return layout

    def _lines_mm_row(self, spin_box):
        row_layout = QHBoxLayout()
        lbl_dpi = QLabel()
        lbl_dpi.setStyleSheet("color: #888888;")

        def refresh_dpi(value, _lbl=lbl_dpi):
            _lbl.setText(f"≈ {value * 25.4:.0f} DPI")

        spin_box.valueChanged.connect(refresh_dpi)
        refresh_dpi(spin_box.value())

        row_layout.addWidget(spin_box)
        row_layout.addWidget(lbl_dpi)
        spin_box.dpi_label = lbl_dpi
        spin_box.dpi_row_layout = row_layout
        return row_layout

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

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        # Icônes standard : celles du thème du système (freedesktop sous Linux), sinon celles du
        # style Qt, présentes sur toutes les plateformes (aucune si le style n'a pas d'équivalent).
        def std_icon(theme_icon, fallback=None):
            return QIcon.fromTheme(theme_icon, self.style().standardIcon(fallback) if fallback else QIcon())

        menu_fichier = menu_bar.addMenu(tr("menu.file"))
        self.action_save_project = action_save = menu_fichier.addAction(
            std_icon(QIcon.ThemeIcon.DocumentSave, QStyle.StandardPixmap.SP_DialogSaveButton),
            tr("menu.file.save_project"))
        action_save.setShortcut(QKeySequence.StandardKey.Save)
        action_save.triggered.connect(self.save_project)
        action_load = self.action_open_project = menu_fichier.addAction(
            std_icon(QIcon.ThemeIcon.DocumentOpen, QStyle.StandardPixmap.SP_DialogOpenButton),
            tr("menu.file.open_project"))
        action_load.setShortcut(QKeySequence.StandardKey.Open)
        action_load.triggered.connect(self.load_project)
        self.menu_recent_projects = menu_fichier.addMenu(
            std_icon(QIcon.ThemeIcon.DocumentOpenRecent, QStyle.StandardPixmap.SP_FileDialogDetailedView),
            tr("menu.file.recent_projects"))
        self._refresh_recent_projects_menu()
        menu_fichier.addSeparator()
        self.action_quit = action_quit = menu_fichier.addAction(
            std_icon(QIcon.ThemeIcon.ApplicationExit, QStyle.StandardPixmap.SP_DialogCloseButton),
            tr("menu.file.quit"))
        # StandardKey.Quit est vide sous Windows (Alt+F4 y est géré par le système) : Ctrl+Q en repli.
        action_quit.setShortcuts(QKeySequence.keyBindings(QKeySequence.StandardKey.Quit)
                                 or [QKeySequence("Ctrl+Q")])
        action_quit.triggered.connect(self.close)

        # Menu Paramètres : réglages propres à la machine (fenêtres ouvertes depuis la barre de
        # menus, ils occupaient des onglets de la colonne de gauche) et langue de l'interface.
        menu_parametres = menu_bar.addMenu(tr("menu.settings"))
        # Pas d'entrée QIcon.ThemeIcon pour ces réglages : noms d'icônes freedesktop.
        self.action_machine_params_window = menu_parametres.addAction(
            std_icon("preferences-system", QStyle.StandardPixmap.SP_ComputerIcon),
            tr("tab.machine_params"))
        self.action_machine_params_window.triggered.connect(lambda: self.show_settings_window("machine_params"))
        self.action_machine_window = menu_parametres.addAction(
            std_icon("network-wired", QStyle.StandardPixmap.SP_DriveNetIcon),
            tr("tab.machine_profiles"))
        self.action_machine_window.triggered.connect(lambda: self.show_settings_window("machine"))
        self.action_grbl_window = menu_parametres.addAction(
            std_icon("utilities-terminal", QStyle.StandardPixmap.SP_FileDialogContentsView),
            tr("tab.grbl_config"))
        self.action_grbl_window.triggered.connect(lambda: self.show_settings_window("grbl"))
        menu_parametres.addSeparator()

        menu_langue = menu_parametres.addMenu(std_icon("preferences-desktop-locale"), tr("menu.language"))
        current_lang = get_current_language()
        self._lang_actions = {}
        for lang_code, lang_label in SUPPORTED_LANGUAGES.items():
            action_lang = menu_langue.addAction(lang_label)
            action_lang.setCheckable(True)
            action_lang.setChecked(lang_code == current_lang)
            action_lang.triggered.connect(lambda checked, code=lang_code: self._on_language_selected(code))
            self._lang_actions[lang_code] = action_lang

        # Menu Outils : assistants ponctuels, hors du flux principal de préparation d'un job.
        self.tools_menu = menu_bar.addMenu(tr("menu.tools"))
        # Grille de carrés de test ; « -symbolic » : seule variante présente dans Adwaita.
        self.action_matrix_window = self.tools_menu.addAction(
            std_icon("view-grid-symbolic"), tr("tab.test_matrix"))
        self.action_matrix_window.triggered.connect(lambda: self.show_settings_window("test_matrix"))
        action_open_stencil = self.tools_menu.addAction(
            std_icon("applications-graphics"), tr("menu.tools.stencil_studio"))
        action_open_stencil.triggered.connect(lambda: open_stencil_studio(self))
        # Raccourcis vers deux onglets centraux (voir show_main_tab).
        separation_icon = QIcon.fromTheme("color-management", QIcon.fromTheme("preferences-color-symbolic"))
        vectorize_icon = QIcon.fromTheme("draw-bezier-curves", QIcon.fromTheme("image-x-generic"))
        action_separation = self.tools_menu.addAction(separation_icon, tr("sep.tab_title"))
        action_separation.triggered.connect(lambda: self.show_main_tab("tab_separation"))
        action_png2svg = self.tools_menu.addAction(vectorize_icon, tr("png2svg.tab_title"))
        action_png2svg.triggered.connect(lambda: self.show_main_tab("tab_png2svg"))

        menu_aide = menu_bar.addMenu(tr("menu.help"))
        # Version : icône de l'application (définie dans main.py, reprise par la fenêtre).
        action_version = menu_aide.addAction(self.windowIcon(), f"{tr('menu.help.version')} {APP_VERSION}")
        action_version.setEnabled(False)
        menu_aide.addSeparator()
        action_about = menu_aide.addAction(
            std_icon(QIcon.ThemeIcon.HelpAbout, QStyle.StandardPixmap.SP_MessageBoxInformation),
            tr("menu.help.about"))
        action_about.triggered.connect(self.show_about_dialog)
        # Support : contact par e-mail (voir ui.support_body).
        action_support = menu_aide.addAction(std_icon(QIcon.ThemeIcon.MailMessageNew), tr("menu.help.support"))
        action_support.triggered.connect(self.show_support_dialog)
        # Buy me a coffee : même logo que le bouton de soutien (_build_support_button).
        coffee_path = find_resource("buy_me_a_coffee.png")
        action_coffee = menu_aide.addAction(QIcon(coffee_path) if coffee_path else QIcon(), tr("menu.help.coffee"))
        action_coffee.triggered.connect(self.show_buy_me_a_coffee_dialog)

    def show_main_tab(self, tab_attr):
        """Affiche l'onglet central `tab_attr` (ex. "tab_separation"), en le rendant visible s'il était
        masqué. S'il est ouvert en plein écran (sorti des onglets), sa fenêtre est ramenée au premier plan."""
        tab = getattr(self, tab_attr, None)
        if tab is None:
            return
        index = self.main_tabs_view.indexOf(tab)
        if index != -1:
            self.main_tabs_view.setTabVisible(index, True)
            self.main_tabs_view.setCurrentWidget(tab)
        else:
            tab.window().raise_()
            tab.window().activateWindow()

    def _build_main_toolbar(self):
        """Barre d'outils sous le menu : raccourcis vers les entrées des menus Fichier, Paramètres et
        Outils (mêmes QAction : icône, libellé, raccourci et action identiques), annuler/refaire des
        réglages image, actions sur l'image chargée, puis connexion au graveur."""
        toolbar = QToolBar(tr("toolbar.main"), self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        # Icônes seules, libellé en infobulle (une entrée sans icône hors Linux affiche son libellé).
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.addAction(self.action_quit)          # même action que Fichier > Quitter (Ctrl+Q)
        toolbar.addSeparator()
        toolbar.addAction(self.action_save_project)
        toolbar.addAction(self.action_open_project)
        toolbar.addSeparator()
        toolbar.addAction(self.action_machine_params_window)
        toolbar.addAction(self.action_machine_window)
        toolbar.addAction(self.action_grbl_window)
        toolbar.addSeparator()
        for action in self.tools_menu.actions():
            toolbar.addAction(action)
        toolbar.addSeparator()
        # Annuler / refaire des réglages image (anciens boutons de l'onglet Image & Filtres). Les
        # raccourcis Ctrl+Z / Ctrl+Y restent ceux de l'onglet (QShortcut limité à l'onglet), pour ne
        # pas entrer en conflit avec l'annulation de l'Éditeur vectoriel.
        toolbar.addAction(QIcon.fromTheme(QIcon.ThemeIcon.EditUndo,
                                          self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)),
                          tr("ui.img_undo"), self.undo_image_settings)
        toolbar.addAction(QIcon.fromTheme(QIcon.ThemeIcon.EditRedo,
                                          self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)),
                          tr("ui.img_redo"), self.redo_image_settings)
        toolbar.addSeparator()
        # Image chargée (anciens boutons et cases de l'onglet Image & Filtres) : suppression,
        # rotation, puis miroirs. Les miroirs sont des actions cochables qui gardent l'état.
        # Suppression et rotation agissent sur l'image de l'onglet affiché (_image_tab_kind).
        action_delete = toolbar.addAction(
            QIcon.fromTheme(QIcon.ThemeIcon.EditDelete,
                            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)),
            tr("img.delete"), self._on_toolbar_delete_image)
        action_rotate_left = toolbar.addAction(QIcon.fromTheme(QIcon.ThemeIcon.ObjectRotateLeft),
                                               tr("img.rotate_left"),
                                               lambda: self._on_toolbar_rotate_image(clockwise=False))
        action_rotate_right = toolbar.addAction(QIcon.fromTheme(QIcon.ThemeIcon.ObjectRotateRight),
                                                tr("img.rotate_right"),
                                                lambda: self._on_toolbar_rotate_image(clockwise=True))
        # Pas d'équivalent QIcon.ThemeIcon pour les miroirs : nom d'icône freedesktop.
        flip_h_icon = QIcon.fromTheme("object-flip-horizontal")
        flip_v_icon = QIcon.fromTheme("object-flip-vertical")
        self.action_mirror_h = toolbar.addAction(flip_h_icon, tr("img.mirror_h"))
        self.action_mirror_v = toolbar.addAction(flip_v_icon, tr("img.mirror_v"))
        for action in (self.action_mirror_h, self.action_mirror_v):
            action.setCheckable(True)
            action.toggled.connect(self.update_image_processing)
        # Même action que le bouton de l'onglet Image & Filtres, toujours disponible.
        toolbar.addAction(QIcon.fromTheme(QIcon.ThemeIcon.DocumentRevert,
                                          self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)),
                          tr("img.reset"), self.reset_image_settings)
        # Activées seulement avec une image chargée, sur un onglet qui l'affiche (update_image_actions_state).
        self._image_actions = (action_delete, action_rotate_left, action_rotate_right)
        self._mirror_actions = (self.action_mirror_h, self.action_mirror_v)
        for action in self._image_actions + self._mirror_actions:
            action.setEnabled(False)
        toolbar.addSeparator()
        # G-Code (anciens boutons du bas de la colonne de gauche) : estimer, générer (bouton bleu
        # conservé tel quel, avec son libellé), importer un G-Code existant.
        estimate_icon = QIcon.fromTheme("chronometer", QIcon.fromTheme("preferences-system-time",
                                                                         QIcon.fromTheme("alarm")))
        toolbar.addAction(estimate_icon, tr("gcode.estimate"), self.estimate_job_time)
        btn_generate = QPushButton(tr("gcode.generate"))
        btn_generate.setStyleSheet("background-color: #2b5c8f; color: white; font-weight: bold; padding: 3px;")
        btn_generate.clicked.connect(self.generate_job)
        toolbar.addWidget(btn_generate)
        import_icon = QIcon.fromTheme("document-import",
                                      self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        toolbar.addAction(import_icon, tr("gcode.import"), self.import_gcode_file)
        toolbar.addSeparator()
        # Connexion au graveur : mêmes réglages que la page « Matériaux et connexion au graveur ».
        # La liste des ports partage son modèle avec celle de la page (voir combo_ports).
        self.combo_ports_toolbar = QComboBox()
        self.combo_ports_toolbar.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_ports_toolbar.setMinimumContentsLength(16)
        self.combo_ports_toolbar.setToolTip(tr("usb.port"))
        self.combo_ports_toolbar.currentTextChanged.connect(
            lambda text: self.combo_ports_toolbar.setToolTip(text or tr("usb.port")))
        toolbar.addWidget(self.combo_ports_toolbar)
        toolbar.addAction(QIcon.fromTheme(QIcon.ThemeIcon.ViewRefresh,
                                          self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)),
                          tr("usb.refresh_ports"), self.refresh_com_ports)
        self.action_connect = toolbar.addAction(tr("laser.connect"), self.toggle_usb)
        # Seul bouton avec son libellé : l'état de la connexion doit se lire d'un coup d'œil.
        toolbar.widgetForAction(self.action_connect).setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.update_connection_widgets()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self.main_toolbar = toolbar

    @staticmethod
    def _status_dot_icon(color):
        """Pastille ronde de la couleur donnée (état de la connexion)."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color).darker(140), 1))
        painter.setBrush(QColor(color))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def update_connection_widgets(self):
        """Met le bouton de connexion (page et barre d'outils) en accord avec l'état du port :
        « Déconnecter » sur fond vert / pastille verte si connecté, « Connecter GRBL » / pastille
        rouge sinon."""
        connected = self.usb.is_connected()
        label = tr("laser.disconnect") if connected else tr("laser.connect")
        button = getattr(self, "btn_connect", None)
        if button is not None:
            button.setText(label)
            button.setStyleSheet("background-color: #27ae60; color: white;" if connected else "")
        action = getattr(self, "action_connect", None)
        if action is not None:
            action.setText(label)
            action.setIcon(self._status_dot_icon("#27ae60" if connected else "#e74c3c"))

    def _on_language_selected(self, lang_code):
        set_language(lang_code)
        for code, action in self._lang_actions.items():
            action.setChecked(code == lang_code)
        QMessageBox.information(
            self, tr("menu.language.restart_title"), tr("menu.language.restart_body")
        )

    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("ui.about_title"))
        layout = QVBoxLayout(dialog)

        banner_path = find_resource("laser_studio_pro_banner.png")
        if banner_path:
            pixmap = QPixmap(banner_path)
            if not pixmap.isNull():
                lbl_banner = QLabel()
                lbl_banner.setPixmap(pixmap.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation))
                lbl_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(lbl_banner)
            else:
                lbl_banner_missing = QLabel(tr("ui.banner_unreadable").format(path=banner_path))
                lbl_banner_missing.setStyleSheet("color: #cc6666;")
                lbl_banner_missing.setWordWrap(True)
                layout.addWidget(lbl_banner_missing)
        else:
            searched = [
                os.path.join(get_app_dir(), "laser_studio_pro_banner.png"),
                os.path.join(get_bundle_dir(), "laser_studio_pro_banner.png"),
            ]
            searched_txt = "\n".join(sorted(set(searched)))
            lbl_banner_missing = QLabel(tr("ui.banner_missing").format(paths=searched_txt))
            lbl_banner_missing.setStyleSheet("color: #cc6666;")
            lbl_banner_missing.setWordWrap(True)
            layout.addWidget(lbl_banner_missing)

        lbl_text = QLabel(
            f"<b>Laser Studio Pro</b> — {tr('menu.help.version')} {APP_VERSION}<br>"
            + tr("dialog.about.description")
        )
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        layout.addWidget(lbl_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def show_support_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("ui.support_title"))
        layout = QVBoxLayout(dialog)

        lbl_text = QLabel(tr("ui.support_body"))
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        lbl_text.setOpenExternalLinks(True)
        lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(lbl_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def show_buy_me_a_coffee_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("ui.coffee_title"))
        layout = QVBoxLayout(dialog)

        lbl_text = QLabel(
            tr("ui.coffee_body").format(
                link="<a href=\"https://ko-fi.com/jb3dlaser\">"
                     "ko-fi.com/jb3dlaser</a>"
            )
        )
        lbl_text.setTextFormat(Qt.TextFormat.RichText)
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_text.setWordWrap(True)
        lbl_text.setOpenExternalLinks(True)
        lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(lbl_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def init_ui(self):
        self._build_menu_bar()
        self._build_main_toolbar()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Plus de colonne de gauche : les pages de réglages s'ouvrent dans des fenêtres (menu
        # Paramètres), les réglages de l'image sont dans « Graver une image », la position du job
        # dans le panneau machine. Le centre occupe toute la largeur.
        tab_machine_params_content = QWidget()
        layout_machine_params = QVBoxLayout(tab_machine_params_content)

        machine_profiles_box = QGroupBox(tr("mach.profiles_box"))
        machine_profiles_layout = QVBoxLayout()
        self.combo_machine_profile = QComboBox()
        self.combo_machine_profile.currentIndexChanged.connect(self._on_machine_profile_selected)
        machine_profiles_layout.addWidget(self.combo_machine_profile)
        profile_btn_row = QHBoxLayout()
        btn_new_machine = QPushButton(tr("mach.new_machine"))
        btn_new_machine.clicked.connect(self._add_machine_profile)
        btn_update_machine = QPushButton(tr("mach.update"))
        btn_update_machine.clicked.connect(self._update_machine_profile)
        btn_del_machine = QPushButton(tr("mach.delete"))
        btn_del_machine.clicked.connect(self._delete_machine_profile)
        profile_btn_row.addWidget(btn_new_machine)
        profile_btn_row.addWidget(btn_update_machine)
        profile_btn_row.addWidget(btn_del_machine)
        machine_profiles_layout.addLayout(profile_btn_row)
        lbl_profile_info = QLabel(tr("mach.profile_info"))
        lbl_profile_info.setWordWrap(True)
        machine_profiles_layout.addWidget(lbl_profile_info)
        machine_profiles_box.setLayout(machine_profiles_layout)
        layout_machine_params.addWidget(machine_profiles_box)

        machine_bed_box = QGroupBox(tr("mach.bed_box"))
        machine_bed_layout = QFormLayout()
        self.spin_machine_w = QDoubleSpinBox(); self.spin_machine_w.setRange(1.0, 5000.0); self.spin_machine_w.setValue(300.0)
        self.spin_machine_w.setSuffix(" mm")
        self.spin_machine_w.valueChanged.connect(self.update_vector_work_area)
        self.spin_machine_h = QDoubleSpinBox(); self.spin_machine_h.setRange(1.0, 5000.0); self.spin_machine_h.setValue(200.0)
        self.spin_machine_h.setSuffix(" mm")
        self.spin_machine_h.valueChanged.connect(self.update_vector_work_area)
        machine_bed_layout.addRow(tr("mach.bed_w"), self.spin_machine_w)
        machine_bed_layout.addRow(tr("mach.bed_h"), self.spin_machine_h)
        lbl_machine_info = QLabel(tr("mach.bed_info"))
        lbl_machine_info.setWordWrap(True)
        machine_bed_layout.addRow(lbl_machine_info)
        machine_bed_box.setLayout(machine_bed_layout)
        layout_machine_params.addWidget(machine_bed_box)

        machine_laser_box = QGroupBox(tr("mach.laser_box"))
        machine_laser_layout = QFormLayout()
        self.spin_machine_focal = QDoubleSpinBox()
        self.spin_machine_focal.setRange(0.01, 2.0)
        self.spin_machine_focal.setSingleStep(0.01)
        self.spin_machine_focal.setDecimals(3)
        self.spin_machine_focal.setValue(0.10)
        self.spin_machine_focal.setSuffix(" mm")
        self.spin_machine_focal.valueChanged.connect(self._on_machine_focal_changed)
        machine_laser_layout.addRow(tr("mach.focal_size"), self.spin_machine_focal)
        lbl_focal_help = QLabel(tr("mach.focal_help"))
        lbl_focal_help.setWordWrap(True)
        machine_laser_layout.addRow(lbl_focal_help)
        machine_laser_box.setLayout(machine_laser_layout)
        layout_machine_params.addWidget(machine_laser_box)

        machine_limits_box = QGroupBox(tr("mach.limits_box"))
        machine_limits_layout = QFormLayout()
        self.spin_machine_max_speed = QDoubleSpinBox()
        self.spin_machine_max_speed.setRange(1.0, 50000.0)
        self.spin_machine_max_speed.setValue(6000.0)
        self.spin_machine_max_speed.setSuffix(" mm/min")
        self.spin_machine_accel = QDoubleSpinBox()
        self.spin_machine_accel.setRange(1.0, 20000.0)
        self.spin_machine_accel.setValue(500.0)
        self.spin_machine_accel.setSuffix(" mm/s²")
        machine_limits_layout.addRow(tr("mach.max_speed"), self.spin_machine_max_speed)
        machine_limits_layout.addRow(tr("mach.accel"), self.spin_machine_accel)
        lbl_limits_info = QLabel(tr("mach.limits_info"))
        lbl_limits_info.setWordWrap(True)
        machine_limits_layout.addRow(lbl_limits_info)
        machine_limits_box.setLayout(machine_limits_layout)
        layout_machine_params.addWidget(machine_limits_box)
        layout_machine_params.addStretch()

        tab_machine_params = QScrollArea()
        tab_machine_params.setWidget(tab_machine_params_content)
        tab_machine_params.setWidgetResizable(True)
        tab_machine_params.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tab_machine_params = tab_machine_params     # affichée dans une fenêtre du menu (show_settings_window)

        tab_img = QWidget()
        layout_img = QFormLayout(tab_img)

        btn_img = QPushButton(tr("img.load"))
        btn_img.clicked.connect(self.load_image)
        layout_img.addRow(btn_img)                 # toute la largeur du panneau


        self.slider_bright = QSlider(Qt.Orientation.Horizontal); self.slider_bright.setRange(-100, 100); self.slider_bright.setValue(0)
        self.slider_bright.valueChanged.connect(self.update_image_processing)
        
        self.slider_contrast = QSlider(Qt.Orientation.Horizontal); self.slider_contrast.setRange(-100, 100); self.slider_contrast.setValue(0)
        self.slider_contrast.valueChanged.connect(self.update_image_processing)
        
        self.slider_gamma = QSlider(Qt.Orientation.Horizontal); self.slider_gamma.setRange(10, 300); self.slider_gamma.setValue(100)
        self.slider_gamma.valueChanged.connect(self.update_image_processing)
        self.slider_sharp = QSlider(Qt.Orientation.Horizontal); self.slider_sharp.setRange(0, 100); self.slider_sharp.setValue(0)
        self.slider_sharp.setToolTip(tr("img.sharpness_tip"))
        self.slider_sharp.valueChanged.connect(self.update_image_processing)

        self.chk_invert = QCheckBox(tr("img.invert"))
        self.chk_invert.stateChanged.connect(self.update_image_processing)

        # Sélecteur de matière : se contente de cocher/décocher « Inverser
        # Couleurs » (la case reste modifiable à la main). Le miroir reste
        # indépendant.
        self.combo_material_bg = QComboBox()
        self.combo_material_bg.addItem(tr("img.bg_dark"), "dark")
        self.combo_material_bg.addItem(tr("img.bg_light"), "light")
        self.combo_material_bg.setCurrentIndex(1)  # fond clair = négatif désactivé (comportement historique)
        self.combo_material_bg.setToolTip(tr("img.material_bg_tooltip"))
        # Les libellés sont longs (exemples de matières : 62 caractères en français, 85 en allemand).
        # Par défaut, une liste déroulante prend la largeur de son élément le PLUS LONG comme largeur
        # minimale : la colonne de gauche ne pouvait plus être rétrécie avec le séparateur. On fixe donc
        # une largeur minimale courte ; la liste ouverte, elle, reste assez large pour tout lire.
        self.combo_material_bg.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_material_bg.setMinimumContentsLength(12)
        for i in range(self.combo_material_bg.count()):
            self.combo_material_bg.setItemData(i, self.combo_material_bg.itemText(i), Qt.ItemDataRole.ToolTipRole)
        _popup = self.combo_material_bg.view()
        _popup.setMinimumWidth(_popup.sizeHintForColumn(0) + 24)
        self.combo_material_bg.currentIndexChanged.connect(self._on_material_bg_changed)

        shortcut_undo_img = QShortcut(QKeySequence.StandardKey.Undo, tab_img)
        shortcut_undo_img.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut_undo_img.activated.connect(self.undo_image_settings)
        shortcut_redo_img = QShortcut(QKeySequence.StandardKey.Redo, tab_img)
        shortcut_redo_img.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut_redo_img.activated.connect(self.redo_image_settings)

        self.combo_algo = QComboBox()
        self.combo_algo.addItems([
            "Floyd-Steinberg", "Jarvis, Judice & Ninke", "Stucki", "Atkinson",
            "Sierra", "Sierra Lite (rapide)", "Burkes",
            "Bayer 2x2 (ordonné)", "Bayer 4x4 (ordonné)", "Bayer 8x8 (ordonné)",
            "Seuil Simple (Binaire)", "Niveaux de Gris"
        ])
        self.combo_algo.currentIndexChanged.connect(self.update_image_processing)

        self.spin_lmm = QDoubleSpinBox(); self.spin_lmm.setRange(1.0, 50.0); self.spin_lmm.setValue(10.0)
        self.spin_lmm.valueChanged.connect(self.update_image_processing)
        self.spin_lmm.valueChanged.connect(self._sync_dpi_and_quality_from_lmm)

        self.combo_lmm_mode = QComboBox()
        self.combo_lmm_mode.addItems([tr("img.mode_lmm"), "DPI", tr("img.mode_focal")])
        self.combo_lmm_mode.currentIndexChanged.connect(self.on_lmm_mode_changed)

        self.spin_dpi = QDoubleSpinBox()
        self.spin_dpi.setRange(10.0, 2000.0)
        self.spin_dpi.setDecimals(0)
        self.spin_dpi.setValue(254.0)
        self.spin_dpi.setSuffix(" DPI")
        self.spin_dpi.valueChanged.connect(self.on_dpi_value_changed)

        self.lbl_focal_info = QLabel()
        self.lbl_focal_info.setStyleSheet("color: #888888;")
        btn_configure_focal = QPushButton(tr("img.configure_focal"))
        btn_configure_focal.clicked.connect(self.goto_laser_focal_settings)

        self.stack_lmm_input = QStackedWidget()
        # Hauteur de son contenu, sans s'étirer : sinon la place libre de l'onglet allait dans la pile
        # et écartait la liste « Résolution », le champ DPI et « Enregistrer comme focale ».
        self.stack_lmm_input.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        btn_save_focal_lmm = QPushButton(tr("img.save_as_focal"))
        btn_save_focal_lmm.clicked.connect(self.save_current_lmm_as_focal)
        page_lmm = QWidget()
        page_lmm_layout = QVBoxLayout(page_lmm)
        page_lmm_layout.setContentsMargins(0, 0, 0, 0)
        page_lmm_layout.addWidget(self.spin_lmm)
        page_lmm_layout.addWidget(btn_save_focal_lmm)
        self.stack_lmm_input.addWidget(page_lmm)

        btn_save_focal_dpi = QPushButton(tr("img.save_as_focal"))
        btn_save_focal_dpi.clicked.connect(self.save_current_lmm_as_focal)
        page_dpi = QWidget()
        page_dpi_layout = QVBoxLayout(page_dpi)
        page_dpi_layout.setContentsMargins(0, 0, 0, 0)
        page_dpi_layout.addWidget(self.spin_dpi)
        page_dpi_layout.addWidget(btn_save_focal_dpi)
        self.stack_lmm_input.addWidget(page_dpi)

        page_focal = QWidget()
        page_focal_layout = QVBoxLayout(page_focal)
        page_focal_layout.setContentsMargins(0, 0, 0, 0)
        page_focal_layout.addWidget(self.lbl_focal_info)
        page_focal_layout.addWidget(btn_configure_focal)
        self.stack_lmm_input.addWidget(page_focal)

        self.lbl_resolution_quality = AutoHideLabel()
        self.lbl_resolution_quality.setWordWrap(True)

        layout_img.addRow(tr("img.brightness"), self.create_slider_with_buttons(self.slider_bright, step=5))
        layout_img.addRow(tr("img.contrast"), self.create_slider_with_buttons(self.slider_contrast, step=5))
        layout_img.addRow(tr("img.gamma"), self.create_slider_with_buttons(
            self.slider_gamma, step=10, value_formatter=lambda v: f"{v / 100.0:.2f}"
        ))
        layout_img.addRow(tr("img.sharpness"), self.create_slider_with_buttons(self.slider_sharp, step=5))
        layout_img.addRow(tr("img.material_bg"), self.combo_material_bg)
        layout_img.addRow("", self.chk_invert)
        layout_img.addRow(tr("img.algorithm"), self.combo_algo)
        layout_img.addRow(tr("img.resolution"), self.combo_lmm_mode)
        layout_img.addRow("", self.stack_lmm_input)
        layout_img.addRow("", self.lbl_resolution_quality)

        self.combo_lmm_mode.setCurrentIndex(2)
        self.on_lmm_mode_changed(2)

        # Réglages de l'image : panneau de gauche de l'onglet central « Graver une image ».
        self.tab_img = tab_img

        self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(0.1, 2000.0); self.spin_w.setValue(100.0)
        self.spin_w.valueChanged.connect(lambda v: self.on_dimension_changed('w', v))
        self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(0.1, 2000.0); self.spin_h.setValue(100.0)
        self.spin_h.valueChanged.connect(lambda v: self.on_dimension_changed('h', v))
        self.chk_keep_ratio = QCheckBox(tr("dim.keep_ratio")); self.chk_keep_ratio.setChecked(True)

        self.combo_origin = QComboBox()
        self.combo_origin.addItems([tr("ui.origin_bottom_left"), tr("ui.origin_center")])
        self.spin_off_x = QDoubleSpinBox(); self.spin_off_x.setRange(-1000.0, 1000.0); self.spin_off_x.setValue(0.0)
        self.spin_off_y = QDoubleSpinBox(); self.spin_off_y.setRange(-1000.0, 1000.0); self.spin_off_y.setValue(0.0)

        # Taille de l'image : en haut des réglages de « Graver une image », sous « Charger Image ».
        layout_img.insertRow(1, tr("dim.width"), self.spin_w)
        layout_img.insertRow(2, tr("dim.height"), self.spin_h)
        layout_img.insertRow(3, self.chk_keep_ratio)          # toute la largeur du panneau

        # Position du job sur le plateau (image ET vecteurs, voir workers.AdvancedGCodeWorker) :
        # dans le panneau machine, avec le jog et le cadrage qui servent à la régler.
        self.job_position_box = QGroupBox(tr("ui.job_position_box"))
        job_position_layout = QHBoxLayout(self.job_position_box)
        job_position_layout.addWidget(QLabel(tr("dim.origin")))
        job_position_layout.addWidget(self.combo_origin)
        job_position_layout.addSpacing(12)
        job_position_layout.addWidget(QLabel(tr("dim.offset_x")))
        job_position_layout.addWidget(self.spin_off_x)
        job_position_layout.addSpacing(12)
        job_position_layout.addWidget(QLabel(tr("dim.offset_y")))
        job_position_layout.addWidget(self.spin_off_y)
        job_position_layout.addStretch()

        tab_mach = QWidget()
        layout_mach = QVBoxLayout(tab_mach)

        usb_box = QGroupBox(tr("usb.box_title"))
        usb_layout = QFormLayout()
        self.combo_ports = QComboBox()
        # Même liste que le sélecteur de la barre d'outils (modèle partagé) et même port choisi.
        self.combo_ports.setModel(self.combo_ports_toolbar.model())
        self.combo_ports.currentIndexChanged.connect(self.combo_ports_toolbar.setCurrentIndex)
        self.combo_ports_toolbar.currentIndexChanged.connect(self.combo_ports.setCurrentIndex)
        btn_refresh = QPushButton(tr("usb.refresh_ports"))
        btn_refresh.clicked.connect(self.refresh_com_ports)
        self.btn_connect = QPushButton(tr("usb.connect"))
        self.btn_connect.clicked.connect(self.toggle_usb)
        usb_layout.addRow(tr("usb.port"), self.combo_ports)
        usb_layout.addRow("", btn_refresh)
        usb_layout.addRow("", self.btn_connect)

        lbl_driver_hint = QLabel(tr("usb.driver_hint"))
        lbl_driver_hint.setTextFormat(Qt.TextFormat.RichText)
        lbl_driver_hint.setOpenExternalLinks(True)
        lbl_driver_hint.setWordWrap(True)
        lbl_driver_hint.setStyleSheet("color: #888888;")
        hint_palette = lbl_driver_hint.palette()
        hint_palette.setColor(QPalette.ColorRole.Link, QColor("#5aa9ff"))
        lbl_driver_hint.setPalette(hint_palette)
        usb_layout.addRow(lbl_driver_hint)
        usb_box.setLayout(usb_layout)
        layout_mach.addWidget(usb_box)

        mat_box = QGroupBox(tr("material.box_title"))
        mat_layout = QFormLayout()
        self.combo_mat = QComboBox()
        self.combo_mat.addItems(list(self.materials_db.keys()))
        self.combo_mat.currentIndexChanged.connect(self.apply_material_profile)

        btn_save_mat = QPushButton(tr("material.save"))
        btn_save_mat.clicked.connect(self.save_material_profile)
        btn_add_mat = QPushButton(tr("material.new"))
        btn_add_mat.clicked.connect(self.add_material_profile)
        btn_del_mat = QPushButton(tr("material.delete"))
        btn_del_mat.clicked.connect(self.delete_material_profile)
        btn_export_mat = QPushButton(tr("material.export"))
        btn_export_mat.clicked.connect(self.export_material_profiles)
        btn_import_mat = QPushButton(tr("material.import"))
        btn_import_mat.clicked.connect(self.import_material_profiles)

        mat_layout.addRow(tr("material.select"), self.combo_mat)
        mat_layout.addRow("", btn_save_mat)
        mat_layout.addRow("", btn_add_mat)
        mat_layout.addRow("", btn_del_mat)
        mat_layout.addRow("", btn_export_mat)
        mat_layout.addRow("", btn_import_mat)
        mat_box.setLayout(mat_layout)
        layout_mach.addWidget(mat_box)
        layout_mach.addStretch()
        # Page affichée dans une fenêtre du menu (voir show_settings_window), plus dans un onglet.
        self.tab_machine_profiles = tab_mach

        tab_matrix = QWidget()
        self.form_matrix = QFormLayout(tab_matrix)

        self.combo_mat_mode = QComboBox()
        self.combo_mat_mode.addItems([
            tr("ui.material_mode_engraving"),
            tr("ui.material_mode_cutting"),
        ])
        self.combo_mat_mode.currentIndexChanged.connect(self.on_mat_mode_changed)

        self.spin_mat_off_x = QDoubleSpinBox(); self.spin_mat_off_x.setRange(-1000.0, 1000.0); self.spin_mat_off_x.setValue(0.0)
        self.spin_mat_off_y = QDoubleSpinBox(); self.spin_mat_off_y.setRange(-1000.0, 1000.0); self.spin_mat_off_y.setValue(0.0)

        self.lbl_mat_p1 = QLabel(tr("ui.mat_min_power"))
        self.spin_mat_min_p = QSpinBox(); self.spin_mat_min_p.setRange(5, 100); self.spin_mat_min_p.setValue(10)
        
        self.spin_mat_max_p = QSpinBox(); self.spin_mat_max_p.setRange(5, 100); self.spin_mat_max_p.setValue(80)
        self.spin_mat_steps_p = QSpinBox(); self.spin_mat_steps_p.setRange(2, 20); self.spin_mat_steps_p.setValue(5)

        self.spin_mat_min_passes = QSpinBox(); self.spin_mat_min_passes.setRange(1, 20); self.spin_mat_min_passes.setValue(1)
        self.spin_mat_max_passes = QSpinBox(); self.spin_mat_max_passes.setRange(1, 20); self.spin_mat_max_passes.setValue(5)
        self.spin_mat_steps_passes = QSpinBox(); self.spin_mat_steps_passes.setRange(2, 20); self.spin_mat_steps_passes.setValue(5)

        self.spin_mat_min_s = QSpinBox(); self.spin_mat_min_s.setRange(100, 20000); self.spin_mat_min_s.setValue(1000)
        self.spin_mat_max_s = QSpinBox(); self.spin_mat_max_s.setRange(100, 20000); self.spin_mat_max_s.setValue(5000)
        self.spin_mat_steps_s = QSpinBox(); self.spin_mat_steps_s.setRange(2, 20); self.spin_mat_steps_s.setValue(5)

        self.spin_mat_size = QDoubleSpinBox(); self.spin_mat_size.setRange(2.0, 50.0); self.spin_mat_size.setValue(10.0)
        self.spin_mat_gap = QDoubleSpinBox(); self.spin_mat_gap.setRange(0.5, 20.0); self.spin_mat_gap.setValue(3.0)
        
        self.spin_mat_lmm = QDoubleSpinBox(); self.spin_mat_lmm.setRange(1.0, 50.0); self.spin_mat_lmm.setValue(self.spin_lmm.value())
        self.spin_mat_lmm.setEnabled(False)
        self.spin_mat_lmm.setToolTip(tr("ui.mat_lmm_auto_tooltip"))

        self.combo_mat_laser_cmd = QComboBox()
        self.combo_mat_laser_cmd.addItems(["M4 (Dynamic Power)", "M3 (Constant Power)"])

        self.chk_mat_homing = QCheckBox(tr("ui.mat_homing"))
        self.chk_mat_homing.setChecked(False)

        btn_gen_matrix = QPushButton(tr("ui.gen_test_matrix"))
        btn_gen_matrix.setStyleSheet("background-color: #d35400; color: white; font-weight: bold; padding: 6px;")
        btn_gen_matrix.clicked.connect(self.generate_test_matrix)

        self.form_matrix.addRow(tr("ui.test_mode"), self.combo_mat_mode)
        self.form_matrix.addRow(tr("ui.mat_offset_x"), self.spin_mat_off_x)
        self.form_matrix.addRow(tr("ui.mat_offset_y"), self.spin_mat_off_y)
        self.form_matrix.addRow(self.lbl_mat_p1, self.spin_mat_min_p)
        self.form_matrix.addRow(tr("ui.mat_max_power"), self.spin_mat_max_p)
        self.form_matrix.addRow(tr("ui.mat_power_step"), self.spin_mat_steps_p)
        self.form_matrix.addRow(tr("ui.mat_min_passes"), self.spin_mat_min_passes)
        self.form_matrix.addRow(tr("ui.mat_max_passes"), self.spin_mat_max_passes)
        self.form_matrix.addRow(tr("ui.mat_passes_step"), self.spin_mat_steps_passes)
        self.form_matrix.addRow(tr("ui.mat_min_speed"), self.spin_mat_min_s)
        self.form_matrix.addRow(tr("ui.mat_max_speed"), self.spin_mat_max_s)
        self.form_matrix.addRow(tr("ui.mat_speed_step"), self.spin_mat_steps_s)
        self.form_matrix.addRow(tr("ui.mat_square_size"), self.spin_mat_size)
        self.form_matrix.addRow(tr("ui.mat_spacing"), self.spin_mat_gap)
        self.form_matrix.addRow(tr("ui.mat_lmm"), self._lines_mm_row(self.spin_mat_lmm))
        self.form_matrix.addRow(tr("ui.mat_laser_cmd"), self.combo_mat_laser_cmd)
        self.form_matrix.addRow("", self.chk_mat_homing)
        self.form_matrix.addRow("", btn_gen_matrix)
        self.tab_matrix = tab_matrix                      # affichée dans une fenêtre du menu (show_settings_window)

        self.on_mat_mode_changed(0)

        tab_gcode_cfg = QWidget()
        layout_gcode_cfg = QFormLayout(tab_gcode_cfg)

        self.combo_laser_cmd = QComboBox()
        self.combo_laser_cmd.addItems(["M4 (Dynamic Power)", "M3 (Constant Power)"])
        self.spin_smax = QSpinBox(); self.spin_smax.setRange(1, 10000); self.spin_smax.setValue(1000)
        self.chk_homing = QCheckBox(tr("ui.grbl_homing")); self.chk_homing.setChecked(True)   # homing automatique au démarrage du job : activé d'office
        self.chk_overscan = QCheckBox(tr("ui.overscan_enabled")); self.chk_overscan.setChecked(True)

        self.combo_overscan_mode = QComboBox()
        self.combo_overscan_mode.addItems([tr("ui.overscan_mode_fixed"), tr("ui.overscan_mode_pct")])
        self.combo_overscan_mode.currentIndexChanged.connect(self.on_overscan_mode_changed)

        self.spin_overscan_dist = QDoubleSpinBox()
        self.spin_overscan_dist.setRange(0.0, 50.0)
        self.spin_overscan_dist.setSingleStep(0.1)
        self.spin_overscan_dist.setDecimals(1)
        self.spin_overscan_dist.setValue(2.5)
        self.spin_overscan_dist.setSuffix(" mm")

        self.spin_overscan_pct = QDoubleSpinBox()
        self.spin_overscan_pct.setRange(0.0, 50.0)
        self.spin_overscan_pct.setSingleStep(0.1)
        self.spin_overscan_pct.setDecimals(1)
        self.spin_overscan_pct.setValue(5.0)
        self.spin_overscan_pct.setSuffix(" %")

        self.overscan_stacked = QStackedWidget()
        self.overscan_stacked.addWidget(self.spin_overscan_dist)
        self.overscan_stacked.addWidget(self.spin_overscan_pct)
        self.overscan_stacked.setFixedHeight(28)

        self.txt_start_gcode = QTextEdit()
        self.txt_start_gcode.setMaximumHeight(45)
        self.txt_start_gcode.setPlainText("G21 ; Unités mm\nG90 ; Absolu")

        self.txt_end_gcode = QTextEdit()
        self.txt_end_gcode.setMaximumHeight(45)
        self.txt_end_gcode.setPlainText("M5 ; Extinction Laser\nG0 X0 Y0 ; Retour origine")

        layout_gcode_cfg.addRow(tr("ui.gcode_laser_cmd"), self.combo_laser_cmd)
        layout_gcode_cfg.addRow(tr("ui.gcode_smax"), self.spin_smax)
        layout_gcode_cfg.addRow("", self.chk_homing)
        layout_gcode_cfg.addRow("", self.chk_overscan)
        self.chk_safe_cut_order = QCheckBox(tr("ui.safe_cut_order"))
        self.chk_safe_cut_order.setChecked(True)
        self.chk_safe_cut_order.setToolTip(tr("ui.safe_cut_order_tip"))
        layout_gcode_cfg.addRow("", self.chk_safe_cut_order)
        layout_gcode_cfg.addRow(tr("ui.overscan_mode_label"), self.combo_overscan_mode)
        layout_gcode_cfg.addRow(tr("ui.overscan_value_label"), self.overscan_stacked)

        # Décalage aller/retour : compense le jeu mécanique et le délai d'allumage du laser
        # entre les lignes gravées dans un sens et dans l'autre (propre à la machine).
        self.spin_scan_offset = QDoubleSpinBox()
        self.spin_scan_offset.setRange(-2.0, 2.0)
        self.spin_scan_offset.setSingleStep(0.01)
        self.spin_scan_offset.setDecimals(2)
        self.spin_scan_offset.setValue(0.0)
        self.spin_scan_offset.setSuffix(" mm")
        self.spin_scan_offset.setToolTip(tr("ui.scan_offset_tip"))
        btn_bidir_test = QPushButton(tr("ui.bidir_test_btn"))
        btn_bidir_test.setToolTip(tr("ui.scan_offset_tip"))
        btn_bidir_test.clicked.connect(self.generate_bidir_test)
        self.spin_scan_offset.valueChanged.connect(self._schedule_layer_persist)   # mémorisé dans le profil de la machine
        layout_gcode_cfg.addRow(tr("ui.scan_offset_label"), self.spin_scan_offset)
        layout_gcode_cfg.addRow("", btn_bidir_test)
        layout_gcode_cfg.addRow(tr("ui.gcode_start"), self.txt_start_gcode)
        layout_gcode_cfg.addRow(tr("ui.gcode_end"), self.txt_end_gcode)

        grbl_settings_box = QGroupBox(tr("ui.grbl_settings_box"))
        grbl_settings_layout = QVBoxLayout()

        self.txt_grbl_settings = QTextEdit()
        self.txt_grbl_settings.setPlaceholderText(tr("ui.grbl_settings_placeholder"))
        self.txt_grbl_settings.setMaximumHeight(140)
        self.txt_grbl_settings.setStyleSheet("font-family: monospace;")
        grbl_settings_layout.addWidget(self.txt_grbl_settings)

        grbl_settings_btn_row = QHBoxLayout()
        btn_grbl_read = QPushButton(tr("ui.grbl_read"))
        btn_grbl_read.clicked.connect(self.read_grbl_settings)
        btn_grbl_send = QPushButton(tr("ui.grbl_send"))
        btn_grbl_send.clicked.connect(self.send_grbl_settings)
        btn_grbl_export = QPushButton(tr("ui.grbl_export"))
        btn_grbl_export.clicked.connect(self.export_grbl_settings)
        btn_grbl_import = QPushButton(tr("ui.grbl_import"))
        btn_grbl_import.clicked.connect(self.import_grbl_settings)
        for b in (btn_grbl_read, btn_grbl_send, btn_grbl_export, btn_grbl_import):
            grbl_settings_btn_row.addWidget(b)
        grbl_settings_layout.addLayout(grbl_settings_btn_row)

        btn_grbl_link_profile = QPushButton(tr("ui.grbl_link_profile"))
        btn_grbl_link_profile.clicked.connect(self.save_grbl_settings_to_profile)
        grbl_settings_layout.addWidget(btn_grbl_link_profile)

        grbl_settings_box.setLayout(grbl_settings_layout)
        layout_gcode_cfg.addRow(grbl_settings_box)

        # Page affichée dans une fenêtre du menu (voir show_settings_window), plus dans un onglet.
        self.tab_grbl_config = tab_gcode_cfg

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

        legacy_svg_box = QGroupBox(tr("ui.svg_legacy_title"))
        legacy_svg_layout = QFormLayout()
        lbl_legacy_info = QLabel(
            "⚠ Ce mode charge un SVG entier avec UN SEUL réglage de puissance/vitesse,\n"
            "sans aperçu ni possibilité de mélanger découpe et gravure sur un même fichier.\n"
            "Préfère plutôt 'Importer SVG (multi-calques)' dans l'Éditeur Vectoriel, qui\n"
            "décompose le SVG en objets indépendants assignables à des calques différents,\n"
            "avec aperçu visuel. Conservé ici uniquement pour compatibilité."
        )
        lbl_legacy_info.setWordWrap(True)
        legacy_svg_layout.addRow(lbl_legacy_info)

        btn_svg = QPushButton(tr("ui.load_svg_legacy"))
        btn_svg.clicked.connect(self.load_svg)

        self.chk_enable_cut = QCheckBox(tr("ui.enable_cut"))
        self.chk_enable_cut.setChecked(False)

        self.spin_speed_cut = QSpinBox(); self.spin_speed_cut.setRange(10, 5000); self.spin_speed_cut.setValue(300)
        self.spin_power_cut = QSpinBox(); self.spin_power_cut.setValue(90)
        self.spin_passes_cut = QSpinBox(); self.spin_passes_cut.setValue(2)

        legacy_svg_layout.addRow(tr("ui.vector_file_label"), btn_svg)
        legacy_svg_layout.addRow("", self.chk_enable_cut)
        legacy_svg_layout.addRow(tr("ui.cut_speed"), self.spin_speed_cut)
        legacy_svg_layout.addRow(tr("ui.cut_power"), self.spin_power_cut)
        legacy_svg_layout.addRow(tr("ui.cut_passes"), self.spin_passes_cut)
        legacy_svg_box.setLayout(legacy_svg_layout)

        # Ancien mode SVG, conservé pour compatibilité mais jamais affiché : gardé en vie ici (ses
        # champs sont encore lus par la génération).
        legacy_svg_box.setVisible(False)
        self.legacy_svg_box = legacy_svg_box

        self.lbl_gen_progress_main = AutoHideLabel("")
        self.gen_progress_bar_main = QProgressBar()
        self.gen_progress_bar_main.setRange(0, 100)
        self.gen_progress_bar_main.setValue(0)
        self.gen_progress_bar_main.setVisible(False)
        self.gen_progress_bar_main.setMaximumHeight(16)
        # Progression de la génération : dans la barre d'état, en bas de la fenêtre.
        self.statusBar().addWidget(self.lbl_gen_progress_main)
        self.statusBar().addWidget(self.gen_progress_bar_main, 1)


        self._last_gcode_text = None


        center_widget = QWidget()
        center_panel = QVBoxLayout(center_widget)
        center_panel.setContentsMargins(0, 0, 0, 0)
        self.main_tabs_view = QTabWidget()
        self.main_tabs_view.setMovable(True)

        tab_previews = QWidget()
        outer_layout_previews = QVBoxLayout(tab_previews)
        outer_layout_previews.setContentsMargins(4, 4, 4, 4)

        # Barre d'outils de l'onglet : comparaison des algorithmes à gauche (ancien bouton de l'onglet
        # Image & Filtres : n'agit que sur l'image de cet onglet), plein écran aligné à droite.
        compare_icon = QIcon.fromTheme("view-app-grid", QIcon.fromTheme(
            "view-list-icons", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)))
        # Affiche ou masque l'image originale (masquée par défaut, voir box_source_image).
        self.chk_show_original = QCheckBox(tr("img.show_original"))
        self.chk_show_original.setToolTip(tr("img.show_original_tip"))
        self.chk_show_original.toggled.connect(lambda checked: self.box_source_image.setVisible(checked))
        toolbar_previews = self._build_tab_toolbar(
            tab_previews, self._toggle_fullscreen_image_tab,
            left_actions=[(compare_icon, tr("img.compare_algos"), tr("img.compare_algos_tip"),
                           self.compare_dither_algorithms)],
            left_widgets=[self.chk_show_original])
        outer_layout_previews.addWidget(toolbar_previews)

        layout_previews = QHBoxLayout()
        # Réglages de l'image à gauche, comme dans Séparation.
        img_settings_scroll = self._side_settings_panel(self.tab_img)
        layout_previews.addWidget(img_settings_scroll)

        box_src = QGroupBox(tr("ui.source_image_box"))
        layout_src = QVBoxLayout()
        self.view_preview_src = ZoomableGraphicsView()
        layout_src.addWidget(self.view_preview_src)
        box_src.setLayout(layout_src)

        box_dither = QGroupBox(tr("ui.final_raster_box"))
        layout_dither = QVBoxLayout()
        self.view_preview_dither = ZoomableGraphicsView()
        layout_dither.addWidget(self.view_preview_dither)
        box_dither.setLayout(layout_dither)

        layout_previews.addWidget(box_src)
        # Image originale masquée par défaut : le rendu tramé prend toute la place. Elle reste tenue
        # à jour (display_source_image) ; la case « Afficher l'originale » la réaffiche.
        box_src.setVisible(False)
        self.box_source_image = box_src
        layout_previews.addWidget(box_dither)
        outer_layout_previews.addLayout(layout_previews)
        self.main_tabs_view.addTab(tab_previews, tr("ui.tab_image_tracing"))
        self.tab_previews = tab_previews

        tab_png2svg = self._init_png2svg_tab()
        self.main_tabs_view.addTab(tab_png2svg, tr("png2svg.tab_title"))

        # --- ONGLET SÉPARATION COULEUR ---
        self.main_tabs_view.addTab(self._init_separation_tab(), tr("sep.tab_title"))

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
        btn_undo_vector = QPushButton(tr("ui.vector_undo"))
        btn_undo_vector.clicked.connect(lambda: self.vector_canvas.undo())
        btn_redo_vector = QPushButton(tr("ui.vector_redo"))
        btn_redo_vector.clicked.connect(lambda: self.vector_canvas.redo())
        btn_fullscreen_vector = QPushButton(tr("ui.vector_fullscreen"))
        btn_fullscreen_vector.setIcon(self._fullscreen_icon())
        btn_fullscreen_vector.clicked.connect(self.toggle_fullscreen_vector_editor)
        tab_vector_editor._fullscreen_control = btn_fullscreen_vector   # voir _show_fullscreen_control
        # Deux lignes : en une seule, les 11 boutons demandaient ~1 500 px et leurs libellés étaient
        # tronqués dès que la fenêtre était un peu étroite. Ligne 1 : créer / importer ; ligne 2 : modifier.
        toolbar_vector.addWidget(btn_add_text)
        toolbar_vector.addWidget(btn_add_shape)
        toolbar_vector.addWidget(btn_import_svg_vector)
        toolbar_vector.addWidget(btn_box_generator)
        toolbar_vector.addWidget(btn_nesting)
        toolbar_vector.addStretch()
        layout_vector_editor.addLayout(toolbar_vector)
        toolbar_vector_edit = QHBoxLayout()
        toolbar_vector_edit.addWidget(btn_edit_selected)
        toolbar_vector_edit.addWidget(btn_rotate_selected)
        toolbar_vector_edit.addWidget(btn_dup_selected)
        toolbar_vector_edit.addWidget(btn_del_selected)
        toolbar_vector_edit.addWidget(btn_undo_vector)
        toolbar_vector_edit.addWidget(btn_redo_vector)
        toolbar_vector_edit.addStretch()
        toolbar_vector_edit.addWidget(btn_fullscreen_vector)
        layout_vector_editor.addLayout(toolbar_vector_edit)

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
        layout_vector_editor.addWidget(align_box)

        gen_progress_row_vector = QHBoxLayout()
        self.lbl_gen_progress_vector = AutoHideLabel("")
        self.gen_progress_bar_vector = QProgressBar()
        self.gen_progress_bar_vector.setRange(0, 100)
        self.gen_progress_bar_vector.setValue(0)
        self.gen_progress_bar_vector.setVisible(False)
        self.gen_progress_bar_vector.setMaximumHeight(16)
        gen_progress_row_vector.addWidget(self.lbl_gen_progress_vector)
        gen_progress_row_vector.addWidget(self.gen_progress_bar_vector)
        layout_vector_editor.addLayout(gen_progress_row_vector)

        self.vector_canvas = VectorCanvasView(self.layer_manager)
        layout_vector_editor.addWidget(self.vector_canvas)

        pos_box = QGroupBox(tr("ui.selection_props_box"))
        pos_form = QVBoxLayout()
        pos_row1 = QHBoxLayout()
        pos_row1.addWidget(QLabel(tr("ui.vector_x_mm")))
        self.spin_vec_x = QDoubleSpinBox(); self.spin_vec_x.setRange(-1000.0, 1000.0); self.spin_vec_x.setDecimals(2)
        self.spin_vec_x.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_x)
        pos_row1.addWidget(QLabel(tr("ui.vector_y_mm")))
        self.spin_vec_y = QDoubleSpinBox(); self.spin_vec_y.setRange(-1000.0, 1000.0); self.spin_vec_y.setDecimals(2)
        self.spin_vec_y.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_y)
        pos_row1.addWidget(QLabel(tr("ui.vector_rotation_deg")))
        self.spin_vec_rot = QDoubleSpinBox(); self.spin_vec_rot.setRange(-360.0, 360.0); self.spin_vec_rot.setDecimals(1)
        self.spin_vec_rot.valueChanged.connect(self.on_vector_position_spin_changed)
        pos_row1.addWidget(self.spin_vec_rot)
        pos_row1.addStretch()
        pos_form.addLayout(pos_row1)

        pos_row2 = QHBoxLayout()
        pos_row2.addWidget(QLabel(tr("ui.vector_layer")))
        self.combo_vec_layer = QComboBox()
        self.combo_vec_layer.currentIndexChanged.connect(self.on_vector_layer_spin_changed)
        pos_row2.addWidget(self.combo_vec_layer)
        pos_row2.addStretch()
        pos_form.addLayout(pos_row2)

        pos_box.setLayout(pos_form)
        pos_box.setEnabled(False)
        self.pos_box_vector = pos_box
        layout_vector_editor.addWidget(pos_box)

        self.lbl_vector_selection = QLabel(tr("ui.no_selection_label"))
        layout_vector_editor.addWidget(self.lbl_vector_selection)
        self.vector_canvas.selection_changed.connect(self.on_vector_selection_changed)
        self.vector_canvas.object_moved.connect(self.on_vector_object_moved)
        self.vector_canvas.edit_requested.connect(self.edit_vector_object)

        self.main_tabs_view.addTab(tab_vector_editor, tr("ui.tab_vector_editor"))
        self.tab_vector_editor = tab_vector_editor
        self.main_tabs_view.addTab(self.tab_layers, tr("tab.layers"))

        tab_vector_2d = QWidget()
        layout_vector_2d = QVBoxLayout(tab_vector_2d)

        # Options de l'aperçu (anciennes cases du bas de la colonne de gauche). « Optimiser le
        # chemin », elle, s'applique à la prochaine génération du G-Code.
        self.chk_flip_raster_preview = QCheckBox(tr("preview.flip"))
        self.chk_flip_raster_preview.setToolTip(tr("preview.flip_tip"))
        self.chk_flip_raster_preview.stateChanged.connect(self.on_flip_raster_preview_changed)
        self.chk_negative_raster_preview = QCheckBox(tr("preview.negative"))
        self.chk_negative_raster_preview.setToolTip(tr("preview.negative_tip"))
        self.chk_negative_raster_preview.setChecked(True)
        self.chk_negative_raster_preview.stateChanged.connect(self.on_flip_raster_preview_changed)
        self.chk_hide_rapid_moves = QCheckBox(tr("preview.hide_rapid"))
        self.chk_hide_rapid_moves.setToolTip(tr("preview.hide_rapid_tip"))
        self.chk_hide_rapid_moves.setChecked(True)
        self.chk_hide_rapid_moves.stateChanged.connect(self.on_flip_raster_preview_changed)
        self.chk_optimize_path = QCheckBox(tr("ui.optimize_path"))
        self.chk_optimize_path.setToolTip(tr("ui.optimize_path_tip"))
        self.chk_optimize_path.setChecked(True)
        toolbar_vector_2d = self._build_tab_toolbar(
            tab_vector_2d, lambda: self._toggle_fullscreen_tab("tab_vector_2d", "ui.tab_2d_preview"),
            left_widgets=[self.chk_flip_raster_preview, self.chk_negative_raster_preview,
                          self.chk_hide_rapid_moves, self.chk_optimize_path],
            right_widgets=[self._build_support_button()])
        layout_vector_2d.addWidget(toolbar_vector_2d)
        
        self.plot_widget = pg.PlotWidget(title=tr("ui.plot_title"))
        self.plot_widget.setBackground('#111111')
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('bottom', tr("ui.plot_x"), color='#ffffff')
        self.plot_widget.setLabel('left', tr("ui.plot_y"), color='#ffffff')
        self.plot_widget.scene().sigMouseClicked.connect(self._on_plot_clicked)

        self.gcode_position_marker = pg.ScatterPlotItem(
            size=14, pen=pg.mkPen('#ffffff', width=2), brush=pg.mkBrush('#ff2d55'),
            symbol='o'
        )
        self.gcode_position_marker.setZValue(1000)
        self.plot_widget.addItem(self.gcode_position_marker)
        
        self.info_text_item = pg.TextItem(html=f'<div style="color: #cccccc;">{tr("ui.plot_empty_state")}</div>', anchor=(0, 0))
        self.plot_widget.addItem(self.info_text_item)
        
        layout_vector_2d.addWidget(self.plot_widget)

        self.main_tabs_view.addTab(tab_vector_2d, tr("ui.tab_2d_preview"))
        self.tab_vector_2d = tab_vector_2d
        center_bottom_widget = QWidget()
        center_bottom_layout = QVBoxLayout(center_bottom_widget)
        center_bottom_layout.setContentsMargins(0, 0, 0, 0)

        dro_box = QGroupBox(tr("ui.dro_box"))
        dro_layout = QHBoxLayout()
        self.lbl_dro_state = QLabel(tr("ui.dro_state").format(value="—"))
        self.lbl_dro_x = QLabel(tr("ui.dro_x").format(value="—"))
        self.lbl_dro_y = QLabel(tr("ui.dro_y").format(value="—"))
        self.lbl_dro_z = QLabel(tr("ui.dro_z").format(value="—"))
        for lbl in (self.lbl_dro_state, self.lbl_dro_x, self.lbl_dro_y, self.lbl_dro_z):
            lbl.setStyleSheet("font-family: monospace; font-size: 13px;")

        self.btn_unlock_alarm = QPushButton(tr("ui.unlock_alarm"))
        self.btn_unlock_alarm.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; padding: 3px 10px;"
        )
        self.btn_unlock_alarm.clicked.connect(self.unlock_alarm)
        self.btn_unlock_alarm.setVisible(False)
        dro_layout.addWidget(self.lbl_dro_state)
        dro_layout.addWidget(self.btn_unlock_alarm)
        dro_layout.addStretch()
        dro_layout.addWidget(self.lbl_dro_x)
        dro_layout.addWidget(self.lbl_dro_y)
        dro_layout.addWidget(self.lbl_dro_z)
        dro_box.setLayout(dro_layout)
        center_bottom_layout.addWidget(dro_box)
        center_bottom_layout.addWidget(self.job_position_box)

        jog_box = QGroupBox(tr("ui.jog_box"))
        jog_layout = QGridLayout()

        btn_up = QPushButton("▲ Y+")
        btn_down = QPushButton("▼ Y-")
        btn_left = QPushButton("◄ X-")
        btn_right = QPushButton("► X+")
        
        btn_up_left = QPushButton("◤")
        btn_up_right = QPushButton("◥")
        btn_down_left = QPushButton("◣")
        btn_down_right = QPushButton("◢")

        btn_up.clicked.connect(lambda: self.jog_move(0, 1))
        btn_down.clicked.connect(lambda: self.jog_move(0, -1))
        btn_left.clicked.connect(lambda: self.jog_move(-1, 0))
        btn_right.clicked.connect(lambda: self.jog_move(1, 0))

        btn_up_left.clicked.connect(lambda: self.jog_move(-1, 1))
        btn_up_right.clicked.connect(lambda: self.jog_move(1, 1))
        btn_down_left.clicked.connect(lambda: self.jog_move(-1, -1))
        btn_down_right.clicked.connect(lambda: self.jog_move(1, -1))

        self.combo_step = QComboBox()
        self.combo_step.addItems(["0.1 mm", "1 mm", "10 mm", "100 mm"])
        self.combo_step.setCurrentIndex(2)

        self.spin_jog_speed = QSpinBox()
        self.spin_jog_speed.setRange(100, 10000)
        self.spin_jog_speed.setValue(3000)

        btn_homing_now = QPushButton(tr("ui.homing_cmd"))
        btn_homing_now.clicked.connect(self.send_homing)

        btn_zero_xy = QPushButton(tr("ui.zero_work"))
        btn_zero_xy.clicked.connect(lambda: self.send_manual_direct_cmd("G92 X0 Y0"))

        btn_go_zero = QPushButton(tr("ui.go_zero"))
        btn_go_zero.clicked.connect(lambda: self.send_manual_direct_cmd("G0 X0 Y0"))

        btn_pause = QPushButton(tr("ui.pause"))
        btn_pause.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        btn_pause.clicked.connect(self.send_pause)

        btn_resume = QPushButton(tr("ui.resume"))
        btn_resume.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_resume.clicked.connect(self.send_resume)

        btn_reset = QPushButton(tr("ui.reset"))
        btn_reset.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        btn_reset.clicked.connect(self.send_reset)

        btn_kill = QPushButton(tr("ui.kill"))
        btn_kill.setStyleSheet("background-color: #ff0000; color: white; font-weight: bold;")
        btn_kill.clicked.connect(self.send_kill)

        btn_frame = QPushButton(tr("ui.frame"))
        btn_frame.clicked.connect(self.run_frame)
        
        self.btn_send = QPushButton(tr("ui.send_to_laser"))
        self.btn_send.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_send.clicked.connect(self.send_to_laser)

        self.btn_repeat_last_job = QPushButton(tr("ui.repeat_last_job"))
        self.btn_repeat_last_job.clicked.connect(self.repeat_last_job)
        self.btn_repeat_last_job.setEnabled(False)

        jog_layout.addWidget(btn_up_left, 0, 0)
        jog_layout.addWidget(btn_up, 0, 1)
        jog_layout.addWidget(btn_up_right, 0, 2)
        jog_layout.addWidget(btn_left, 1, 0)
        jog_layout.addWidget(btn_homing_now, 1, 1)
        jog_layout.addWidget(btn_right, 1, 2)
        jog_layout.addWidget(btn_down_left, 2, 0)
        jog_layout.addWidget(btn_down, 2, 1)
        jog_layout.addWidget(btn_down_right, 2, 2)

        jog_layout.addWidget(QLabel(tr("ui.jog_step_label")), 0, 3)
        jog_layout.addWidget(self.combo_step, 0, 4)
        jog_layout.addWidget(QLabel(tr("ui.jog_speed_label")), 1, 3)
        jog_layout.addWidget(self.spin_jog_speed, 1, 4)

        jog_layout.addWidget(btn_zero_xy, 2, 3)
        jog_layout.addWidget(btn_go_zero, 2, 4)

        jog_layout.addWidget(btn_pause, 3, 0)
        jog_layout.addWidget(btn_resume, 3, 1)
        jog_layout.addWidget(btn_reset, 3, 2)
        jog_layout.addWidget(btn_kill, 3, 3)
        jog_layout.addWidget(btn_frame, 4, 0)
        jog_layout.addWidget(self.btn_send, 4, 1, 1, 4)
        jog_layout.addWidget(self.btn_repeat_last_job, 5, 1, 1, 4)

        jog_box.setLayout(jog_layout)
        center_bottom_layout.addWidget(jog_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        center_bottom_layout.addWidget(self.progress_bar)

        cmd_box = QGroupBox(tr("ui.direct_console_box"))
        cmd_layout = QHBoxLayout()
        self.txt_manual_cmd = HistoryLineEdit()
        self.txt_manual_cmd.setPlaceholderText(tr("ui.manual_grbl_placeholder"))
        self.txt_manual_cmd.returnPressed.connect(self.send_manual_cmd)
        
        btn_send_cmd = QPushButton(tr("ui.manual_send"))
        btn_send_cmd.clicked.connect(self.send_manual_cmd)

        cmd_layout.addWidget(self.txt_manual_cmd)
        cmd_layout.addWidget(btn_send_cmd)
        cmd_box.setLayout(cmd_layout)
        center_bottom_layout.addWidget(cmd_box)
        center_bottom_layout.addStretch()              # place libre en bas, pas dans les cadres

        self.main_tabs_view.setMinimumHeight(150)
        # Le panneau machine (DRO, jog, console directe) demande ~400 px. Réduit plus bas avec le
        # séparateur, il défile au lieu d'écraser ses cadres jusqu'à n'en laisser que les titres.
        center_bottom_scroll = QScrollArea()
        center_bottom_scroll.setWidget(center_bottom_widget)
        center_bottom_scroll.setWidgetResizable(True)
        center_bottom_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        center_bottom_scroll.setMinimumHeight(100)
        self.center_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.center_v_splitter.addWidget(self.main_tabs_view)
        self.center_v_splitter.addWidget(center_bottom_scroll)
        self.center_v_splitter.setStretchFactor(0, 3)
        self.center_v_splitter.setStretchFactor(1, 1)
        center_panel.addWidget(self.center_v_splitter)

        tab_console_gcode = QWidget()
        layout_console_gcode = QVBoxLayout(tab_console_gcode)
        layout_console_gcode.setContentsMargins(6, 6, 6, 6)

        toolbar_console_gcode = self._build_tab_toolbar(
            tab_console_gcode, lambda: self._toggle_fullscreen_tab("tab_console_gcode", "ui.tab_console_gcode"))
        layout_console_gcode.addWidget(toolbar_console_gcode)

        stats_box = QGroupBox(tr("ui.job_stats_box"))
        stats_layout = QVBoxLayout()
        self.lbl_stat_lines = QLabel(tr("ui.job_lines"))
        self.lbl_stat_power = QLabel(tr("ui.job_avg_power"))
        self.lbl_stat_time = QLabel(tr("ui.job_estimated_time"))
        stats_layout.addWidget(self.lbl_stat_lines)
        stats_layout.addWidget(self.lbl_stat_power)
        stats_layout.addWidget(self.lbl_stat_time)
        stats_box.setLayout(stats_layout)
        layout_console_gcode.addWidget(stats_box)

        export_box = QGroupBox(tr("ui.gcode_export_box"))
        export_layout = QHBoxLayout()
        
        btn_exp_gcode = QPushButton("Export .gcode")
        btn_exp_gcode.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_exp_gcode.clicked.connect(lambda: self.export_gcode_with_ext(".gcode"))
        
        btn_exp_nc = QPushButton("Export .nc")
        btn_exp_nc.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_exp_nc.clicked.connect(lambda: self.export_gcode_with_ext(".nc"))
        
        btn_exp_gc = QPushButton("Export .gc")
        btn_exp_gc.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px;")
        btn_exp_gc.clicked.connect(lambda: self.export_gcode_with_ext(".gc"))

        export_layout.addWidget(btn_exp_gcode)
        export_layout.addWidget(btn_exp_nc)
        export_layout.addWidget(btn_exp_gc)
        export_box.setLayout(export_layout)
        layout_console_gcode.addWidget(export_box)

        layout_console_gcode.addWidget(QLabel(tr("ui.generated_console_label")))
        self.txt_console = QTextEdit()
        self.txt_console.setFontFamily("Courier")
        layout_console_gcode.addWidget(self.txt_console)

        gen_progress_row = QHBoxLayout()
        self.lbl_gen_progress = AutoHideLabel("")
        self.gen_progress_bar = QProgressBar()
        self.gen_progress_bar.setRange(0, 100)
        self.gen_progress_bar.setValue(0)
        self.gen_progress_bar.setVisible(False)
        self.gen_progress_bar.setMaximumHeight(16)
        gen_progress_row.addWidget(self.lbl_gen_progress)
        gen_progress_row.addWidget(self.gen_progress_bar)
        layout_console_gcode.addLayout(gen_progress_row)

        self.main_tabs_view.addTab(tab_console_gcode, tr("ui.tab_console_gcode"))
        self.tab_console_gcode = tab_console_gcode

        tab_job_queue = QWidget()
        layout_tab_job_queue = QVBoxLayout(tab_job_queue)
        layout_tab_job_queue.setContentsMargins(6, 6, 6, 6)
        # Deux moitiés réglables : la file à gauche, le G-Code envoyé à droite.
        queue_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout_tab_job_queue.addWidget(queue_splitter)
        queue_left = QWidget()
        layout_job_queue = QVBoxLayout(queue_left)
        layout_job_queue.setContentsMargins(0, 0, 0, 0)
        queue_splitter.addWidget(queue_left)

        self.list_job_queue = QListWidget()
        self.list_job_queue.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_job_queue.model().rowsMoved.connect(self._on_queue_reordered)
        layout_job_queue.addWidget(self.list_job_queue)

        queue_btn_row1 = QHBoxLayout()
        btn_queue_add = QPushButton(tr("ui.queue_add_current"))
        btn_queue_add.clicked.connect(self.add_current_gcode_to_queue)
        btn_queue_remove = QPushButton(tr("ui.queue_remove_selected"))
        btn_queue_remove.clicked.connect(self.remove_selected_from_queue)
        btn_queue_clear = QPushButton(tr("ui.queue_clear"))
        btn_queue_clear.clicked.connect(self.clear_job_queue)
        queue_btn_row1.addWidget(btn_queue_add)
        queue_btn_row1.addWidget(btn_queue_remove)
        queue_btn_row1.addWidget(btn_queue_clear)
        layout_job_queue.addLayout(queue_btn_row1)

        self.btn_run_queue = QPushButton(tr("ui.queue_run"))
        self.btn_run_queue.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 6px;")
        self.btn_run_queue.clicked.connect(self.run_job_queue)
        layout_job_queue.addWidget(self.btn_run_queue)

        self.lbl_queue_status = QLabel(tr("ui.queue_empty"))
        layout_job_queue.addWidget(self.lbl_queue_status)

        # Suivi de l'envoi : chaque ligne de G-Code s'ajoute ici au moment où elle part vers la
        # machine (GCodeStreamerThread.lines_sent), pour la file comme pour « Envoyer au laser ».
        sent_box = QGroupBox(tr("queue.sent_log_title"))
        sent_layout = QVBoxLayout(sent_box)
        self.txt_sent_gcode = QPlainTextEdit()
        self.txt_sent_gcode.setReadOnly(True)
        self.txt_sent_gcode.setMaximumBlockCount(20000)     # garde les 20 000 dernières lignes
        self.txt_sent_gcode.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.txt_sent_gcode.setStyleSheet("font-family: monospace;")
        self.txt_sent_gcode.setPlaceholderText(tr("queue.sent_log_placeholder"))
        sent_layout.addWidget(self.txt_sent_gcode)
        queue_splitter.addWidget(sent_box)
        # Moitié / moitié au départ, puis à chaque redimensionnement de la fenêtre. Des tailles
        # égales et grandes : Qt les ramène à la largeur réelle en gardant la proportion.
        queue_splitter.setStretchFactor(0, 1)
        queue_splitter.setStretchFactor(1, 1)
        queue_splitter.setSizes([100000, 100000])

        self.main_tabs_view.addTab(tab_job_queue, tr("ui.tab_job_queue"))
        self.tab_job_queue = tab_job_queue

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

    def _on_main_tab_changed(self, idx):
      if hasattr(self, 'tab_separation') and self.main_tabs_view.widget(idx) == self.tab_separation:
          self.separation_refresh_if_dirty()