"""Onglets du centre de la fenêtre et panneau du bas.

    tabs = MainTabs(window.main_tabs_view, window, splitter=window.center_v_splitter,
                    bottom_panel=window.center_bottom_widget, ...)
    tabs.show(window.tab_separation)
    tabs.toggle_current_fullscreen()

Rôle de MainTabs : afficher un onglet (même masqué ou en plein écran), gérer les
onglets facultatifs du menu Affichage (croix, choix mémorisé), ouvrir l'onglet
affiché en plein écran, et montrer le panneau machine sous les onglets
seulement là où il sert, avec la position mémorisée des séparateurs.
"""
from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtWidgets import QDialog, QPushButton, QTabBar, QVBoxLayout

from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import tr
from laser_studio.ui.widgets import FullscreenWindow, TabCloseButton

# Onglets facultatifs (menu Affichage) : clé de UIConfig qui mémorise s'ils
# sont affichés, et état au premier démarrage.
GCODE_CONSOLE_SETTING = "show_gcode_console"
JOB_QUEUE_SETTING = "show_job_queue"
OPTIONAL_TAB_DEFAULTS = {GCODE_CONSOLE_SETTING: False, JOB_QUEUE_SETTING: True}


def optional_tab_was_visible(setting):
    """Onglet facultatif affiché à la dernière utilisation ? (au premier
    démarrage : l'état par défaut de OPTIONAL_TAB_DEFAULTS)"""
    return ui_preferences().get_bool(setting, OPTIONAL_TAB_DEFAULTS[setting])


class MainTabs(QObject):
    """Onglets du centre (`view`, QTabWidget) de la fenêtre `window`.

    - `splitter` : séparateur onglets / panneau du bas ; `bottom_panel` : le
      panneau (machine), montré seulement sur les onglets `panel_tabs` ou
      pendant un job (`job_in_progress()`) ;
    - `preview_splitter` : séparateur aperçu 2D / statistiques, dont la
      position est mémorisée avec celle de `splitter` ;
    - `vector_editor` et `png2svg` : onglets au plein écran particulier
      (fenêtre à part, titre propre) ; `recenter_vector_editor()` recentre le
      canevas une fois l'éditeur déplacé.
    """

    def __init__(self, view, window, *, splitter, bottom_panel, panel_tabs, preview_splitter,
                 job_in_progress, vector_editor, recenter_vector_editor, png2svg, parent=None):
        super().__init__(parent)
        self.view = view
        self.window = window
        self.splitter = splitter
        self.bottom_panel = bottom_panel
        self.panel_tabs = tuple(panel_tabs)
        self.preview_splitter = preview_splitter
        self._job_in_progress = job_in_progress
        self.vector_editor = vector_editor
        self._recenter_vector_editor = recenter_vector_editor
        self.png2svg = png2svg
        # Onglet facultatif -> (clé de UIConfig, case du menu Affichage)
        self._optional = {}
        # Tailles du séparateur avant que le panneau du bas soit masqué, rendues à son retour.
        self.bottom_panel_sizes = None

    # -- afficher un onglet

    def show(self, tab):
        """Affiche l'onglet `tab`, rendu visible s'il était masqué. S'il est
        ouvert en plein écran (sorti des onglets), sa fenêtre est ramenée au
        premier plan."""
        index = self.view.indexOf(tab)
        if index != -1:
            self.view.setTabVisible(index, True)
            self.view.setCurrentWidget(tab)
        else:
            tab.window().raise_()
            tab.window().activateWindow()

    # -- onglets facultatifs (menu Affichage)

    def add_optional(self, tab, setting, action):
        """Onglet facultatif `tab` : affiché ou masqué par la case `action` du
        menu Affichage, choix mémorisé sous la clé `setting` de UIConfig. Une
        croix sur l'onglet le ferme en décochant la case."""
        self._optional[tab] = (setting, action)
        self._add_close_button(tab, action)

    def restore_optional_tabs(self):
        """Onglets facultatifs et cases du menu comme à la dernière utilisation."""
        for tab, (setting, action) in self._optional.items():
            visible = optional_tab_was_visible(setting)
            action.setChecked(visible)
            self.set_optional_visible(tab, visible)

    def set_optional_visible(self, tab, visible):
        """Affiche ou masque l'onglet facultatif `tab`, et mémorise ce choix
        pour le prochain démarrage. Ouvert en plein écran (sorti des onglets),
        il n'est pas touché. Le réglage n'est écrit que s'il change."""
        setting = self._optional[tab][0]
        index = self.view.indexOf(tab)
        if index != -1:
            self.view.setTabVisible(index, visible)
        if optional_tab_was_visible(setting) != bool(visible):
            ui_preferences().set(setting, bool(visible))

    def _add_close_button(self, tab, action):
        """Croix sur l'onglet `tab` : le ferme en décochant `action`, qui masque
        l'onglet et mémorise le choix."""
        index = self.view.indexOf(tab)
        if index == -1:
            return
        button = TabCloseButton()
        button.clicked.connect(lambda: action.setChecked(False))
        self.view.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, button)

    def _restore_close_button(self, tab):
        """Remet la croix d'un onglet facultatif au retour du plein écran : Qt
        la supprime quand l'onglet sort de la barre."""
        if tab in self._optional:
            self._add_close_button(tab, self._optional[tab][1])

    # -- plein écran

    def toggle_current_fullscreen(self):
        """Plein écran de l'onglet affiché (bouton « Plein écran » de la barre
        d'outils, F11).

        L'éditeur vectoriel garde sa propre fenêtre (open_vector_editor_fullscreen),
        la vectorisation son titre ; les autres onglets passent par la fenêtre
        commune, avec le titre de l'onglet."""
        tab = self.view.currentWidget()
        if tab is None:
            return
        if tab is self.vector_editor:
            self.open_vector_editor_fullscreen()
        elif tab is self.png2svg:
            self.open_fullscreen(tab, tr("png2svg.fullscreen_title"), tr("png2svg.close_fullscreen"),
                                 tr("png2svg.tab_title"))
        else:
            title = self.view.tabText(self.view.indexOf(tab))
            self.open_fullscreen(tab, title, tr("vector.close_fullscreen"), title,
                                 on_restored=lambda: self._restore_close_button(tab))

    def open_fullscreen(self, tab, window_title, close_text, tab_title, on_restored=None):
        """Sort `tab` des onglets dans une FullscreenWindow, et l'y remet à la
        même place quand elle se ferme (puis appelle `on_restored`). Sans
        effet si l'onglet est déjà en plein écran."""
        index = self.view.indexOf(tab)
        if index == -1:
            return
        fullscreen = FullscreenWindow(self.window, tab, window_title, close_text)

        def restore():
            self.view.insertTab(index, tab, tab_title)
            self.view.setCurrentWidget(tab)
            tab.setVisible(True)
            tab.updateGeometry()
            self.view.update()
            self.window.update()
            self.window.repaint()
            if on_restored is not None:
                on_restored()

        fullscreen.content_released.connect(restore)
        fullscreen.show_maximized()

    def open_vector_editor_fullscreen(self):
        """Ouvre l'éditeur vectoriel (texte/formes/SVG) dans une fenêtre à
        part, maximisée, pour travailler plus confortablement. Fermer cette
        fenêtre (bouton dédié, Échap, ou la croix) remet l'éditeur à sa place
        normale dans l'onglet."""
        tab = self.vector_editor
        idx = self.view.indexOf(tab)
        if idx == -1:
            return  # déjà sorti (fenêtre plein écran probablement déjà ouverte)

        dialog = QDialog(self.window)
        # Fenêtre indépendante à part entière (pas une simple boîte de
        # dialogue) : ça lui donne les boutons minimiser/agrandir/fermer
        # standards de Windows et un vrai comportement plein écran.
        dialog.setWindowFlags(Qt.WindowType.Window)
        dialog.setWindowTitle(tr("vector.fullscreen_title"))

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(4, 4, 4, 4)

        btn_close_fullscreen = QPushButton(tr("vector.close_fullscreen"))
        btn_close_fullscreen.setStyleSheet("background-color: #8f2b2b; color: white; padding: 6px; font-weight: bold;")
        btn_close_fullscreen.clicked.connect(dialog.close)
        dlg_layout.addWidget(btn_close_fullscreen)

        dlg_layout.addWidget(tab)
        tab.setVisible(True)

        def restore(_result=None):
            dlg_layout.removeWidget(tab)
            tab.setParent(None)
            self.view.insertTab(idx, tab, tr("tab.vector_editor"))
            self.view.setCurrentWidget(tab)
            tab.setVisible(True)
            self._recenter_vector_editor()

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)
        # Recentre la vue sur le contenu une fois la fenêtre maximisée.
        self._recenter_vector_editor()

    # -- panneau du bas et séparateurs

    def update_bottom_panel(self, *_args):
        """Panneau machine montré sur les onglets `panel_tabs` et pendant un
        job, masqué ailleurs ; sa hauteur est rendue à son retour."""
        panel = self.bottom_panel
        current = self.view.currentWidget()
        show = self._job_in_progress() or any(current is t for t in self.panel_tabs)
        if show and panel.isHidden():
            panel.setVisible(True)
            sizes = self.bottom_panel_sizes
            if sizes:
                QTimer.singleShot(0, lambda s=sizes: self.splitter.setSizes(s))
        elif not show and not panel.isHidden():
            sizes = self.splitter.sizes()
            if all(v > 0 for v in sizes):
                self.bottom_panel_sizes = sizes
            panel.setVisible(False)

    def save_splitter_sizes(self, *_args):
        prefs = ui_preferences()
        if self.bottom_panel.isHidden():
            sizes = self.bottom_panel_sizes
        else:
            sizes = self.splitter.sizes()
        if sizes and all(v > 0 for v in sizes):
            prefs.set("center_v_splitter_sizes", sizes)
        # Aperçu 2D / colonne de droite (position du job, statistiques) : un côté peut être replié.
        sizes = self.preview_splitter.sizes()
        if sum(sizes) > 0:
            prefs.set("preview_2d_side_sizes", sizes)

    def load_splitter_sizes(self):
        prefs = ui_preferences()
        # Tailles de l'ancienne colonne de gauche, supprimée : plus utilisées.
        prefs.remove("main_splitter_sizes")
        prefs.remove("left_v_splitter_sizes")
        center_v_sizes = prefs.get("center_v_splitter_sizes")
        if center_v_sizes:
            try:
                loaded_sizes = [int(s) for s in center_v_sizes]
                if all(v > 0 for v in loaded_sizes):
                    self.bottom_panel_sizes = loaded_sizes
                    self.splitter.setSizes(loaded_sizes)
            except (TypeError, ValueError):
                pass
        # Moitié / moitié d'une version précédente : remplacé par la colonne étroite par défaut.
        prefs.remove("preview_2d_splitter_sizes")
        preview_sizes = prefs.get("preview_2d_side_sizes")
        if preview_sizes:
            try:
                loaded_sizes = [int(s) for s in preview_sizes]
                if len(loaded_sizes) == 2 and min(loaded_sizes) >= 0 and sum(loaded_sizes) > 0:
                    self.preview_splitter.setSizes(loaded_sizes)
            except (TypeError, ValueError):
                pass
