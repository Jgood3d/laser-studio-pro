"""Contrôleur de la fenêtre : reçoit les demandes de l'interface et agit.

Il abonne la fenêtre aux signaux du menu et de la barre d'outils
(ui/app/menu/), et regroupe ce qui agit sur toute la fenêtre : thème,
langue, onglets annexes, état de la connexion, actions de la barre
d'outils sur l'image de l'onglet courant. Il deviendra un vrai
contrôleur, séparé de la fenêtre.
"""

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSettings, Qt
from i18n import set_language, tr
from stencil_studio.studio_dialog import open_stencil_studio
from ui.about import AboutDialog
from ui.app.menu import AppActions, AppMenuBar, AppToolBar
from ui.buy_me_a_coffee import BuyMeACoffeeDialog
from ui.support import SupportDialog


class WindowControllerMixin:
    def change_theme(self, theme_name):
        """Bascule de thème à la volée et mémorise le code.

        Codes possibles : dark, light, dusk, warm.
        """
        from ui.app.theme import apply_app_theme, normalize_theme_name

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
        self._refresh_recent_projects_menu()
        self.update_connection_widgets()

    def _connect_app_actions(self, actions):
        """Abonne la fenêtre aux signaux du menu et de la barre d'outils."""
        # Fichier
        actions.save_project_requested.connect(self.save_project)
        actions.open_project_requested.connect(self.load_project)
        actions.recent_project_requested.connect(self._load_project_from_path)
        actions.quit_requested.connect(self.close)
        # Paramètres et outils
        actions.settings_window_requested.connect(self.show_settings_window)
        actions.language_selected.connect(self._on_language_selected)
        actions.theme_selected.connect(self.change_theme)
        actions.stencil_studio_requested.connect(
            lambda: open_stencil_studio(self)
        )
        actions.main_tab_requested.connect(self.show_main_tab)
        # Aide
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
        actions.estimate_requested.connect(self.estimate_job_time)
        actions.generate_requested.connect(self.generate_job)
        actions.gcode_import_requested.connect(self.import_gcode_file)
        # Connexion au graveur
        actions.refresh_ports_requested.connect(self.refresh_com_ports)
        actions.connection_toggle_requested.connect(self.toggle_connection)

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

    def update_connection_widgets(self):
        """Met le bouton de connexion en accord avec l'état du port.

        Page et barre d'outils : « Déconnecter » sur fond vert / pastille
        verte si connecté, « Connecter GRBL » / pastille rouge sinon.
        Verrouille ou déverrouille aussi les commandes de la machine.
        """
        connected = self.usb.is_connected()
        page = getattr(self, "tab_machine_profiles", None)
        if page is not None:
            page.set_connected(connected)
        actions = getattr(self, "app_actions", None)
        if actions is not None:
            actions.set_connected(connected)
        # Pilotage, actions de job et console directe : verrouillés tant que
        # le graveur n'est pas connecté. La position du job reste modifiable
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
