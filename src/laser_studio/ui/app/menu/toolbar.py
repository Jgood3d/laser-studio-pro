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
        self.addAction(actions.machine_window)
        self.addAction(actions.grbl_window)
        self.addSeparator()
        for action in actions.tool_actions:
            self.addAction(action)
        self.addSeparator()
        # Actions sur l'image (annuler, pivoter, miroirs, réinitialiser,
        # supprimer) : barre flottante des aperçus d'image (FloatingToolBar,
        # main_window._add_image_floating_toolbars).
        self.addAction(actions.estimate)
        self.addWidget(self._generate_button(actions))
        self.addSeparator()
        # Case à cocher : bouton enfoncé tant que la file d'attente est affichée.
        self.addAction(actions.job_queue)
        # Soutien du projet, aligné à droite.
        self.addWidget(self._spacer())
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
    def _generate_button(actions):
        """Bouton bleu « Générer le G-code », avec son libellé."""
        button = QPushButton(tr("gcode.generate"))
        button.setStyleSheet(
            "background-color: #2b5c8f; color: white; "
            "font-weight: bold; padding: 3px;"
        )
        button.clicked.connect(actions.generate_requested)
        return button
