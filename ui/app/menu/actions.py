"""Actions de la fenêtre principale, partagées par le menu et la barre.

Une QAction porte l'icône, le libellé, le raccourci et l'état (actif,
coché) d'une commande. Le menu et la barre d'outils affichent les mêmes
actions : un seul endroit les crée, et un seul endroit émet les signaux.
"""

from PyQt6.QtCore import QObject, QSettings, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication, QStyle

from app_utils import APP_VERSION, find_resource
from i18n import SUPPORTED_LANGUAGES, get_current_language, tr


def standard_icon(theme_icon, fallback=QStyle.StandardPixmap.SP_FileIcon):
    """Icône du thème du système (freedesktop sous Linux), sinon icône
    standard du style Qt, présente sur toutes les plateformes."""
    icon = QIcon.fromTheme(theme_icon)
    if icon.isNull():
        icon = QApplication.style().standardIcon(fallback)
    return icon


def status_dot_icon(color):
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


class AppActions(QObject):
    """Toutes les actions du menu et de la barre d'outils, et leurs signaux.

    AppMenuBar et AppToolBar ne font que ranger ces actions. La fenêtre
    (plus tard un contrôleur) s'abonne aux signaux :

        actions = AppActions(window)
        actions.save_project_requested.connect(window.save_project)

    L'état passe par des méthodes set_… (connexion, langue, thème, actions
    sur l'image) ; les miroirs se lisent sur mirror_h / mirror_v.
    """

    # Fichier
    save_project_requested = pyqtSignal()
    open_project_requested = pyqtSignal()
    recent_project_requested = pyqtSignal(str)  # chemin du projet
    quit_requested = pyqtSignal()
    # Paramètres et outils : "machine_params", "machine", "grbl",
    # "test_matrix"
    settings_window_requested = pyqtSignal(str)
    language_selected = pyqtSignal(str)  # code de langue : "fr", "en"…
    theme_selected = pyqtSignal(str)  # code de thème : "dark", "light"…
    stencil_studio_requested = pyqtSignal()
    main_tab_requested = pyqtSignal(str)  # "tab_separation", "tab_png2svg"
    # Aide
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
    # Connexion au graveur
    refresh_ports_requested = pyqtSignal()
    connection_toggle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_file_actions()
        self._create_settings_actions()
        self._create_tools_actions()
        self._create_help_actions(parent)
        self._create_image_actions()
        self._create_gcode_actions()
        self._create_connection_actions()

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Bouton de connexion : « Déconnecter » / pastille verte si
        connecté, « Connecter GRBL » / pastille rouge sinon."""
        self.connection.setText(
            tr("laser.disconnect") if connected else tr("laser.connect")
        )
        self.connection.setIcon(
            status_dot_icon("#27ae60" if connected else "#e74c3c")
        )

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

    def _create_settings_actions(self):
        # Pas d'entrée QIcon.ThemeIcon pour ces réglages : noms d'icônes
        # freedesktop.
        self.machine_params_window = self._action(
            standard_icon(
                "preferences-system", QStyle.StandardPixmap.SP_ComputerIcon
            ),
            tr("tab.machine_params"),
            self.settings_window_requested,
            "machine_params",
        )
        self.machine_window = self._action(
            standard_icon(
                "network-wired", QStyle.StandardPixmap.SP_DriveNetIcon
            ),
            tr("tab.machine_profiles"),
            self.settings_window_requested,
            "machine",
        )
        self.grbl_window = self._action(
            standard_icon(
                "utilities-terminal",
                QStyle.StandardPixmap.SP_FileDialogContentsView,
            ),
            tr("tab.grbl_config"),
            self.settings_window_requested,
            "grbl",
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

        from app_theme import available_themes, normalize_theme_name

        self.theme_icon = standard_icon(
            "preferences-desktop-theme", QStyle.StandardPixmap.SP_DesktopIcon
        )
        current_theme = normalize_theme_name(
            QSettings("LaserStudioPro", "UIConfig").value("app_theme", "dark")
        )
        self.theme_actions = {}
        for code, label_key in available_themes():
            action = self._action(
                QIcon(), tr(label_key), self.theme_selected, code
            )
            action.setCheckable(True)
            action.setChecked(code == current_theme)
            self.theme_actions[code] = action

    def _create_tools_actions(self):
        # Grille de carrés de test ; « -symbolic » : seule variante présente
        # dans Adwaita.
        self.test_matrix_window = self._action(
            standard_icon(
                "view-grid-symbolic",
                QStyle.StandardPixmap.SP_FileDialogListView,
            ),
            tr("tab.test_matrix"),
            self.settings_window_requested,
            "test_matrix",
        )
        self.stencil_studio = self._action(
            standard_icon(
                "applications-graphics", QStyle.StandardPixmap.SP_DesktopIcon
            ),
            tr("menu.tools.stencil_studio"),
            self.stencil_studio_requested,
        )
        # Raccourcis vers deux onglets centraux (voir show_main_tab).
        self.separation_tab = self._action(
            standard_icon(
                "color-management", QStyle.StandardPixmap.SP_DriveNetIcon
            ),
            tr("sep.tab_title"),
            self.main_tab_requested,
            "tab_separation",
        )
        self.png2svg_tab = self._action(
            standard_icon(
                "draw-bezier-curves", QStyle.StandardPixmap.SP_FileIcon
            ),
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
        # Annuler / refaire des réglages image. Les raccourcis Ctrl+Z /
        # Ctrl+Y restent ceux de l'onglet (QShortcut limité à l'onglet), pour
        # ne pas entrer en conflit avec l'annulation de l'éditeur vectoriel.
        self.image_undo = self._action(
            standard_icon(
                QIcon.ThemeIcon.EditUndo, QStyle.StandardPixmap.SP_ArrowBack
            ),
            tr("ui.img_undo"),
            self.image_undo_requested,
        )
        self.image_redo = self._action(
            standard_icon(
                QIcon.ThemeIcon.EditRedo, QStyle.StandardPixmap.SP_ArrowForward
            ),
            tr("ui.img_redo"),
            self.image_redo_requested,
        )
        # Image chargée : suppression, rotation, puis miroirs. Elles agissent
        # sur l'image de l'onglet affiché.
        self.image_delete = self._action(
            standard_icon(
                QIcon.ThemeIcon.EditDelete, QStyle.StandardPixmap.SP_TrashIcon
            ),
            tr("img.delete"),
            self.image_delete_requested,
        )
        self.image_rotate_left = self._action(
            standard_icon(
                QIcon.ThemeIcon.ObjectRotateLeft,
                QStyle.StandardPixmap.SP_ArrowBack,
            ),
            tr("img.rotate_left"),
            self.image_rotate_requested,
            False,
        )
        self.image_rotate_right = self._action(
            standard_icon(
                QIcon.ThemeIcon.ObjectRotateRight,
                QStyle.StandardPixmap.SP_ArrowForward,
            ),
            tr("img.rotate_right"),
            self.image_rotate_requested,
            True,
        )
        # Pas d'équivalent QIcon.ThemeIcon pour les miroirs : nom d'icône
        # freedesktop. Cochables : ils gardent l'état.
        self.mirror_h = self._action(
            standard_icon(
                "object-flip-horizontal", QStyle.StandardPixmap.SP_ArrowLeft
            ),
            tr("img.mirror_h"),
        )
        self.mirror_v = self._action(
            standard_icon(
                "object-flip-vertical", QStyle.StandardPixmap.SP_ArrowUp
            ),
            tr("img.mirror_v"),
        )
        for action in (self.mirror_h, self.mirror_v):
            action.setCheckable(True)
            action.toggled.connect(self._emit_mirror_changed)
        self.image_reset = self._action(
            standard_icon(
                QIcon.ThemeIcon.DocumentRevert,
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

    def _create_connection_actions(self):
        self.refresh_ports = self._action(
            standard_icon(
                QIcon.ThemeIcon.ViewRefresh,
                QStyle.StandardPixmap.SP_BrowserReload,
            ),
            tr("usb.refresh_ports"),
            self.refresh_ports_requested,
        )
        self.connection = self._action(
            QIcon(), tr("laser.connect"), self.connection_toggle_requested
        )

    def _emit_mirror_changed(self, _checked=False):
        self.mirror_changed.emit(
            self.mirror_h.isChecked(), self.mirror_v.isChecked()
        )
