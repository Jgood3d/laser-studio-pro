"""Barre de menus, barre d'outils principale et état de la connexion."""

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QMessageBox,
    QPushButton,
    QStyle,
    QToolBar,
)
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
)
from app_utils import APP_VERSION, find_resource
from i18n import SUPPORTED_LANGUAGES, get_current_language, set_language, tr
from stencil_studio.studio_dialog import open_stencil_studio
from ui.about import AboutDialog
from ui.buy_me_a_coffee import BuyMeACoffeeDialog
from ui.support import SupportDialog


class MenusMixin:
    def change_theme(self, theme_name):
        """Bascule de thème à la volée et mémorise le code.

        Codes possibles : dark, light, dusk, warm.
        """
        from app_theme import apply_app_theme, normalize_theme_name

        theme_name = normalize_theme_name(theme_name)
        app = QApplication.instance()
        settings = QSettings("LaserStudioPro", "UIConfig")
        settings.setValue("app_theme", theme_name)
        settings.sync()  # écriture immédiate sous Windows
        apply_app_theme(app, theme_name)

        for code, act in getattr(self, "_theme_actions", {}).items():
            act.setChecked(code == theme_name)

        # Stencil Studio ouvert : même thème que LSP
        dlg = getattr(self, "_stencil_studio_dialog", None)
        if dlg is not None:
            try:
                dlg.sync_theme_from_lsp(theme_name)
            except Exception:
                pass

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        # Icônes standard : celles du thème du système (freedesktop sous
        # Linux), sinon celles du style Qt, présentes sur toutes les
        # plateformes (aucune si le style n'a pas d'équivalent).
        def std_icon(theme_icon, fallback=QStyle.StandardPixmap.SP_FileIcon):
            icon = QIcon.fromTheme(theme_icon)
            return (
                icon
                if not icon.isNull()
                else self.style().standardIcon(fallback)
            )

        menu_fichier = menu_bar.addMenu(tr("menu.file"))
        self.action_save_project = action_save = menu_fichier.addAction(
            std_icon(
                QIcon.ThemeIcon.DocumentSave,
                QStyle.StandardPixmap.SP_DialogSaveButton,
            ),
            tr("menu.file.save_project"),
        )
        action_save.setShortcut(QKeySequence.StandardKey.Save)
        action_save.triggered.connect(self.save_project)
        action_load = self.action_open_project = menu_fichier.addAction(
            std_icon(
                QIcon.ThemeIcon.DocumentOpen,
                QStyle.StandardPixmap.SP_DialogOpenButton,
            ),
            tr("menu.file.open_project"),
        )
        action_load.setShortcut(QKeySequence.StandardKey.Open)
        action_load.triggered.connect(self.load_project)
        self.menu_recent_projects = menu_fichier.addMenu(
            std_icon(
                QIcon.ThemeIcon.DocumentOpenRecent,
                QStyle.StandardPixmap.SP_FileDialogDetailedView,
            ),
            tr("menu.file.recent_projects"),
        )
        self._refresh_recent_projects_menu()
        menu_fichier.addSeparator()
        self.action_quit = action_quit = menu_fichier.addAction(
            std_icon(
                QIcon.ThemeIcon.ApplicationExit,
                QStyle.StandardPixmap.SP_DialogCloseButton,
            ),
            tr("menu.file.quit"),
        )
        # StandardKey.Quit est vide sous Windows (Alt+F4 y est géré par le
        # système) : Ctrl+Q en repli.
        action_quit.setShortcuts(
            QKeySequence.keyBindings(QKeySequence.StandardKey.Quit)
            or [QKeySequence("Ctrl+Q")]
        )
        action_quit.triggered.connect(self.close)

        # Menu Paramètres : réglages propres à la machine (fenêtres ouvertes
        # depuis la barre de menus, ils occupaient des onglets de la colonne de
        # gauche) et langue de l'interface.
        menu_parametres = menu_bar.addMenu(tr("menu.settings"))
        # Pas d'entrée QIcon.ThemeIcon pour ces réglages : noms d'icônes
        # freedesktop.
        self.action_machine_params_window = menu_parametres.addAction(
            std_icon(
                "preferences-system", QStyle.StandardPixmap.SP_ComputerIcon
            ),
            tr("tab.machine_params"),
        )
        self.action_machine_params_window.triggered.connect(
            lambda: self.show_settings_window("machine_params")
        )
        self.action_machine_window = menu_parametres.addAction(
            std_icon("network-wired", QStyle.StandardPixmap.SP_DriveNetIcon),
            tr("tab.machine_profiles"),
        )
        self.action_machine_window.triggered.connect(
            lambda: self.show_settings_window("machine")
        )
        self.action_grbl_window = menu_parametres.addAction(
            std_icon(
                "utilities-terminal",
                QStyle.StandardPixmap.SP_FileDialogContentsView,
            ),
            tr("tab.grbl_config"),
        )
        self.action_grbl_window.triggered.connect(
            lambda: self.show_settings_window("grbl")
        )
        menu_parametres.addSeparator()

        menu_langue = menu_parametres.addMenu(
            std_icon(
                "preferences-desktop-locale", QStyle.StandardPixmap.SP_DirIcon
            ),
            tr("menu.language"),
        )
        current_lang = get_current_language()
        self._lang_actions = {}
        for lang_code, lang_label in SUPPORTED_LANGUAGES.items():
            action_lang = menu_langue.addAction(lang_label)
            action_lang.setCheckable(True)
            action_lang.setChecked(lang_code == current_lang)
            action_lang.triggered.connect(
                lambda checked, code=lang_code: self._on_language_selected(
                    code
                )
            )
            self._lang_actions[lang_code] = action_lang

        # Sous-menu Thème (Sombre / Clair / Dusk / Warm)
        from app_theme import available_themes, normalize_theme_name

        settings = QSettings("LaserStudioPro", "UIConfig")
        current_theme = normalize_theme_name(
            settings.value("app_theme", "dark")
        )
        menu_theme = menu_parametres.addMenu(
            std_icon(
                "preferences-desktop-theme",
                QStyle.StandardPixmap.SP_DesktopIcon,
            ),
            tr("menu.theme"),
        )
        self._theme_actions = {}
        for t_code, t_label_key in available_themes():
            act = menu_theme.addAction(tr(t_label_key))
            act.setCheckable(True)
            act.setChecked(t_code == current_theme)
            act.triggered.connect(
                lambda checked, code=t_code: self.change_theme(code)
            )
            self._theme_actions[t_code] = act

        menu_parametres.addSeparator()

        # Menu Outils : assistants ponctuels, hors du flux principal de
        # préparation d'un job.
        self.tools_menu = menu_bar.addMenu(tr("menu.tools"))
        # Grille de carrés de test ; « -symbolic » : seule variante présente
        # dans Adwaita.
        self.action_matrix_window = self.tools_menu.addAction(
            std_icon(
                "view-grid-symbolic",
                QStyle.StandardPixmap.SP_FileDialogListView,
            ),
            tr("tab.test_matrix"),
        )
        self.action_matrix_window.triggered.connect(
            lambda: self.show_settings_window("test_matrix")
        )
        action_open_stencil = self.tools_menu.addAction(
            std_icon(
                "applications-graphics", QStyle.StandardPixmap.SP_DesktopIcon
            ),
            tr("menu.tools.stencil_studio"),
        )
        action_open_stencil.triggered.connect(
            lambda: open_stencil_studio(self)
        )
        # Raccourcis vers deux onglets centraux (voir show_main_tab).
        separation_icon = std_icon(
            "color-management", QStyle.StandardPixmap.SP_DriveNetIcon
        )
        vectorize_icon = std_icon(
            "draw-bezier-curves", QStyle.StandardPixmap.SP_FileIcon
        )
        action_separation = self.tools_menu.addAction(
            separation_icon, tr("sep.tab_title")
        )
        action_separation.triggered.connect(
            lambda: self.show_main_tab("tab_separation")
        )
        action_png2svg = self.tools_menu.addAction(
            vectorize_icon, tr("png2svg.tab_title")
        )
        action_png2svg.triggered.connect(
            lambda: self.show_main_tab("tab_png2svg")
        )

        menu_aide = menu_bar.addMenu(tr("menu.help"))
        # Version : icône de l'application (définie dans main.py, reprise par
        # la fenêtre).
        action_version = menu_aide.addAction(
            self.windowIcon(), f"{tr('menu.help.version')} {APP_VERSION}"
        )
        action_version.setEnabled(False)
        menu_aide.addSeparator()
        action_about = menu_aide.addAction(
            std_icon(
                QIcon.ThemeIcon.HelpAbout,
                QStyle.StandardPixmap.SP_MessageBoxInformation,
            ),
            tr("menu.help.about"),
        )
        action_about.triggered.connect(lambda: AboutDialog(self).exec())
        # Support : contact par e-mail (voir ui.support_body).
        action_support = menu_aide.addAction(
            std_icon(QIcon.ThemeIcon.MailMessageNew), tr("menu.help.support")
        )
        action_support.triggered.connect(lambda: SupportDialog(self).exec())
        # Buy me a coffee : même logo que le bouton de soutien
        # (_build_support_button).
        coffee_path = find_resource("buy_me_a_coffee.png")
        action_coffee = menu_aide.addAction(
            QIcon(coffee_path) if coffee_path else QIcon(),
            tr("menu.help.coffee"),
        )
        action_coffee.triggered.connect(
            lambda: BuyMeACoffeeDialog(self).exec()
        )

    def show_main_tab(self, tab_attr):
        """Affiche l'onglet central `tab_attr` (ex. "tab_separation").

        Il est rendu visible s'il était masqué. S'il est ouvert en plein
        écran (sorti des onglets), sa fenêtre est ramenée au premier plan.
        """
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
        """Barre d'outils sous le menu.

        Raccourcis vers les entrées des menus Fichier, Paramètres et Outils
        (mêmes QAction : icône, libellé, raccourci et action identiques),
        annuler/refaire des réglages image, actions sur l'image chargée,
        puis connexion au graveur.
        """
        toolbar = QToolBar(tr("toolbar.main"), self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        # Icônes seules, libellé en infobulle (une entrée sans icône hors Linux
        # affiche son libellé).
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        # Même action que Fichier > Quitter (Ctrl+Q).
        toolbar.addAction(self.action_quit)
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

        def std_icon(theme_icon, fallback=QStyle.StandardPixmap.SP_FileIcon):
            icon = (
                QIcon.fromTheme(theme_icon)
                if isinstance(theme_icon, str)
                else QIcon.fromTheme(theme_icon)
            )
            if icon.isNull():
                icon = self.style().standardIcon(fallback)
            return icon

        # Annuler / refaire des réglages image (anciens boutons de l'onglet
        # Image & Filtres). Les raccourcis Ctrl+Z / Ctrl+Y restent ceux de
        # l'onglet (QShortcut limité à l'onglet), pour ne pas entrer en conflit
        # avec l'annulation de l'Éditeur vectoriel.
        toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.EditUndo, QStyle.StandardPixmap.SP_ArrowBack
            ),
            tr("ui.img_undo"),
            self.undo_image_settings,
        )
        toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.EditRedo, QStyle.StandardPixmap.SP_ArrowForward
            ),
            tr("ui.img_redo"),
            self.redo_image_settings,
        )
        toolbar.addSeparator()
        # Image chargée (anciens boutons et cases de l'onglet Image & Filtres)
        # : suppression, rotation, puis miroirs. Les miroirs sont des actions
        # cochables qui gardent l'état. Suppression et rotation agissent sur
        # l'image de l'onglet affiché (_image_tab_kind).
        action_delete = toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.EditDelete, QStyle.StandardPixmap.SP_TrashIcon
            ),
            tr("img.delete"),
            self._on_toolbar_delete_image,
        )
        action_rotate_left = toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.ObjectRotateLeft,
                QStyle.StandardPixmap.SP_ArrowBack,
            ),
            tr("img.rotate_left"),
            lambda: self._on_toolbar_rotate_image(clockwise=False),
        )
        action_rotate_right = toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.ObjectRotateRight,
                QStyle.StandardPixmap.SP_ArrowForward,
            ),
            tr("img.rotate_right"),
            lambda: self._on_toolbar_rotate_image(clockwise=True),
        )
        # Pas d'équivalent QIcon.ThemeIcon pour les miroirs : nom d'icône
        # freedesktop.
        flip_h_icon = std_icon(
            "object-flip-horizontal", QStyle.StandardPixmap.SP_ArrowLeft
        )
        flip_v_icon = std_icon(
            "object-flip-vertical", QStyle.StandardPixmap.SP_ArrowUp
        )
        self.action_mirror_h = toolbar.addAction(
            flip_h_icon, tr("img.mirror_h")
        )
        self.action_mirror_v = toolbar.addAction(
            flip_v_icon, tr("img.mirror_v")
        )
        for action in (self.action_mirror_h, self.action_mirror_v):
            action.setCheckable(True)
            action.toggled.connect(self.update_image_processing)
        # Même action que le bouton de l'onglet Image & Filtres, toujours
        # disponible.
        toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.DocumentRevert,
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("img.reset"),
            self.reset_image_settings,
        )
        # Activées seulement avec une image chargée, sur un onglet qui
        # l'affiche (update_image_actions_state).
        self._image_actions = (
            action_delete,
            action_rotate_left,
            action_rotate_right,
        )
        self._mirror_actions = (self.action_mirror_h, self.action_mirror_v)
        for action in self._image_actions + self._mirror_actions:
            action.setEnabled(False)
        toolbar.addSeparator()
        # G-Code (anciens boutons du bas de la colonne de gauche) : estimer,
        # générer (bouton bleu conservé tel quel, avec son libellé), importer
        # un G-Code existant.
        estimate_icon = std_icon(
            "chronometer", QStyle.StandardPixmap.SP_FileDialogInfoView
        )
        toolbar.addAction(
            estimate_icon, tr("gcode.estimate"), self.estimate_job_time
        )
        btn_generate = QPushButton(tr("gcode.generate"))
        btn_generate.setStyleSheet(
            "background-color: #2b5c8f; color: white; "
            "font-weight: bold; padding: 3px;"
        )
        btn_generate.clicked.connect(self.generate_job)
        toolbar.addWidget(btn_generate)
        import_icon = std_icon(
            "document-import", QStyle.StandardPixmap.SP_FileIcon
        )
        toolbar.addAction(
            import_icon, tr("gcode.import"), self.import_gcode_file
        )
        toolbar.addSeparator()
        # Connexion au graveur : mêmes réglages que la page « Matériaux et
        # connexion au graveur ». La liste des ports partage son modèle avec
        # celle de la page (voir combo_ports).
        self.combo_ports_toolbar = QComboBox()
        self.combo_ports_toolbar.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo_ports_toolbar.setMinimumContentsLength(16)
        self.combo_ports_toolbar.setToolTip(tr("usb.port"))
        self.combo_ports_toolbar.currentTextChanged.connect(
            lambda text: self.combo_ports_toolbar.setToolTip(
                text or tr("usb.port")
            )
        )
        toolbar.addWidget(self.combo_ports_toolbar)
        toolbar.addAction(
            std_icon(
                QIcon.ThemeIcon.ViewRefresh,
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("usb.refresh_ports"),
            self.refresh_com_ports,
        )
        self.action_connect = toolbar.addAction(
            tr("laser.connect"), self.toggle_usb
        )
        # Seul bouton avec son libellé : l'état de la connexion doit se lire
        # d'un coup d'œil.
        toolbar.widgetForAction(self.action_connect).setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
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
        """Met le bouton de connexion en accord avec l'état du port.

        Page et barre d'outils : « Déconnecter » sur fond vert / pastille
        verte si connecté, « Connecter GRBL » / pastille rouge sinon.
        Verrouille ou déverrouille aussi les commandes de la machine.
        """
        connected = self.usb.is_connected()
        label = tr("laser.disconnect") if connected else tr("laser.connect")
        button = getattr(self, "btn_connect", None)
        if button is not None:
            button.setText(label)
            button.setStyleSheet(
                "background-color: #27ae60; color: white;" if connected else ""
            )
        action = getattr(self, "action_connect", None)
        if action is not None:
            action.setText(label)
            action.setIcon(
                self._status_dot_icon("#27ae60" if connected else "#e74c3c")
            )
        # Pilotage, actions de job et console directe : verrouillés tant que
        # le graveur n'est pas connecté. La position du job reste modifiable
        # (elle sert aussi à générer le G-Code hors connexion).
        for name in ("jog_panel", "job_actions_panel"):
            panel = getattr(self, name, None)
            if panel is not None:
                panel.set_connected(connected)
        for name in ("direct_console_box",):
            box = getattr(self, name, None)
            if box is not None:
                box.setEnabled(connected)

    def _on_language_selected(self, lang_code):
        set_language(lang_code)
        for code, action in self._lang_actions.items():
            action.setChecked(code == lang_code)
        QMessageBox.information(
            self,
            tr("menu.language.restart_title"),
            tr("menu.language.restart_body"),
        )
