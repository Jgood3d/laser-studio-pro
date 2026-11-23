"""Contrôleur de la fenêtre : ce qui agit sur la fenêtre entière.

    controller = WindowController(window)
    controller.connect_actions(window.app_actions)

Il abonne la fenêtre aux signaux du menu et de la barre d'outils
(ui/app/menu/), et regroupe les actions qui touchent plusieurs parties de la
fenêtre : thème, langue, aide, caméra, fenêtres de réglages, matrice de test,
résolution et focale de « Graver une image », outils de dessin de l'éditeur
vectoriel.

Le reste a son propre objet, créé par la fenêtre : MainTabs (onglets,
plein écran, panneau du bas), JobDisplay (résultats du job, état du graveur),
ImageToolbarActions (actions de la barre d'outils sur l'image).

La fenêtre (`window`) est le point d'assemblage : le contrôleur y lit les
modèles, contrôleurs et pages qu'elle a construits.
"""

from PyQt6.QtCore import QObject, QSettings, QTimer
from PyQt6.QtWidgets import QApplication

from laser_studio.i18n import set_language, tr
from laser_studio.ui.about import AboutDialog
from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeDialog
from laser_studio.ui.dialogs.dither_comparison import DitherComparisonDialog
from laser_studio.ui.help import HelpDialog
from laser_studio.ui.settings.window import SettingsWindow
from laser_studio.ui.support import SupportDialog
from laser_studio.ui.utils import busy_cursor
from stencil_studio.studio_dialog import open_stencil_studio, preload_stencil_studio

# Délai (ms) avant de préchauffer Stencil Studio, une fois la fenêtre affichée.
STENCIL_PRELOAD_DELAY_MS = 3000


class WindowController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._help_dialog = None
        self._settings_windows = {}
        self.camera = None

    # -- menu et barre d'outils

    def connect_actions(self, actions):
        """Abonne la fenêtre aux signaux du menu et de la barre d'outils
        (AppActions). Appelé une fois toute la fenêtre construite."""
        w = self.window
        # Fichier
        actions.save_project_requested.connect(w.project.save)
        actions.gcode_export_requested.connect(
            lambda extension: w.job.export_gcode(extension, w.txt_console.toPlainText()))
        actions.open_project_requested.connect(w.project.open)
        actions.recent_project_requested.connect(w.project.open_path)
        actions.quit_requested.connect(w.close)
        # Paramètres et outils
        actions.settings_window_requested.connect(self.show_settings_window)
        actions.language_selected.connect(self.select_language)
        actions.theme_selected.connect(self.change_theme)
        actions.stencil_studio_requested.connect(lambda: open_stencil_studio(w))
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

    def schedule_stencil_preload(self):
        """Préchauffe Stencil Studio en arrière-plan une fois la fenêtre
        affichée : « Outils > Stencil Studio » s'ouvre ensuite sans attente."""
        QTimer.singleShot(STENCIL_PRELOAD_DELAY_MS, lambda: preload_stencil_studio(self.window))

    def change_theme(self, theme_name):
        """Bascule de thème à la volée et mémorise le code.

        Codes possibles : dark, light, dusk, warm.
        """
        # Importé ici : le thème n'est chargé qu'au premier changement.
        from laser_studio.ui.app.theme import apply_app_theme, normalize_theme_name

        theme_name = normalize_theme_name(theme_name)
        settings = QSettings("LaserStudioPro", "UIConfig")
        settings.setValue("app_theme", theme_name)
        settings.sync()  # écriture immédiate sous Windows
        apply_app_theme(QApplication.instance(), theme_name)
        self.window.app_actions.set_theme(theme_name)

        # Stencil Studio ouvert : même thème que LSP
        dlg = getattr(self.window, "_stencil_studio_dialog", None)
        if dlg is not None:
            try:
                dlg.sync_theme_from_lsp(theme_name)
            except Exception:
                pass

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

    def show_main_tab(self, tab_attr):
        """Affiche l'onglet central dont l'attribut de la fenêtre est
        `tab_attr` (ex. "tab_separation", envoyé par le menu Outils)."""
        tab = getattr(self.window, tab_attr, None)
        if tab is not None:
            self.window.tabs.show(tab)

    def run_in_vector_editor(self, command):
        """Affiche l'onglet « Graver une image vectorielle », puis lance
        `command` (import SVG / DXF, générateur de boîte, puzzle, boule de Noël)."""
        self.window.tabs.show(self.window.tab_vector_editor)
        command()

    def _ensure_camera(self):
        """Le contrôleur Caméra (créé une fois), branché sur le fond de l'éditeur vectoriel."""
        # Importé ici : OpenCV n'est chargé qu'à la première utilisation.
        from laser_studio.controllers.camera import CameraController

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
        return self.camera

    def open_camera_dialog(self):
        """Ouvre le dialogue Caméra (choix appareil, état, actions)."""
        from laser_studio.ui.dialogs.camera import CameraDialog

        CameraDialog(self._ensure_camera(), self.window).exec()

    def refresh_camera_background(self):
        """Capture la caméra et met l'image en fond de l'éditeur vectoriel (bouton de la barre de l'éditeur).
        Renvoie True si l'image est posée."""
        camera = self._ensure_camera()
        with busy_cursor():
            return bool(camera.refresh_overlay())

    def set_camera_background_enabled(self, enabled):
        """Interrupteur « Fond caméra » de l'éditeur vectoriel : capture et affiche, ou retire l'image."""
        toggle = self.window.vector_camera_toggle
        if enabled:
            if not self.refresh_camera_background():
                toggle.blockSignals(True)      # pas de caméra prête : l'interrupteur revient sur « éteint »
                toggle.setChecked(False)
                toggle.blockSignals(False)
        elif self.camera is not None:
            self.camera.clear_overlay()

    def refresh_camera_clicked(self):
        """Bouton « Actualiser l'image » : recapture, et allume l'interrupteur si l'image est posée."""
        ok = self.refresh_camera_background()
        toggle = self.window.vector_camera_toggle
        if ok and not toggle.isChecked():
            toggle.blockSignals(True)
            toggle.setChecked(True)
            toggle.blockSignals(False)

    def show_settings_window(self, kind):
        """Ouvre (ou ramène au premier plan) une fenêtre de réglages : « Paramètres du graveur »
        (kind="machine_params"), « Configuration GRBL » (kind="grbl") ou « Matrice de test »
        (kind="test_matrix"). Créée à la première demande, puis réutilisée."""
        windows = self._settings_windows
        if kind not in windows:
            w = self.window
            page, title = {
                "grbl": (getattr(w, "tab_grbl_config", None), tr("tab.grbl_config")),
                "machine_params": (getattr(w, "tab_machine_params", None), tr("tab.machine_params")),
                "test_matrix": (getattr(w, "tab_matrix", None), tr("tab.test_matrix")),
            }[kind]
            if page is None:
                return
            windows[kind] = SettingsWindow(w, title, page, kind)
        windows[kind].bring_to_front()

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

    def resolution_changed(self, _lines_mm):
        """Résolution de gravure changée (saisie, DPI, focale, réglages restaurés) :
        la matrice de test et la Séparation la reprennent, l'image est retraitée.
        La matrice et la Séparation, construites après l'onglet image, sont
        absentes lors des tout premiers réglages."""
        w = self.window
        if hasattr(w, "tab_matrix"):
            self.sync_matrix_lines_mm()
        separation = getattr(w, "separation", None)
        if separation is not None:
            separation.resolution_changed()
        w.image.schedule_processing()

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

    def refresh_engrave_layer_combo(self, *_args):
        """Remet à jour la liste « Calque de gravure » de l'onglet image (calques ajoutés,
        supprimés, renommés ou changés de mode)."""
        layers = self.window.layer_manager
        layer = layers.engrave_layer()
        self.window.tab_previews.settings.engrave_layer_combo.set_layers(layers.layers,
                                                                         layer.id if layer else None)

    # -- éditeur vectoriel : outils de la souris, zone de travail

    def set_vector_draw_tool(self, tool):
        """Active un outil de dessin à la souris sur le canevas vectoriel.

        tool: None/'select', 'line', 'rect', 'circle', 'ellipse', 'measure'.
        Rectangle : 3 points. Cercle (du centre vers le rayon) et ellipse (d'un coin du cadre à l'autre) :
        un seul clic-glisser. Échap ou clic droit annule l'outil.
        """
        w = self.window
        layers = w.layer_manager
        if tool and tool not in (None, "select") and not layers.layers:
            w.dialogs.warning(tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            tool = None
        layer = layers.default_svg_layer() if layers.layers else None
        layer_id = layer.id if layer else None
        resolved = None if tool in (None, "select") else tool
        w.vector_canvas.set_draw_tool(resolved, layer_id=layer_id)
        for key, btn in w.vector_draw_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(key == resolved)
            btn.blockSignals(False)

    def update_vector_work_area(self, *_args):
        """Zone de travail de l'éditeur vectoriel aux dimensions physiques du
        graveur (Paramètres Machine), et non à celles du job en cours."""
        machine = self.window.machine
        self.window.vector_canvas.set_work_area(machine.bed_w, machine.bed_h)
