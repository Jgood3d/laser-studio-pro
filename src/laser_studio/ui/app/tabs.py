"""Onglets du centre de la fenêtre et panneau du bas.

    tabs = MainTabs(window.main_tabs_view, window, splitter=window.center_v_splitter,
                    bottom_panel=window.bottom_panel, ...)
    tabs.show(window.tab_separation)
    tabs.toggle_current_fullscreen()

Rôle de MainTabs : afficher un onglet (même masqué ou en plein écran), ouvrir l'onglet
affiché en plein écran, et mémoriser la position des séparateurs (onglets / panneau du
bas, aperçu 2D / statistiques). Le panneau du bas lui-même est ui/app/bottom_panel.py.
"""
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout

from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import tr
from laser_studio.ui.widgets import FullscreenWindow

class MainTabs(QObject):
    """Onglets du centre (`view`, QTabWidget) de la fenêtre `window`.

    - `splitter` : séparateur onglets / panneau du bas ; `bottom_panel` : le
      panneau (BottomPanel), dont les tailles dépliées sont mémorisées ;
    - `preview_splitter` : séparateur aperçu 2D / statistiques, dont la
      position est mémorisée avec celle de `splitter` ;
    - `vector_editor` et `png2svg` : onglets au plein écran particulier
      (fenêtre à part, titre propre) ; `recenter_vector_editor()` recentre le
      canevas une fois l'éditeur déplacé.
    """

    def __init__(self, view, window, *, splitter, bottom_panel, preview_splitter,
                 vector_editor, recenter_vector_editor, png2svg, parent=None):
        super().__init__(parent)
        self.view = view
        self.window = window
        self.splitter = splitter
        self.bottom_panel = bottom_panel
        self.preview_splitter = preview_splitter
        self.vector_editor = vector_editor
        self._recenter_vector_editor = recenter_vector_editor
        self.png2svg = png2svg
        self._closable = ()

    # -- onglets fermables (ouverts depuis le menu Outils)

    def set_closable(self, tabs):
        """Croix de fermeture (comme dans VS Code) sur les seuls onglets `tabs` ; fermer un onglet le masque, le
        menu Outils le rouvre (show)."""
        self._closable = tuple(tabs)
        self.view.setTabsClosable(True)
        self.view.tabCloseRequested.connect(self._close_tab)
        self.refresh_close_buttons()

    def refresh_close_buttons(self):
        """Retire la croix des onglets qui ne se ferment pas (Qt en pose une sur chaque onglet ajouté)."""
        bar = self.view.tabBar()
        for index in range(self.view.count()):
            if self.view.widget(index) not in self._closable:
                bar.setTabButton(index, bar.ButtonPosition.RightSide, None)

    def _close_tab(self, index):
        if self.view.widget(index) in self._closable:
            self.view.setTabVisible(index, False)

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
            self.open_fullscreen(tab, title, tr("vector.close_fullscreen"), title)

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
            self.refresh_close_buttons()
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
        btn_close_fullscreen.setProperty("role", "primary")       # couleurs du thème (theme.py)
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
            self.refresh_close_buttons()
            self._recenter_vector_editor()

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)
        # Recentre la vue sur le contenu une fois la fenêtre maximisée.
        self._recenter_vector_editor()

    # -- panneau du bas et séparateurs

    def save_splitter_sizes(self, *_args):
        prefs = ui_preferences()
        if self.bottom_panel.is_collapsed():
            sizes = self.bottom_panel.expanded_sizes
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
                    self.bottom_panel.expanded_sizes = loaded_sizes
                    if not self.bottom_panel.is_collapsed():
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
