"""Barre d'outils principale, sous le menu.

La liste des boutons est personnalisable (issue #190) : configuration
chargée depuis les préférences, reconstruite à la volée. Restent toujours
présents :
- le bouton principal « Générer le G-Code » ;
- le bouton rouge « Arrêt d'urgence » (visible seulement pendant une gravure) ;
- le bouton de soutien ko-fi, aligné à droite avec le plein écran.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.app.menu.toolbar_config import (
    SEPARATOR,
    action_for_id,
    load_toolbar_actions,
    save_toolbar_actions,
)
from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeButton


class AppToolBar(QToolBar):
    """Barre d'outils : raccourcis du menu, image et G-code.

    Elle reprend les actions de AppActions (mêmes icône, libellé, raccourci
    et état que dans le menu) et y ajoute des widgets : le bouton
    « Générer le G-code » et, tout à droite, le bouton de soutien ko-fi.
    La connexion au graveur est dans le panneau machine (ConnectionPanel).
    """

    # Demande d'ouverture de la page de personnalisation (Paramètres).
    customize_requested = pyqtSignal()

    def __init__(self, actions, parent=None):
        super().__init__(tr("toolbar.main"), parent)
        self.setObjectName("main_toolbar")
        self.setMovable(False)
        # Icônes seules, libellé en infobulle (une entrée sans icône hors
        # Linux affiche son libellé).
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._actions = actions
        # Identifiant de chaque action ajoutée à la barre (pour le menu contextuel).
        self._action_ids = {}  # QAction -> id
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self._machine_running = False
        # Créés dans rebuild() : clear() du QToolBar détruit les widgets
        # ajoutés via addWidget, il faut les recréer à chaque reconstruction.
        self.stop_button = None
        self.stop_button_action = None

        self.rebuild()

        actions.machine_running_changed.connect(self._set_stop_visible)

    # -- construction / reconstruction

    def rebuild(self, action_ids=None):
        """Vide la barre et la reconstruit depuis `action_ids` (ou les préférences)."""
        if action_ids is None:
            action_ids = load_toolbar_actions()
        self.clear()
        self._action_ids.clear()

        for action_id in action_ids:
            if action_id == SEPARATOR:
                self.addSeparator()
                continue
            action = action_for_id(self._actions, action_id)
            if action is None:
                continue
            self.addAction(action)
            self._action_ids[action] = action_id

        # Bouton principal « Générer le G-Code » (toujours présent).
        self.addWidget(self._generate_button(self._actions))

        # Arrêt d'urgence : toujours à l'écran pendant une gravure, un homing
        # ou des commandes, même panneau du graveur replié.
        self.stop_button = self._stop_button(self._actions)
        self.stop_button_action = self.addWidget(self.stop_button)
        self.stop_button_action.setVisible(self._machine_running)

        self.addSeparator()

        # Plein écran + soutien du projet, alignés à droite.
        # Si fullscreen est déjà dans la liste personnalisée, on ne le double pas.
        has_fullscreen = "fullscreen" in action_ids
        self.addWidget(self._spacer())
        if not has_fullscreen:
            self.addAction(self._actions.fullscreen)
            self._action_ids[self._actions.fullscreen] = "fullscreen"
        self.addWidget(BuyMeACoffeeButton(self.iconSize().height()))

    def apply_and_save(self, action_ids):
        """Enregistre la configuration et reconstruit la barre immédiatement."""
        cleaned = save_toolbar_actions(action_ids)
        self.rebuild(cleaned)
        return cleaned

    def current_action_ids(self):
        """Identifiants actuellement affichés (hors widgets fixes)."""
        return load_toolbar_actions()

    # -- widgets fixes

    @staticmethod
    def _spacer():
        """Espace extensible : pousse les widgets suivants à droite."""
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        return spacer

    @staticmethod
    def _stop_button(actions):
        """Gros bouton rouge « Arrêt d'urgence » (F9) : reset immédiat du graveur."""
        button = QPushButton(tr("menu.job.emergency_stop_button"))
        button.setToolTip(tr("menu.job.emergency_stop_tip"))
        button.setProperty("role", "danger")     # rouge dans tous les thèmes (theme.py)
        button.clicked.connect(actions.emergency_stop.trigger)
        return button

    @staticmethod
    def _generate_button(actions):
        """Bouton principal « Générer le G-code », avec son libellé."""
        button = QPushButton(tr("gcode.generate"))
        button.setProperty("role", "primary")    # couleurs du thème (theme.py)
        button.clicked.connect(actions.generate_requested)
        return button

    def _set_stop_visible(self, visible):
        self._machine_running = bool(visible)
        if hasattr(self, "stop_button_action") and self.stop_button_action is not None:
            self.stop_button_action.setVisible(self._machine_running)

    # -- menu contextuel

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        customize = menu.addAction(tr("toolbar.customize"))
        customize.triggered.connect(self.customize_requested.emit)

        # Clic sur un bouton d'action → proposer de le retirer.
        child = self.childAt(pos)
        action = None
        if child is not None:
            # QToolButton sous-jacent porte l'action via defaultAction().
            default = getattr(child, "defaultAction", lambda: None)()
            if isinstance(default, QAction) and default in self._action_ids:
                action = default
        if action is not None:
            action_id = self._action_ids[action]
            remove = menu.addAction(tr("toolbar.remove_action"))
            remove.triggered.connect(lambda: self._remove_action(action_id))

        menu.exec(self.mapToGlobal(pos))

    def _remove_action(self, action_id):
        ids = [i for i in load_toolbar_actions() if i != action_id]
        # Évite une barre vide de boutons personnalisables.
        if not any(i != SEPARATOR for i in ids):
            return
        self.apply_and_save(ids)
