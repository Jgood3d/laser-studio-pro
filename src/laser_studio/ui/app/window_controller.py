"""Contrôleur de la fenêtre : reçoit les demandes de l'interface et agit.

Il abonne la fenêtre aux signaux du menu et de la barre d'outils
(ui/app/menu/), et regroupe ce qui agit sur toute la fenêtre : thème,
langue, onglets annexes, état de la connexion, actions de la barre
d'outils sur l'image de l'onglet courant, affichage des résultats du job
(console, statistiques, barre de progression, aperçu 2D). Il deviendra un
vrai contrôleur, séparé de la fenêtre.
"""

from contextlib import contextmanager

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton, QVBoxLayout
from PyQt6.QtCore import QSettings, Qt, QTimer
from laser_studio.gcode import MATRIX_ENGRAVE
from laser_studio.i18n import set_language, tr
from laser_studio.ui.about import AboutDialog
from laser_studio.ui.help import HelpDialog
from laser_studio.ui.app.menu import AppActions, AppMenuBar, AppToolBar
from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeDialog
from laser_studio.ui.support import SupportDialog
from stencil_studio.studio_dialog import open_stencil_studio, preload_stencil_studio

# Onglets facultatifs (menu Affichage) : clé de UIConfig qui mémorise s'ils
# sont affichés, et état au premier démarrage.
GCODE_CONSOLE_SETTING = "show_gcode_console"
JOB_QUEUE_SETTING = "show_job_queue"
OPTIONAL_TABS = {
    "tab_console_gcode": (GCODE_CONSOLE_SETTING, False),
    "tab_job_queue": (JOB_QUEUE_SETTING, True),
}


class WindowControllerMixin:
    def change_theme(self, theme_name):
        """Bascule de thème à la volée et mémorise le code.

        Codes possibles : dark, light, dusk, warm.
        """
        from laser_studio.ui.app.theme import apply_app_theme, normalize_theme_name

        theme_name = normalize_theme_name(theme_name)
        app = QApplication.instance()
        settings = QSettings("LaserStudioPro", "UIConfig")
        settings.setValue("app_theme", theme_name)
        settings.sync()  # écriture immédiate sous Windows
        apply_app_theme(app, theme_name)

        actions = getattr(self, "app_actions", None)
        if actions is not None:
            actions.set_theme(theme_name)

        # Stencil Studio ouvert : même thème que LSP
        dlg = getattr(self, "_stencil_studio_dialog", None)
        if dlg is not None:
            try:
                dlg.sync_theme_from_lsp(theme_name)
            except Exception:
                pass

    def _build_app_menus(self):
        """Menu et barre d'outils : actions partagées, abonnées à la fenêtre.

        AppActions crée les actions et émet les signaux ; AppMenuBar et
        AppToolBar ne font que les ranger.
        """
        actions = self.app_actions = AppActions(self)
        self.app_menu_bar = AppMenuBar(actions)
        self.setMenuBar(self.app_menu_bar)
        self.main_toolbar = AppToolBar(actions, self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_toolbar)
        self._connect_app_actions(actions)
        self.project.refresh_recent_projects()
        self.update_connection_widgets()
        # Préchauffe Stencil Studio en arrière-plan une fois la fenêtre affichée :
        # « Outils > Stencil Studio » s'ouvre ensuite sans attente.
        QTimer.singleShot(3000, lambda: preload_stencil_studio(self))

    def _connect_app_actions(self, actions):
        """Abonne la fenêtre aux signaux du menu et de la barre d'outils."""
        # Fichier
        actions.save_project_requested.connect(self.project.save)
        actions.gcode_export_requested.connect(
            lambda extension: self.job.export_gcode(extension, self.txt_console.toPlainText())
        )
        actions.open_project_requested.connect(self.project.open)
        actions.recent_project_requested.connect(self.project.open_path)
        actions.quit_requested.connect(self.close)
        # Paramètres et outils
        actions.settings_window_requested.connect(self.show_settings_window)
        actions.language_selected.connect(self._on_language_selected)
        actions.theme_selected.connect(self.change_theme)
        actions.stencil_studio_requested.connect(
            lambda: open_stencil_studio(self)
        )
        actions.main_tab_requested.connect(self.show_main_tab)
        actions.vector_import_requested.connect(
            lambda: self._run_in_vector_editor(self.vector_editor.import_dialog)
        )
        actions.box_generator_requested.connect(
            lambda: self._run_in_vector_editor(self.vector_editor.open_box_generator)
        )
        actions.puzzle_generator_requested.connect(
            lambda: self._run_in_vector_editor(self.vector_editor.open_puzzle_generator)
        )
        actions.library_requested.connect(
            lambda: self._run_in_vector_editor(self.library.open)
        )
        actions.ornament_generator_requested.connect(
            lambda: self._run_in_vector_editor(self.vector_editor.open_ornament_generator)
        )
        actions.camera_requested.connect(self.open_camera_dialog)
        # Affichage
        actions.fullscreen_requested.connect(self.toggle_current_tab_fullscreen)

        actions.gcode_console_toggled.connect(self.set_gcode_console_visible)
        actions.job_queue_toggled.connect(self.set_job_queue_visible)
        # Aide
        actions.documentation_requested.connect(self.show_documentation)
        actions.about_requested.connect(lambda: AboutDialog(self).exec())
        actions.support_requested.connect(lambda: SupportDialog(self).exec())
        actions.coffee_requested.connect(
            lambda: BuyMeACoffeeDialog(self).exec()
        )
        # Image
        actions.image_undo_requested.connect(self.undo_image_settings)
        actions.image_redo_requested.connect(self.redo_image_settings)
        actions.image_delete_requested.connect(self._on_toolbar_delete_image)
        actions.image_rotate_requested.connect(
            lambda clockwise: self._on_toolbar_rotate_image(
                clockwise=clockwise
            )
        )
        actions.mirror_changed.connect(self.update_image_processing)
        actions.image_reset_requested.connect(self.reset_image_settings)
        # G-code
        actions.estimate_requested.connect(self.job.estimate)
        actions.generate_requested.connect(self.job.generate)
        actions.gcode_import_requested.connect(self.job.import_gcode)
        actions.keychain_generator_requested.connect(
            lambda: self._run_in_vector_editor(self.vector_editor.open_keychain_generator)
        )

    def show_documentation(self, page="index.md"):
        """Ouvre la fenêtre de documentation (une seule, réutilisée)."""
        if getattr(self, "_help_dialog", None) is None:
            self._help_dialog = HelpDialog(self)
        self._help_dialog.show_page(page)

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

    def _run_in_vector_editor(self, command):
        """Affiche l'onglet « Graver une image vectorielle », puis lance
        `command` (import SVG / DXF, générateur de boîte, puzzle, boule de Noël)."""
        self.show_main_tab("tab_vector_editor")
        command()

    def set_optional_tab_visible(self, tab_attr, visible):
        """Affiche ou masque un onglet facultatif (OPTIONAL_TABS, menu
        Affichage), et mémorise ce choix pour le prochain démarrage.

        Ouvert en plein écran (sorti des onglets), il n'est pas touché. Le
        réglage n'est écrit que s'il change.
        """
        index = self.main_tabs_view.indexOf(getattr(self, tab_attr))
        if index != -1:
            self.main_tabs_view.setTabVisible(index, visible)
        if self.optional_tab_was_visible(tab_attr) != bool(visible):
            settings = QSettings("LaserStudioPro", "UIConfig")
            settings.setValue(OPTIONAL_TABS[tab_attr][0], bool(visible))
            settings.sync()  # écriture immédiate sous Windows

    @staticmethod
    def optional_tab_was_visible(tab_attr):
        """Onglet facultatif affiché à la dernière utilisation ? (au premier
        démarrage : l'état par défaut de OPTIONAL_TABS)"""
        key, default = OPTIONAL_TABS[tab_attr]
        value = QSettings("LaserStudioPro", "UIConfig").value(key, default)
        return value in (True, "true", "1", 1)

    def set_gcode_console_visible(self, visible):
        """Onglet « Console / G-Code » : masqué au premier démarrage."""
        self.set_optional_tab_visible("tab_console_gcode", visible)

    def gcode_console_was_visible(self):
        return self.optional_tab_was_visible("tab_console_gcode")

    def set_job_queue_visible(self, visible):
        """Onglet « File d'attente » : affiché au premier démarrage."""
        self.set_optional_tab_visible("tab_job_queue", visible)

    def job_queue_was_visible(self):
        return self.optional_tab_was_visible("tab_job_queue")

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
            return self.separation.has_image()
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

    def update_connection_widgets(self):
        """Met le bouton de connexion en accord avec l'état du port.

        Panneau « Connexion » : « Déconnecter » / pastille verte si connecté,
        « Connecter GRBL » / pastille rouge sinon. Verrouille ou déverrouille
        aussi les commandes de la machine.
        """
        connected = self.connection.is_connected()
        # Bouton de connexion, pilotage, actions de job et console directe :
        # verrouillés tant que le graveur n'est pas connecté. La position du job reste modifiable
        # (elle sert aussi à générer le G-Code hors connexion).
        machine_panel = getattr(self, "machine_panel", None)
        if machine_panel is not None:
            machine_panel.set_connected(connected)

    def _on_language_selected(self, lang_code):
        set_language(lang_code)
        self.app_actions.set_language(lang_code)
        QMessageBox.information(
            self,
            tr("menu.language.restart_title"),
            tr("menu.language.restart_body"),
        )

    def open_camera_dialog(self):
        """Ouvre le dialogue Caméra (choix appareil, état, actions)."""
        from laser_studio.controllers.camera import CameraController
        from laser_studio.ui.dialogs.camera import CameraDialog

        if getattr(self, "camera", None) is None:
            self.camera = CameraController(
                self,
                bed_size=lambda: (self.machine.bed_w, self.machine.bed_h),
                dialogs=self.dialogs,
            )
        CameraDialog(self.camera, self).exec()

    # -- résultats du job (JobController) : console, statistiques, aperçu 2D

    def on_gcode_generation_started(self):
        """Génération lancée : barre de progression, et l'aperçu 2D est montré
        aussitôt (il se remplit à la fin, voir on_gcode_generated)."""
        self.statusBar().show_progress(0, tr("gen.in_progress"))
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)

    def on_gcode_generation_progress(self, pct):
        self.statusBar().show_progress(pct, tr("gen.in_progress_pct").format(pct=pct))

    def on_gcode_generation_error(self, error_text):
        self.statusBar().hide_progress()
        self.log_message(f"\n; ERREUR DE GÉNÉRATION :\n; {error_text}")
        QMessageBox.critical(self, tr("gen.failed_title"), tr("gen.failed_body").format(error=error_text))

    def on_gcode_generated(self, gcode_str, num_lines, avg_power, time_str):
        """G-Code prêt : console, statistiques, aperçu 2D."""
        self.statusBar().show_progress(100, tr("gen.done"))
        self.statusBar().hide_progress(delay_ms=1500)
        self.txt_console.setPlainText(gcode_str)
        self.tab_vector_2d.job_stats_panel.set_stats(tr("gen.stat_lines").format(n=num_lines),
                                                     tr("gen.stat_power").format(value=f"{avg_power:.1f}"),
                                                     tr("gen.stat_time").format(value=time_str))
        # « Fichier > Enregistrer le G-Code » : actif une fois le G-Code généré.
        self.app_actions.set_gcode_export_enabled(True)
        self.plot_gcode_preview(gcode_str)
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)

    def show_imported_gcode(self, gcode_text, path):
        """Affiche un fichier G-Code importé (JobController.import_gcode) dans
        la console et l'aperçu 2D."""
        self.txt_console.setPlainText(gcode_text)
        num_lines = len([l for l in gcode_text.split('\n') if l.strip()])
        self.tab_vector_2d.job_stats_panel.set_stats(tr("gen.stat_lines").format(n=num_lines),
                                                     tr("gen.stat_power_imported"),
                                                     tr("gen.stat_time_imported"))
        self.plot_gcode_preview(gcode_text)
        # « Fichier > Enregistrer le G-Code » : le G-Code importé peut être réenregistré.
        self.app_actions.set_gcode_export_enabled(True)
        self.main_tabs_view.setCurrentWidget(self.tab_vector_2d)
        self.log_message(tr("gcode.imported_from").format(path=path))

    def _layer_colors(self):
        """Couleur de chaque calque, par nom (le premier calque d'un nom donné)."""
        colors = {}
        for layer in self.layer_manager.layers:
            colors.setdefault(layer.name, layer.color)
        return colors

    def plot_gcode_preview(self, gcode_text):
        """Dessine `gcode_text` dans l'aperçu 2D (Preview2DTab.show_gcode)."""
        self._last_gcode_text = gcode_text
        matrix = self.job.last_test_matrix_params or {}
        try:
            self.tab_vector_2d.show_gcode(gcode_text, self._layer_colors(),
                                          matrix_engrave=matrix.get("mode") == MATRIX_ENGRAVE)
        except Exception as e:
            # Ne jamais laisser l'aperçu 2D silencieusement vide : si le G-Code
            # (notamment un fichier importé d'un autre outil) contient une
            # ligne inattendue qui fait planter l'analyse, on le signale.
            self.log_message(f"\n; ERREUR aperçu 2D : {e}")
            QMessageBox.warning(self, tr("gen.preview_error_title"),
                                tr("gen.preview_error_body").format(error=e))

    # -- graveur (EngraverController, MachineConnection) : affichage

    def _connect_machine_signals(self):
        """Abonne l'affichage aux signaux de la connexion au graveur et de son
        contrôleur (self.engraver)."""
        c = self.connection
        c.connection_changed.connect(lambda _connected: self.update_connection_widgets())
        c.status_updated.connect(self._on_status_updated)
        c.log.connect(self.log_message)
        c.position_lost.connect(lambda: self.log_message(tr("laser.position_lost_log")))
        c.stream_progress.connect(
            lambda current, total: self.machine_panel.progress_bar.setValue(
                int((current / total) * 100) if total else 0))
        c.stream_lines_sent.connect(self.machine_panel.sent_gcode_log.append_lines)
        c.stream_lines_acked.connect(lambda acked: self.tab_vector_2d.set_lines_acked(acked))
        c.reconnecting.connect(lambda: self.log_message(tr("laser.reconnecting")))
        e = self.engraver
        e.log.connect(self.log_message)
        e.ports_changed.connect(self.machine_panel.connection_panel.set_ports)
        e.disconnected.connect(lambda: self._update_dro_display(None, None, None, None))
        e.direct_job_started.connect(self._on_direct_job_started)
        e.direct_job_finished.connect(lambda: self.machine_panel.jog_panel.set_send_enabled(True))
        e.stream_starting.connect(self._on_stream_starting)
        e.stream_ended.connect(self._on_stream_ended)
        e.gcode_restored.connect(self.txt_console.setPlainText)
        e.job_done.connect(self._beep_job_done)

    def _on_status_updated(self, state, x, y, z):
        """État et position du graveur (sondage hors job, thread d'envoi
        pendant un job) : affichage, position de la tête sur l'aperçu 2D,
        traits déjà gravés en rouge pendant un job."""
        self._update_dro_display(state, x, y, z)
        preview = getattr(self, "tab_vector_2d", None)
        if preview is None:
            return
        preview.set_head_position(x, y)
        if self.connection.is_streaming():
            preview.update_burn(x, y)

    def _update_dro_display(self, state, x, y, z):
        """Transmet l'état (cadre Connexion) et la position (sous le pilotage)
        au panneau machine (MachinePanel.set_status)."""
        machine_panel = getattr(self, "machine_panel", None)
        if machine_panel is None:
            return
        machine_panel.set_status(state, x, y, z)
        # Déconnecté : plus de position connue, le point de la tête disparaît de l'aperçu 2D.
        if state is None and getattr(self, "tab_vector_2d", None) is not None:
            self.tab_vector_2d.clear_head_position()

    def _on_direct_job_started(self):
        """« Envoyer au laser » : bouton d'envoi grisé pendant le job, « Répéter »
        disponible, suivi du G-Code envoyé remis à zéro."""
        self.machine_panel.jog_panel.set_send_enabled(False)
        self.machine_panel.job_actions_panel.set_repeat_enabled(True)
        self.machine_panel.sent_gcode_log.clear_lines()
        self.machine_panel.sent_gcode_log.append_lines([tr("queue.sent_log_direct")])

    def _on_stream_starting(self, gcode_text):
        """Un envoi commence : barre de progression à zéro ; l'aperçu 2D doit
        montrer le G-Code envoyé (un job de la file n'est pas forcément celui
        affiché) et le tracé « déjà gravé » repart de zéro."""
        self.machine_panel.progress_bar.setValue(0)
        if gcode_text != getattr(self, "_last_gcode_text", None):
            self.plot_gcode_preview(gcode_text)
        else:
            self.tab_vector_2d.reset_burn()

    def _on_stream_ended(self, clean_finish):
        """Un envoi se termine : repère de fin dans le suivi, aperçu 2D."""
        self.machine_panel.sent_gcode_log.mark_end(clean_finish)
        self.tab_vector_2d.finish_burn(clean_finish)

    @staticmethod
    def _beep_job_done():
        """Signal sonore de fin de job (2 bips espacés), pour être prévenu même
        sans regarder l'écran (gravure longue, utilisateur dans une autre pièce)."""
        QTimer.singleShot(0, QApplication.beep)
        QTimer.singleShot(250, QApplication.beep)

    def _set_homing_available(self, available, tip):
        """Cases « Inclure $H » (Configuration GRBL) et homing de la matrice de
        test : grisées (et décochées) si le graveur n'a pas de homing.
        Renvoie True si une case cochée a été décochée."""
        unchecked = False
        for name in ("chk_homing", "chk_mat_homing"):
            checkbox = getattr(self, name, None)
            if checkbox is None:
                continue
            if not available and checkbox.isChecked():
                checkbox.setChecked(False)
                unchecked = True
            checkbox.setEnabled(available)
            checkbox.setToolTip(tip)
        return unchecked

    # -- éditeur vectoriel : affichage (la logique est dans VectorEditorController)

    def update_vector_work_area(self, *args):
        """Synchronise la zone de travail de l'éditeur vectoriel avec les
        dimensions physiques du graveur (onglet 'Paramètres Machine'), et non
        plus avec les dimensions du job en cours."""
        if hasattr(self, "vector_canvas") and hasattr(self, "machine"):
            self.vector_canvas.set_work_area(self.machine.bed_w, self.machine.bed_h)

    def on_layers_changed(self):
        """Les calques ont changé (LayersModel.changed : couleur, mode,
        puissance, ajout/suppression...) : on rafraîchit les couleurs des
        objets du canevas et la liste « Calque de gravure » de l'onglet image.
        Le tableau de l'onglet Calques se met à jour seul, abonné au modèle."""
        if hasattr(self, "vector_canvas"):
            self.vector_canvas.refresh_all()
        self._refresh_engrave_layer_combo()

    def _refresh_engrave_layer_combo(self):
        """Remet à jour la liste « Calque de gravure » de l'onglet image (calques ajoutés, supprimés,
        renommés ou changés de mode). Sans effet tant que l'onglet n'est pas construit."""
        combo = getattr(getattr(getattr(self, "tab_previews", None), "settings", None), "engrave_layer_combo", None)
        if combo is not None:
            layer = self.layer_manager.engrave_layer()
            combo.set_layers(self.layer_manager.layers, layer.id if layer else None)

    def _on_engrave_layer_chosen(self, layer_id):
        """Calque de gravure choisi dans la liste de l'onglet image : sa vitesse et sa puissance
        deviennent celles de la gravure (LayersModel.engrave_layer)."""
        self.layer_manager.select_engrave_layer(layer_id)

    def set_vector_draw_tool(self, tool):
        """Active un outil de dessin à la souris sur le canevas vectoriel.

        tool: None/'select', 'line', 'rect', 'circle', 'ellipse', 'measure'.
        Rectangle : 3 points. Cercle (du centre vers le rayon) et ellipse (d'un coin du cadre à l'autre) :
        un seul clic-glisser. Échap ou clic droit annule l'outil.
        """
        if not hasattr(self, "vector_canvas"):
            return
        if tool and tool not in (None, "select") and not self.layer_manager.layers:
            self.dialogs.warning(tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            tool = None
        layer = self.layer_manager.default_svg_layer() if self.layer_manager.layers else None
        layer_id = layer.id if layer else None
        resolved = None if tool in (None, "select") else tool
        self.vector_canvas.set_draw_tool(resolved, layer_id=layer_id)
        for key, btn in getattr(self, "_vector_draw_buttons", {}).items():
            btn.blockSignals(True)
            btn.setChecked(key == resolved)
            btn.blockSignals(False)

    def toggle_fullscreen_vector_editor(self):
        """Ouvre l'éditeur vectoriel (texte/formes/SVG) dans une fenêtre à
        part, maximisée, pour travailler plus confortablement. Fermer cette
        fenêtre (bouton dédié, Échap, ou la croix) remet l'éditeur à sa place
        normale dans l'onglet."""
        idx = self.main_tabs_view.indexOf(self.tab_vector_editor)
        if idx == -1:
            return  # déjà sorti (fenêtre plein écran probablement déjà ouverte)

        dialog = QDialog(self)
        # Fenêtre indépendante à part entière (pas une simple boîte de
        # dialogue) : ça lui donne les boutons minimiser/agrandir/fermer
        # standards de Windows et un vrai comportement plein écran.
        dialog.setWindowFlags(Qt.WindowType.Window)
        dialog.setWindowTitle(tr("vector.fullscreen_title"))

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(4, 4, 4, 4)

        btn_close_fullscreen = QPushButton(
    tr("vector.close_fullscreen")
)
        btn_close_fullscreen.setStyleSheet("background-color: #8f2b2b; color: white; padding: 6px; font-weight: bold;")
        btn_close_fullscreen.clicked.connect(dialog.close)
        dlg_layout.addWidget(btn_close_fullscreen)

        dlg_layout.addWidget(self.tab_vector_editor)
        self.tab_vector_editor.setVisible(True)

        def restore(_result=None):
            dlg_layout.removeWidget(self.tab_vector_editor)
            self.tab_vector_editor.setParent(None)
            self.main_tabs_view.insertTab(
    idx,
    self.tab_vector_editor,
    tr("tab.vector_editor")
)
            self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
            self.tab_vector_editor.setVisible(True)
            self.vector_canvas.request_recenter()

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)
        # Recentre la vue sur le contenu une fois la fenêtre maximisée.
        self.vector_canvas.request_recenter()

    def set_vector_snap_enabled(self, enabled):
        self.vector_canvas.snap_enabled = bool(enabled)

    def set_vector_snap_step(self, value):
        self.vector_canvas.snap_step_mm = float(value)

    def _image_frame(self):
        """(x, y, largeur, hauteur) en mm de l'image de « Graver une image »,
        pour caler le puzzle dessus (VectorEditorController)."""
        if not (hasattr(self, "spin_w") and hasattr(self, "spin_h")):
            return None
        ox = float(self.spin_off_x.value()) if hasattr(self, "spin_off_x") else 0.0
        oy = float(self.spin_off_y.value()) if hasattr(self, "spin_off_y") else 0.0
        return ox, oy, float(self.spin_w.value()), float(self.spin_h.value())

    @contextmanager
    def _busy_cursor(self):
        """Curseur d'attente pendant un calcul long (imbrication, série)."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()
