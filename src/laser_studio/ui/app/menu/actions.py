"""Actions de la fenêtre principale, partagées par le menu et la barre.

Une QAction porte l'icône, le libellé, le raccourci et l'état (actif,
coché) d'une commande. Le menu et la barre d'outils affichent les mêmes
actions : un seul endroit les crée, et un seul endroit émet les signaux.
"""

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import QApplication, QStyle

from laser_studio.core.paths import find_resource
from laser_studio.core.version import APP_VERSION
from laser_studio.i18n import SUPPORTED_LANGUAGES, get_current_language, tr
from laser_studio.ui.utils import palette_icon


def standard_icon(theme_icon, fallback=QStyle.StandardPixmap.SP_FileIcon):
    """Icône du thème du système (freedesktop sous Linux), sinon icône
    standard du style Qt, présente sur toutes les plateformes."""
    icon = QIcon.fromTheme(theme_icon)
    if icon.isNull():
        icon = QApplication.style().standardIcon(fallback)
    return icon


def bundled_icon(name, fallback):
    """Icône `name` du pack Breeze embarqué, dans la couleur du texte du
    thème (voir ui.utils.palette_icon), sinon l'icône standard `fallback`."""
    return palette_icon(
        name, QApplication.palette(), QApplication.style().standardIcon(fallback)
    )


# Extensions proposées dans « Fichier > Enregistrer le G-Code », une par
# entrée.
GCODE_EXPORT_EXTENSIONS = (".gcode", ".nc", ".gc")


class AppActions(QObject):
    """Toutes les actions du menu et de la barre d'outils, et leurs signaux.

    AppMenuBar et AppToolBar ne font que ranger ces actions. La fenêtre
    (plus tard un contrôleur) s'abonne aux signaux :

        actions = AppActions(window)
        actions.save_project_requested.connect(window.project.save)

    L'état passe par des méthodes set_… (langue, thème, actions sur
    l'image, enregistrement du G-Code) ; les miroirs se lisent sur
    mirror_h / mirror_v.
    """

    # Fichier
    save_project_requested = pyqtSignal()
    open_project_requested = pyqtSignal()
    recent_project_requested = pyqtSignal(str)  # chemin du projet
    gcode_export_requested = pyqtSignal(str)  # extension : ".gcode"…
    # Enregistrement du G-Code possible ou non (sous-menu du menu Fichier)
    gcode_export_enabled_changed = pyqtSignal(bool)
    quit_requested = pyqtSignal()
    # Paramètres et outils : "machine_params", "grbl",
    # "test_matrix"
    settings_window_requested = pyqtSignal(str)
    language_selected = pyqtSignal(str)  # code de langue : "fr", "en"…
    theme_selected = pyqtSignal(str)  # code de thème : "dark", "light"…
    stencil_studio_requested = pyqtSignal()
    main_tab_requested = pyqtSignal(str)  # "tab_separation", "tab_png2svg"
    # Outils de l'onglet « Graver une image vectorielle »
    vector_import_requested = pyqtSignal()
    generator_requested = pyqtSignal(str)  # fenêtre des générateurs, sur « box », « puzzle », « ornament », « keychain »
    camera_requested = pyqtSignal()  # dialogue Caméra (alignement plateau)
    history_requested = pyqtSignal()  # historique des gravures
    # Affichage
    fullscreen_requested = pyqtSignal()  # onglet affiché en plein écran

    job_queue_requested = pyqtSignal()  # file d'attente : son onglet du panneau du bas
    bottom_panel_toggled = pyqtSignal(bool)  # True : panneau du bas déplié (Ctrl+J)
    # Aide
    documentation_requested = pyqtSignal()
    about_requested = pyqtSignal()
    support_requested = pyqtSignal()
    coffee_requested = pyqtSignal()
    # Image
    image_undo_requested = pyqtSignal()
    image_redo_requested = pyqtSignal()
    image_delete_requested = pyqtSignal()
    image_rotate_requested = pyqtSignal(bool)  # True : sens horaire
    mirror_changed = pyqtSignal(bool, bool)  # miroir horizontal, vertical
    image_reset_requested = pyqtSignal()
    # G-code
    estimate_requested = pyqtSignal()
    generate_requested = pyqtSignal()
    gcode_import_requested = pyqtSignal()
    # Menu Job (raccourcis clavier valables dans toute la fenêtre)
    send_job_requested = pyqtSignal()
    frame_requested = pyqtSignal()
    frame_contour_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_file_actions()
        self._create_settings_actions()
        self._create_view_actions()
        self._create_tools_actions()
        self._create_help_actions(parent)
        self._create_image_actions()
        self._create_gcode_actions()

    # -- état reçu de la fenêtre / du contrôleur

    def set_gcode_export_enabled(self, enabled):
        """Enregistrement du G-Code : actif une fois le G-Code généré."""
        for action in self.gcode_export_actions.values():
            action.setEnabled(enabled)
        self.gcode_export_enabled_changed.emit(enabled)

    def set_language(self, code):
        """Coche la langue `code` dans le menu."""
        for lang, action in self.language_actions.items():
            action.setChecked(lang == code)

    def set_theme(self, code):
        """Coche le thème `code` dans le menu."""
        for theme, action in self.theme_actions.items():
            action.setChecked(theme == code)

    def set_image_actions_enabled(self, enabled):
        """Supprimer et pivoter : actifs si l'onglet affiche une image."""
        for action in self.image_actions:
            action.setEnabled(enabled)

    def set_mirrors_enabled(self, enabled):
        """Miroirs : actifs si l'onglet affiche une image à graver."""
        for action in (self.mirror_h, self.mirror_v):
            action.setEnabled(enabled)

    # -- création

    def _action(self, icon, text, signal=None, *args):
        """QAction de ce menu ; `signal` (avec `args`) émis au clic."""
        action = QAction(icon, text, self)
        if signal is not None:
            action.triggered.connect(lambda _checked=False: signal.emit(*args))
        return action

    def _create_file_actions(self):
        self.save_project = self._action(
            standard_icon(
                QIcon.ThemeIcon.DocumentSave,
                QStyle.StandardPixmap.SP_DialogSaveButton,
            ),
            tr("menu.file.save_project"),
            self.save_project_requested,
        )
        self.save_project.setShortcut(QKeySequence.StandardKey.Save)
        self.open_project = self._action(
            standard_icon(
                QIcon.ThemeIcon.DocumentOpen,
                QStyle.StandardPixmap.SP_DialogOpenButton,
            ),
            tr("menu.file.open_project"),
            self.open_project_requested,
        )
        self.open_project.setShortcut(QKeySequence.StandardKey.Open)
        self.recent_projects_icon = standard_icon(
            QIcon.ThemeIcon.DocumentOpenRecent,
            QStyle.StandardPixmap.SP_FileDialogDetailedView,
        )
        self.quit = self._action(
            standard_icon(
                QIcon.ThemeIcon.ApplicationExit,
                QStyle.StandardPixmap.SP_DialogCloseButton,
            ),
            tr("menu.file.quit"),
            self.quit_requested,
        )
        # StandardKey.Quit est vide sous Windows (Alt+F4 y est géré par le
        # système) : Ctrl+Q en repli.
        self.quit.setShortcuts(
            QKeySequence.keyBindings(QKeySequence.StandardKey.Quit)
            or [QKeySequence("Ctrl+Q")]
        )
        self.gcode_export_icon = standard_icon(
            QIcon.ThemeIcon.DocumentSaveAs,
            QStyle.StandardPixmap.SP_DialogSaveButton,
        )
        self.gcode_export_actions = {
            extension: self._action(
                QIcon(), extension, self.gcode_export_requested, extension
            )
            for extension in GCODE_EXPORT_EXTENSIONS
        }
        # Rien à enregistrer avant la première génération.
        for action in self.gcode_export_actions.values():
            action.setEnabled(False)

    def _create_view_actions(self):
        # Plein écran de l'onglet affiché, quel qu'il soit (barre d'outils,
        # à côté du bouton ko-fi ; F11).
        self.fullscreen = self._action(
            bundled_icon("view-fullscreen", QStyle.StandardPixmap.SP_TitleBarMaxButton),
            tr("ui.vector_fullscreen"),
            self.fullscreen_requested,
        )
        self.fullscreen.setShortcut(QKeySequence(Qt.Key.Key_F11))
        # Panneau du bas (graveur, G-Code, file d'attente) : déplié ou replié, Ctrl+J comme dans VS Code.
        self.bottom_panel = self._action(QIcon(), tr("menu.view.bottom_panel"))
        self.bottom_panel.setCheckable(True)
        self.bottom_panel.setShortcut(QKeySequence("Ctrl+J"))
        self.bottom_panel.toggled.connect(self.bottom_panel_toggled)
        # File d'attente (barre d'outils) : son onglet du panneau du bas.
        self.job_queue = self._action(
            standard_icon(
                "view-list-details",
                QStyle.StandardPixmap.SP_FileDialogDetailedView,
            ),
            tr("menu.view.job_queue"),
        )
        self.job_queue.triggered.connect(lambda: self.job_queue_requested.emit())

    def _create_settings_actions(self):
        # Pas d'entrée QIcon.ThemeIcon pour ces réglages : noms d'icônes
        # freedesktop.
        self.machine_params_window = self._action(
            standard_icon(
                "preferences-system", QStyle.StandardPixmap.SP_ComputerIcon
            ),
            tr("menu.file.settings"),           # fenêtre « Paramètres » (graveur, GRBL, langue et thème)
            self.settings_window_requested,
            "machine_params",
        )
        self.language_icon = standard_icon(
            "preferences-desktop-locale", QStyle.StandardPixmap.SP_DirIcon
        )
        current_lang = get_current_language()
        self.language_actions = {}
        for code, label in SUPPORTED_LANGUAGES.items():
            action = self._action(QIcon(), label, self.language_selected, code)
            action.setCheckable(True)
            action.setChecked(code == current_lang)
            self.language_actions[code] = action

        from laser_studio.ui.app.theme import available_themes, current_theme_name

        self.theme_icon = standard_icon(
            "preferences-desktop-theme", QStyle.StandardPixmap.SP_DesktopIcon
        )
        current_theme = current_theme_name()
        self.theme_actions = {}
        for code, label_key in available_themes():
            action = self._action(
                QIcon(), tr(label_key), self.theme_selected, code
            )
            action.setCheckable(True)
            action.setChecked(code == current_theme)
            self.theme_actions[code] = action

    def _create_tools_actions(self):
        # Icônes du pack Breeze embarqué, dans la couleur du thème : le thème
        # d'icônes du bureau (Adwaita…) n'a pas la plupart d'entre elles.
        # Grille de carrés de test ; « -symbolic » : seule variante présente
        # dans Adwaita.
        self.test_matrix_window = self._action(
            bundled_icon("view-grid-symbolic", QStyle.StandardPixmap.SP_FileDialogListView),
            tr("tab.test_matrix"),
            self.settings_window_requested,
            "test_matrix",
        )
        self.stencil_studio = self._action(
            bundled_icon("applications-graphics", QStyle.StandardPixmap.SP_DesktopIcon),
            tr("menu.tools.stencil_studio"),
            self.stencil_studio_requested,
        )
        # Raccourcis vers deux onglets centraux (voir show_main_tab).
        self.separation_tab = self._action(
            bundled_icon("color-management", QStyle.StandardPixmap.SP_DriveNetIcon),
            tr("sep.tab_title"),
            self.main_tab_requested,
            "tab_separation",
        )
        self.png2svg_tab = self._action(
            bundled_icon("draw-bezier-curves", QStyle.StandardPixmap.SP_FileIcon),
            tr("png2svg.tab_title"),
            self.main_tab_requested,
            "tab_png2svg",
        )
        self.tool_actions = (
            self.test_matrix_window,
            self.stencil_studio,
            self.separation_tab,
            self.png2svg_tab,
        )

        # Outils de l'éditeur vectoriel : ouvrent d'abord son onglet.
        self.vector_import = self._action(
            bundled_icon("document-import", QStyle.StandardPixmap.SP_FileIcon),
            tr("menu.tools.import_vector"),
            self.vector_import_requested,
        )
        # Accès direct à chaque générateur : la fenêtre des générateurs, ouverte sur sa page.
        self.generator_actions = {
            kind: self._action(bundled_icon(icon, QStyle.StandardPixmap.SP_DirIcon), tr(key),
                               self.generator_requested, kind)
            for kind, key, icon in (("box", "menu.tools.box", "draw-cuboid"),
                                    ("puzzle", "menu.tools.puzzle", "games-config-board"),
                                    ("ornament", "menu.tools.ornament", "draw-ellipse"),
                                    ("keychain", "menu.tools.keychain", "keychain"))
        }
        self.camera = self._action(
            bundled_icon("camera-photo", QStyle.StandardPixmap.SP_ComputerIcon),
            tr("menu.tools.camera"),
            self.camera_requested,
        )
        self.history = self._action(
            bundled_icon("chronometer", QStyle.StandardPixmap.SP_FileDialogInfoView),
            tr("menu.tools.history"),
            self.history_requested,
        )
        # Bibliothèque : la fenêtre des générateurs, sur sa première page.
        self.library = self._action(bundled_icon("view-app-grid", QStyle.StandardPixmap.SP_DirIcon),
                                    tr("menu.tools.library"), self.generator_requested, "library")
        self.vector_tool_actions = (
            self.library,
            self.vector_import,
            *self.generator_actions.values(),
        )
        # Caméra : placée avec les outils généraux (pas seulement vectoriel). L'historique des gravures est
        # dans le menu Fichier, les macros dans la fenêtre Paramètres.
        self.tool_actions = (
            *self.tool_actions,
            self.camera,
        )

    def _create_help_actions(self, parent):
        # Version : icône de l'application (définie dans main.py).
        window_icon = (
            parent.windowIcon()
            if hasattr(parent, "windowIcon")
            else QApplication.windowIcon()
        )
        self.version = self._action(
            window_icon, f"{tr('menu.help.version')} {APP_VERSION}"
        )
        self.version.setEnabled(False)
        # Documentation : pages Markdown de doc/, touche F1.
        self.documentation = self._action(
            standard_icon(
                QIcon.ThemeIcon.HelpFaq,
                QStyle.StandardPixmap.SP_DialogHelpButton,
            ),
            tr("menu.help.documentation"),
            self.documentation_requested,
        )
        self.documentation.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.about = self._action(
            standard_icon(
                QIcon.ThemeIcon.HelpAbout,
                QStyle.StandardPixmap.SP_MessageBoxInformation,
            ),
            tr("menu.help.about"),
            self.about_requested,
        )
        # Support : contact par e-mail (voir ui.support_body).
        self.support = self._action(
            standard_icon(QIcon.ThemeIcon.MailMessageNew),
            tr("menu.help.support"),
            self.support_requested,
        )
        # Buy me a coffee : même logo que le bouton de soutien.
        coffee_path = find_resource("buy_me_a_coffee.png")
        self.coffee = self._action(
            QIcon(coffee_path) if coffee_path else QIcon(),
            tr("menu.help.coffee"),
            self.coffee_requested,
        )

    def _create_image_actions(self):
        # Icônes Breeze embarquées, dans la couleur du thème : les mêmes que dans les barres flottantes de
        # l'éditeur vectoriel (annuler, pivoter, supprimer…), quel que soit le thème d'icônes du bureau.
        # Annuler / refaire des réglages image. Les raccourcis Ctrl+Z /
        # Ctrl+Y restent ceux de l'onglet (QShortcut limité à l'onglet), pour
        # ne pas entrer en conflit avec l'annulation de l'éditeur vectoriel.
        self.image_undo = self._action(
            bundled_icon(
                "edit-undo", QStyle.StandardPixmap.SP_ArrowBack
            ),
            tr("ui.img_undo"),
            self.image_undo_requested,
        )
        self.image_redo = self._action(
            bundled_icon(
                "edit-redo", QStyle.StandardPixmap.SP_ArrowForward
            ),
            tr("ui.img_redo"),
            self.image_redo_requested,
        )
        # Image chargée : suppression, rotation, puis miroirs. Elles agissent
        # sur l'image de l'onglet affiché.
        self.image_delete = self._action(
            bundled_icon(
                "edit-delete", QStyle.StandardPixmap.SP_TrashIcon
            ),
            tr("img.delete"),
            self.image_delete_requested,
        )
        self.image_rotate_left = self._action(
            bundled_icon(
                "object-rotate-left",
                QStyle.StandardPixmap.SP_ArrowBack,
            ),
            tr("img.rotate_left"),
            self.image_rotate_requested,
            False,
        )
        self.image_rotate_right = self._action(
            bundled_icon(
                "object-rotate-right",
                QStyle.StandardPixmap.SP_ArrowForward,
            ),
            tr("img.rotate_right"),
            self.image_rotate_requested,
            True,
        )
        # Miroirs cochables : ils gardent l'état.
        self.mirror_h = self._action(
            bundled_icon(
                "object-flip-horizontal", QStyle.StandardPixmap.SP_ArrowLeft
            ),
            tr("img.mirror_h"),
        )
        self.mirror_v = self._action(
            bundled_icon(
                "object-flip-vertical", QStyle.StandardPixmap.SP_ArrowUp
            ),
            tr("img.mirror_v"),
        )
        for action in (self.mirror_h, self.mirror_v):
            action.setCheckable(True)
            action.toggled.connect(self._emit_mirror_changed)
        self.image_reset = self._action(
            bundled_icon(
                "document-revert",
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("img.reset"),
            self.image_reset_requested,
        )
        # Actives seulement avec une image chargée, sur un onglet qui
        # l'affiche (voir update_image_actions_state).
        self.image_actions = (
            self.image_delete,
            self.image_rotate_left,
            self.image_rotate_right,
        )
        self.set_image_actions_enabled(False)
        self.set_mirrors_enabled(False)

    def _create_gcode_actions(self):
        self.estimate = self._action(
            standard_icon(
                "chronometer", QStyle.StandardPixmap.SP_FileDialogInfoView
            ),
            tr("gcode.estimate"),
            self.estimate_requested,
        )
        self.gcode_import = self._action(
            standard_icon(
                "document-import", QStyle.StandardPixmap.SP_FileIcon
            ),
            tr("gcode.import"),
            self.gcode_import_requested,
        )
        # Menu Job : les actions de tous les jours au clavier. Ctrl+G est pris par « Grouper » de l'éditeur
        # vectoriel : touches de fonction, comme « lancer » dans les éditeurs de code (F5).
        self.job_actions = []
        for name, key, shortcut, signal in (
            ("generate", "menu.job.generate", "F5", self.generate_requested),
            ("frame", "menu.job.frame", "F6", self.frame_requested),
            ("frame_contour", "menu.job.frame_contour", "Shift+F6", self.frame_contour_requested),
            ("send", "menu.job.send", "Ctrl+Return", self.send_job_requested),
            ("pause", "menu.job.pause", "F7", self.pause_requested),
            ("resume", "menu.job.resume", "F8", self.resume_requested),
        ):
            action = self._action(QIcon(), tr(key), signal)
            action.setShortcut(QKeySequence(shortcut))
            action.setObjectName(f"job_{name}")
            self.job_actions.append(action)

    def _emit_mirror_changed(self, _checked=False):
        self.mirror_changed.emit(
            self.mirror_h.isChecked(), self.mirror_v.isChecked()
        )