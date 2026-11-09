"""Barre d'outils principale, sous le menu."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from i18n import tr
from ui.buy_me_a_coffee import BuyMeACoffeeButton


class AppToolBar(QToolBar):
    """Barre d'outils : raccourcis du menu, image, G-code et connexion.

    Elle reprend les actions de AppActions (mêmes icône, libellé, raccourci
    et état que dans le menu) et y ajoute des widgets : le bouton
    « Générer le G-code », la liste des ports du graveur (ports_combo) et,
    tout à droite, le bouton de soutien ko-fi.
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
        self.addAction(actions.image_undo)
        self.addAction(actions.image_redo)
        self.addSeparator()
        for action in actions.image_actions:
            self.addAction(action)
        self.addAction(actions.mirror_h)
        self.addAction(actions.mirror_v)
        self.addAction(actions.image_reset)
        self.addSeparator()
        self.addAction(actions.estimate)
        self.addWidget(self._generate_button(actions))
        self.addAction(actions.gcode_import)
        self.addSeparator()
        self.ports_combo = self._ports_combo()
        self.addWidget(self.ports_combo)
        self.addAction(actions.refresh_ports)
        self.addAction(actions.connection)
        # Seul bouton avec son libellé : l'état de la connexion doit se lire
        # d'un coup d'œil.
        self.widgetForAction(actions.connection).setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
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

    @staticmethod
    def _ports_combo():
        """Liste des ports du graveur.

        Elle partage son modèle avec celle de la page « Matériaux et
        connexion au graveur ». L'infobulle donne le port choisi.
        """
        combo = QComboBox()
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(16)
        combo.setToolTip(tr("usb.port"))
        combo.currentTextChanged.connect(
            lambda text: combo.setToolTip(text or tr("usb.port"))
        )
        return combo
