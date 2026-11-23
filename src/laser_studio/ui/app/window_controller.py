"""Contrôleur de la fenêtre : ce qui agit sur la fenêtre entière.

    controller = WindowController(window)
    controller.connect_actions(window.app_actions)

Il abonne la fenêtre aux signaux du menu et de la barre d'outils
(ui/app/menu/), et regroupe les actions qui touchent plusieurs parties de la
fenêtre : thème, langue, aide, caméra, fenêtres de réglages, matrice de test,
résolution et focale de « Graver une image », Stencil Studio.

Le reste a son propre objet, créé par la fenêtre : MainTabs (onglets,
plein écran, panneau du bas), JobDisplay (résultats du job, état du graveur),
ImageToolbarActions (actions de la barre d'outils sur l'image).

La fenêtre (`window`) est le point d'assemblage : le contrôleur y lit les
modèles, contrôleurs et pages qu'elle a construits.
"""

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication

from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import get_current_language, set_language, tr
from laser_studio.ui.about import AboutDialog
from laser_studio.ui.app.theme import apply_app_theme, current_theme_name, normalize_theme_name, page_colors
from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeDialog
from laser_studio.ui.dialogs.dither_comparison import DitherComparisonDialog
from laser_studio.ui.help import HelpDialog
from laser_studio.ui.settings.window import SettingsWindow
from laser_studio.ui.support import SupportDialog
from stencil_studio.controllers.studio import StencilStudioController

# Délai (ms) avant de préchauffer Stencil Studio, une fois la fenêtre affichée.
STENCIL_PRELOAD_DELAY_MS = 3000


class WindowController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._help_dialog = None
        self._settings_windows = {}
        # Pages des fenêtres de réglages (kind -> (page, clé du titre)) et onglets que le menu peut
        # demander par leur nom, inscrits par la fenêtre (add_settings_page, add_main_tab).
        self._settings_pages = {}
        self._main_tabs = {}
        self.camera = None
        self.stencil_studio = None

    # -- menu et barre d'outils

    def connect_actions(self, actions):
        """Abonne la fenêtre aux signaux du menu et de la barre d'outils
        (AppActions). Appelé une fois toute la fenêtre construite."""
        w = self.window
        # Fichier
        actions.save_project_requested.connect(w.project.save)
        actions.gcode_export_requested.connect(
            lambda extension: w.job.export_gcode(extension, w.tab_console_gcode.gcode()))
        actions.open_project_requested.connect(w.project.open)
        actions.recent_project_requested.connect(w.project.open_path)
        actions.quit_requested.connect(w.close)
        # Paramètres et outils
        actions.settings_window_requested.connect(self.show_settings_window)
        actions.language_selected.connect(self.select_language)
        actions.theme_selected.connect(self.change_theme)
        actions.stencil_studio_requested.connect(lambda: self.stencil().open())
        actions.main_tab_requested.connect(self.show_main_tab)
        editor = w.vector_editor
        actions.vector_import_requested.connect(lambda: self.run_in_vector_editor(editor.import_dialog))
        actions.box_generator_requested.connect(lambda: self.run_in_vector_editor(editor.open_box_generator))
        actions.puzzle_generator_requested.connect(lambda: self.run_in_vector_editor(editor.open_puzzle_generator))
        actions.library_requested.connect(lambda: self.run_in_vector_editor(w.library.open))
        actions.ornament_generator_requested.connect(
            lambda: self.run_in_vector_editor(editor.open_ornament_generator))
        actions.keychain_generator_requested.connect(
            lambda: self.run_in_vector_editor(editor.open_keychain_generator))
        actions.camera_requested.connect(self.open_camera_dialog)
        # Affichage
        actions.fullscreen_requested.connect(w.tabs.toggle_current_fullscreen)
        actions.gcode_console_toggled.connect(
            lambda visible: w.tabs.set_optional_visible(w.tab_console_gcode, visible))
        actions.job_queue_toggled.connect(lambda visible: w.tabs.set_optional_visible(w.tab_job_queue, visible))
        # Aide
        actions.documentation_requested.connect(self.show_documentation)
        actions.about_requested.connect(lambda: AboutDialog(w).exec())
        actions.support_requested.connect(lambda: SupportDialog(w).exec())
        actions.coffee_requested.connect(lambda: BuyMeACoffeeDialog(w).exec())
        # Image
        actions.image_undo_requested.connect(w.image_history.undo)
        actions.image_redo_requested.connect(w.image_history.redo)
        actions.image_delete_requested.connect(w.image_actions.delete)
        actions.image_rotate_requested.connect(w.image_actions.rotate)
        actions.mirror_changed.connect(w.image.schedule_processing)
        actions.image_reset_requested.connect(w.image.reset_settings)
        # G-code
        actions.estimate_requested.connect(w.job.estimate)
        actions.generate_requested.connect(w.job.generate)
        actions.gcode_import_requested.connect(w.job.import_gcode)

    def stencil(self):
        """Contrôleur de Stencil Studio, créé à la première demande. Ses exports SVG / DXF arrivent
        dans l'éditeur vectoriel, rangés dans les calques (VectorEditorController.import_stencil_export)."""
        if self.stencil_studio is None:
            w = self.window
            self.stencil_studio = StencilStudioController(
                w, theme=lambda: page_colors(current_theme_name()), language=get_current_language(),
                dialogs=w.dialogs, parent=self)
            self.stencil_studio.export_ready.connect(w.vector_editor.import_stencil_export)
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
        apply_app_theme(QApplication.instance(), theme_name)
        self.window.app_actions.set_theme(theme_name)

        # Stencil Studio ouvert : même thème que LSP
        if self.stencil_studio is not None:
            self.stencil_studio.set_theme(page_colors(theme_name))

    def select_language(self, lang_code):
        """Langue choisie dans le menu : appliquée au prochain démarrage."""
        set_language(lang_code)
        self.window.app_actions.set_language(lang_code)
        self.window.dialogs.info(tr("menu.language.restart_title"), tr("menu.language.restart_body"))

    def show_documentation(self, page="index.md"):
        """Ouvre la fenêtre de documentation (une seule, réutilisée)."""
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(self.window)
        self._help_dialog.show_page(page)

    def add_main_tab(self, name, tab):
        """Onglet que le menu Outils peut demander par son nom (ex. "tab_separation")."""
        self._main_tabs[name] = tab

    def show_main_tab(self, name):
        """Affiche l'onglet central inscrit sous `name` (envoyé par le menu Outils) ; nom inconnu : rien."""
        tab = self._main_tabs.get(name)
        if tab is not None:
            self.window.tabs.show(tab)

    def run_in_vector_editor(self, command):
        """Affiche l'onglet « Graver une image vectorielle », puis lance
        `command` (import SVG / DXF, générateur de boîte, puzzle, boule de Noël)."""
        self.window.tabs.show(self.window.tab_vector_editor)
        command()

    def open_camera_dialog(self):
        """Ouvre le dialogue Caméra (choix appareil, état, actions)."""
        # Importés ici : OpenCV n'est chargé qu'à la première ouverture.
        from laser_studio.controllers.camera import CameraController
        from laser_studio.ui.dialogs.camera import CameraDialog

        w = self.window
        if self.camera is None:
            self.camera = CameraController(
                w,
                bed_size=lambda: (w.machine.bed_w, w.machine.bed_h),
                dialogs=w.dialogs,
            )
            # L'image de la caméra (redressée sur le plateau) s'affiche sous la grille de l'éditeur vectoriel.
            canvas = w.vector_canvas
            self.camera.overlay_ready.connect(canvas.set_camera_background)
            self.camera.overlay_cleared.connect(canvas.clear_camera_background)
            self.camera.overlay_opacity_changed.connect(canvas.set_camera_background_opacity)
        CameraDialog(self.camera, w).exec()

    def show_settings_window(self, kind):
        """Ouvre (ou ramène au premier plan) une fenêtre de réglages : « Paramètres du graveur »
        (kind="machine_params"), « Configuration GRBL » (kind="grbl") ou « Matrice de test »
        (kind="test_matrix"). Créée à la première demande, puis réutilisée."""
        windows = self._settings_windows
        if kind not in windows:
            if kind not in self._settings_pages:
                return                     # page pas (encore) construite
            page, title_key = self._settings_pages[kind]
            windows[kind] = SettingsWindow(self.window, tr(title_key), page, kind)
        windows[kind].bring_to_front()

    def add_settings_page(self, kind, page, title_key):
        """Page affichée par show_settings_window(kind), titre tr(`title_key`)."""
        self._settings_pages[kind] = (page, title_key)

    # -- onglets

    def main_tab_changed(self, index):
        """Onglet Séparation affiché : ses aperçus, en retard, sont refaits."""
        w = self.window
        if w.main_tabs_view.widget(index) is w.tab_separation:
            w.separation.refresh_if_dirty()

    # -- matrice de test

    def generate_test_matrix_and_show(self):
        """Génère la matrice de test, puis ferme sa fenêtre et affiche
        l'aperçu 2D, où le G-Code apparaît. En cas d'erreur, la fenêtre
        reste ouverte pour corriger les réglages."""
        w = self.window
        # Lignes/mm toujours identiques à l'onglet « Graver une image ».
        self.sync_matrix_lines_mm()
        page = w.tab_matrix
        if not w.job.generate_test_matrix(page.matrix_params(), page.is_engraving(),
                                          page.image_test_enabled(), w.matrix_image.build_tile):
            return
        page.window().close()
        w.tabs.show(w.tab_vector_2d)
        w.raise_()
        w.activateWindow()

    def sync_matrix_lines_mm(self):
        """Lignes/mm de « Graver une image » reportées dans la matrice de test
        gravure : le test est fait avec la même densité de lignes que la
        gravure réelle."""
        self.window.tab_matrix.set_lines_mm(self.window.resolution_box.lines_per_mm())

    # -- onglet « Graver une image » : résolution, focale, comparaison des algorithmes

    def machine_focal_changed(self, focal):
        """La focale est une caractéristique physique du laser : tout
        changement dans les Paramètres Machine recale lignes/mm, DPI et
        l'avis sur l'écart des lignes de « Graver une image », quel que soit
        le mode de saisie, et la qualité du pas de remplissage des calques."""
        w = self.window
        w.resolution_box.set_focal(focal)
        w.resolution_box.apply_focal()
        w.layers_tab.refresh_focal_quality()

    def goto_focal_settings(self):
        """Ouvre les Paramètres Machine sur le champ de focale (bouton de la
        résolution de « Graver une image »)."""
        self.show_settings_window("machine_params")
        self.window.tab_machine_params.focal_spin.setFocus()

    def show_dither_comparison(self):
        """Grille de vignettes comparant chaque algorithme de tramage sur l'image
        chargée, avec les réglages actuels ; un clic choisit l'algorithme."""
        image = self.window.image
        thumbnails = image.comparison()
        if thumbnails is None:
            return
        dialog = DitherComparisonDialog(self.window, thumbnails)
        dialog.algorithm_chosen.connect(image.choose_algorithm)
        dialog.exec()
