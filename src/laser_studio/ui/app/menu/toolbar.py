"""Barre d'outils principale, sous le menu."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.buy_me_a_coffee import BuyMeACoffeeButton


class AppToolBar(QToolBar):
    """Barre d'outils : raccourcis du menu, image et G-code.

    Elle reprend les actions de AppActions (mêmes icône, libellé, raccourci
    et état que dans le menu) et y ajoute des widgets : le bouton
    « Générer le G-code » et, tout à droite, le bouton de soutien ko-fi.
    La connexion au graveur est dans le panneau machine (ConnectionPanel).
    """

    def __init__(self, actions, parent=None):
        super().__init__(tr("toolbar.main"), parent)
        self.setObjectName("main_toolbar")
        self.setMovable(False)
        # Icônes seules, libellé en infobulle (une entrée sans icône hors
        # Linux affiche son libellé).
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addAction(actions.quit)
        self.addSeparator()
        self.addAction(actions.save_project)
        self.addAction(actions.open_project)
        self.addSeparator()
        self.addAction(actions.machine_params_window)
        self.addSeparator()
        # Outils généraux du menu Outils ; ceux de l'éditeur vectoriel (bibliothèque, import, générateurs)
        # sont dans l'éditeur lui-même (rangée du haut, barre d'édition, canevas vide).
        for action in actions.tool_actions:
            self.addAction(action)
        self.addSeparator()
        # Actions sur l'image (annuler, pivoter, miroirs, réinitialiser,
        # supprimer) : barre flottante des aperçus d'image (FloatingToolBar,
        # ui/app/main_window._add_image_floating_toolbars).
        self.addAction(actions.estimate)
        self.addWidget(self._generate_button(actions))
        # Arrêt d'urgence : toujours à l'écran pendant une gravure, un homing ou des commandes, même panneau du
        # graveur replié.
        self.stop_button = self._stop_button(actions)
        self.stop_button_action = self.addWidget(self.stop_button)
        self.stop_button_action.setVisible(False)
        actions.machine_running_changed.connect(self.stop_button_action.setVisible)
        self.addSeparator()
        # File d'attente : son onglet du panneau du bas.
        self.addAction(actions.job_queue)
        # Plein écran de l'onglet affiché et soutien du projet, alignés à
        # droite.
        self.addWidget(self._spacer())
        self.addAction(actions.fullscreen)
        self.addWidget(BuyMeACoffeeButton(self.iconSize().height()))

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
