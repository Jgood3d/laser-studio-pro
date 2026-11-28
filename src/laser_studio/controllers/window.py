"""Contrôleur de la fenêtre : les actions qui touchent plusieurs parties de la fenêtre à la fois.

    controller = WindowController(window, forms=WindowForms(window), dialogs=dialogs, actions=app_actions, ...)

Thème, langue, aide, historique des gravures, Stencil Studio, caméra (fond de l'éditeur vectoriel),
fenêtres de réglages, matrice de test, résolution et focale de « Graver une image ».

Il reçoit à sa création ce dont il se sert (modèles, contrôleurs, pages) : la fenêtre le crée une fois
construites toutes ses parties, et branche elle-même le menu et la barre d'outils sur ces parties
(FullLaserStudio._connect_app_actions). `parent` (la fenêtre) ne sert que de parent Qt aux fenêtres
qu'il fait ouvrir. Il ne construit aucune fenêtre : `forms` (ui/app/window_forms.py) les ouvre pour lui.
"""

from types import SimpleNamespace

from PyQt6.QtCore import QObject, QTimer

from laser_studio.controllers.job_history import clear_history, export_history
from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import get_current_language, set_language, tr
from laser_studio.ui.app.theme import current_theme_name, normalize_theme_name, page_colors
from stencil_studio.controllers.studio import StencilStudioController

# Délai (ms) avant de préchauffer Stencil Studio, une fois la fenêtre affichée.
STENCIL_PRELOAD_DELAY_MS = 3000
# Pages réunies dans la fenêtre « Paramètres » (liste des catégories à gauche), dans cet ordre.
SETTINGS_CATEGORIES = ("machine_params", "grbl", "macros", "appearance", "toolbar")


class WindowController(QObject):
    """`forms` : WindowForms ; `dialogs` : UserDialogs ; `actions` : AppActions (thème, langue cochés) ;
    `tabs` : MainTabs ; `machine` : MachineConfig ; `job` : JobController ; `image` : ImageController ;
    `job_history` : JobHistory ; `vector` : éditeur vectoriel (`controller`, `canvas`, `tab`) ;
    `pages` : pages et onglets (`machine_params`, `test_matrix`, `matrix_image`, `resolution`, `layers`,
    `preview`) ; `settings_pages` : {kind: (page, clé du titre)} des fenêtres de réglages ;
    `main_tabs` : {nom: onglet} que le menu Outils peut demander."""

    def __init__(self, parent=None, *, forms, dialogs, actions=None, tabs=None, machine=None, job=None,
                 image=None, job_history=None, vector=None, pages=None, settings_pages=None, main_tabs=None,
                 placement=None):
        super().__init__(parent)
        self.window = parent
        self.forms = forms
        self.dialogs = dialogs
        self.actions = actions
        self.tabs = tabs
        self.machine = machine
        self.job = job
        self.image = image
        self.job_history = job_history
        self.placement = placement
        self.vector = vector
        self.pages = SimpleNamespace(**(pages or {}))
        self._settings_pages = dict(settings_pages or {})
        self._main_tabs = dict(main_tabs or {})
        self.camera = None
        self.stencil_studio = None

    def stencil(self):
        """Contrôleur de Stencil Studio, créé à la première demande. Ses exports SVG / DXF arrivent
        dans l'éditeur vectoriel, rangés dans les calques (VectorImporter.import_stencil_export)."""
        if self.stencil_studio is None:
            self.stencil_studio = StencilStudioController(
                self.window, theme=lambda: page_colors(current_theme_name()), language=get_current_language(),
                dialogs=self.dialogs, parent=self)
            self.stencil_studio.export_ready.connect(self.vector.controller.importer.import_stencil_export)
        return self.stencil_studio

    def schedule_stencil_preload(self):
        """Préchauffe Stencil Studio en arrière-plan une fois la fenêtre
        affichée : « Outils > Stencil Studio » s'ouvre ensuite sans attente."""
        QTimer.singleShot(STENCIL_PRELOAD_DELAY_MS, lambda: self.stencil().preload())

    def change_theme(self, theme_name):
        """Bascule de thème à la volée et mémorise le code.

        Codes possibles : dark, light, dusk, warm.
        """
        theme_name = normalize_theme_name(theme_name)
        ui_preferences().set("app_theme", theme_name)
        self.forms.apply_theme(theme_name)
        self.actions.set_theme(theme_name)

        # Stencil Studio ouvert : même thème que LSP
        if self.stencil_studio is not None:
            self.stencil_studio.set_theme(page_colors(theme_name))

    def select_language(self, lang_code):
        """Langue choisie dans le menu : appliquée au prochain démarrage."""
        set_language(lang_code)
        self.actions.set_language(lang_code)
        self.dialogs.info(tr("menu.language.restart_title"), tr("menu.language.restart_body"))

    def show_documentation(self, page="index.md"):
        """Ouvre la fenêtre de documentation (une seule, réutilisée)."""
        self.forms.help(page)

    def show_main_tab(self, name):
        """Affiche l'onglet central inscrit sous `name` (envoyé par le menu Outils) ; nom inconnu : rien."""
        tab = self._main_tabs.get(name)
        if tab is not None:
            self.tabs.show(tab)

    def run_in_vector_editor(self, command):
        """Affiche l'onglet « Graver une image vectorielle », puis lance
        `command` (import SVG / DXF, générateur de boîte, puzzle, boule de Noël)."""
        self.tabs.show(self.vector.tab)
        command()

    def _ensure_camera(self):
        """Le contrôleur Caméra (créé une fois), branché sur le fond de l'éditeur vectoriel."""
        # Importé ici : OpenCV n'est chargé qu'à la première utilisation.
        from laser_studio.controllers.camera import CameraController

        if self.camera is None:
            self.camera = CameraController(
                self.window,
                bed_size=lambda: (self.machine.bed_w, self.machine.bed_h),
                dialogs=self.dialogs,
            )
            # L'image de la caméra (redressée sur le plateau) s'affiche sous la grille de l'éditeur vectoriel.
            canvas = self.vector.canvas
            self.camera.overlay_ready.connect(canvas.set_camera_background)
            self.camera.overlay_cleared.connect(canvas.camera.clear)
            self.camera.overlay_opacity_changed.connect(canvas.camera.set_opacity)
        return self.camera

    def show_job_history(self):
        """Fenêtre « Historique des gravures » (non modale, une seule à la fois)."""
        history, dialogs = self.job_history, self.dialogs
        self.forms.job_history(history, on_export=lambda: export_history(history, dialogs),
                               on_clear=lambda: clear_history(history, dialogs))

    def open_camera_dialog(self):
        """Ouvre le dialogue Caméra (choix appareil, état, actions)."""
        self.forms.camera(self._ensure_camera())

    def refresh_camera_background(self):
        """Demande l'épaisseur de la matière, capture la caméra et met l'image en fond de l'éditeur vectoriel.
        Renvoie True si l'image est posée (False si annulé ou si la caméra n'est pas prête)."""
        camera = self._ensure_camera()
        profile = camera.profile
        if profile is None or not profile.is_ready:
            camera.refresh_overlay()                   # affiche le message « calibrez / alignez d'abord »
            return False
        thickness = self.dialogs.ask_number(
            tr("camera.thickness_title"),
            tr("camera.thickness_label").format(tag=f"{profile.alignment.tag_height_mm:g}"),
            camera.overlay_thickness_mm, 0.0, 200.0,
        )
        if thickness is None:
            return False
        with self.forms.busy():
            return bool(camera.refresh_overlay(thickness_mm=thickness))

    def set_camera_background_enabled(self, enabled):
        """Interrupteur « Fond caméra » de l'éditeur vectoriel : capture et affiche, ou retire l'image."""
        if enabled:
            if not self.refresh_camera_background():
                # Pas de caméra prête : l'interrupteur revient sur « éteint ».
                self.vector.tab.show_camera_background(False)
        elif self.camera is not None:
            self.camera.clear_overlay()

    def refresh_camera_clicked(self):
        """Bouton « Actualiser l'image » : recapture, et allume l'interrupteur si l'image est posée."""
        if self.refresh_camera_background():
            self.vector.tab.show_camera_background(True)

    def show_settings_window(self, kind):
        """Ouvre (ou ramène au premier plan) une fenêtre de réglages : « Paramètres » sur la page « Paramètres
        du graveur » (kind="machine_params") ou « Configuration GRBL » (kind="grbl"), ou la « Matrice de test »
        (kind="test_matrix"), un outil dans sa propre fenêtre. Créée à la première demande, puis réutilisée."""
        if kind not in self._settings_pages:
            return                     # page pas (encore) construite
        if kind in SETTINGS_CATEGORIES:
            pages = [(key, tr(self._settings_pages[key][1]), self._settings_pages[key][0])
                     for key in SETTINGS_CATEGORIES if key in self._settings_pages]
            self.forms.settings_categories(tr("menu.settings"), pages, kind)
            return
        page, title_key = self._settings_pages[kind]
        self.forms.settings_window(kind, tr(title_key), page)

    # -- matrice de test

    def generate_test_matrix_and_show(self):
        """Génère la matrice de test, puis ferme sa fenêtre et affiche
        l'aperçu 2D, où le G-Code apparaît. En cas d'erreur, la fenêtre
        reste ouverte pour corriger les réglages."""
        # Lignes/mm toujours identiques à l'onglet « Graver une image ».
        self.sync_matrix_lines_mm()
        page = self.pages.test_matrix
        if not self.job.generate_test_matrix(page.matrix_params(), page.is_engraving(),
                                             page.image_test_enabled(), self.pages.matrix_image.build_tile):
            return
        page.window().close()
        self.tabs.show(self.pages.preview)
        if self.window is not None:
            self.window.raise_()
            self.window.activateWindow()

    def sync_matrix_lines_mm(self):
        """Lignes/mm de « Graver une image » reportées dans la matrice de test
        gravure : le test est fait avec la même densité de lignes que la
        gravure réelle."""
        self.pages.test_matrix.set_lines_mm(self.placement.lines_mm)

    # -- onglet « Graver une image » : résolution, focale, comparaison des algorithmes

    def machine_focal_changed(self, focal):
        """La focale est une caractéristique physique du laser : tout
        changement dans les Paramètres Machine recale lignes/mm, DPI et
        l'avis sur l'écart des lignes de « Graver une image », quel que soit
        le mode de saisie, et la qualité du pas de remplissage des calques."""
        self.pages.resolution.set_focal(focal)
        self.pages.resolution.apply_focal()
        self.pages.layers.refresh_focal_quality()

    def goto_focal_settings(self):
        """Ouvre les Paramètres Machine sur le champ de focale (bouton de la
        résolution de « Graver une image »)."""
        self.show_settings_window("machine_params")
        self.pages.machine_params.focal_spin.setFocus()

    def show_dither_comparison(self):
        """Grille de vignettes comparant chaque algorithme de tramage sur l'image
        chargée, avec les réglages actuels ; un clic choisit l'algorithme."""
        image = self.image
        thumbnails = image.comparison()
        if thumbnails is None:
            return
        self.forms.dither_comparison(thumbnails, image.choose_algorithm)
