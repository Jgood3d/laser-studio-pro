"""Connexion au graveur : liste des ports, actualisation, connexion."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QStyle,
    QVBoxLayout,
)

from laser_studio.i18n import tr

CONNECTED_COLOR = "#27ae60"
DISCONNECTED_COLOR = "#e74c3c"


def status_dot_icon(color):
    """Pastille ronde de la couleur donnée (état de la connexion)."""
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color).darker(140), 1))
    painter.setBrush(QColor(color))
    painter.drawEllipse(2, 2, 12, 12)
    painter.end()
    return QIcon(pixmap)


class ConnectionPanel(QGroupBox):
    """Choix du port du graveur, actualisation de la liste, connexion.

    Il ne se connecte pas : ses boutons émettent des signaux, auxquels la
    fenêtre (plus tard un contrôleur) s'abonne. L'état de la connexion lui
    est transmis par set_connected() :

        panel = ConnectionPanel(ports_model)
        panel.refresh_requested.connect(laser.refresh_com_ports)
        panel.connect_requested.connect(laser.toggle_connection)
        panel.set_connected(False)

    `ports_model` : modèle de la liste des ports (ports_combo), partagé
    avec la page « Matériaux et connexion au graveur » : la fenêtre
    remplit l'une, les deux affichent les mêmes ports.
    """

    refresh_requested = pyqtSignal()
    connect_requested = pyqtSignal()

    def __init__(self, ports_model, parent=None):
        super().__init__(tr("ui.connection_box"), parent)
        self.ports_combo = self._ports_combo(ports_model)
        self.refresh_button = self._refresh_button()
        self.connect_button = QPushButton()
        self.connect_button.clicked.connect(self.connect_requested)

        ports_row = QHBoxLayout()
        ports_row.addWidget(self.ports_combo, 1)
        ports_row.addWidget(self.refresh_button)
        layout = QVBoxLayout(self)
        layout.addLayout(ports_row)
        layout.addWidget(self.connect_button)
        layout.addStretch()
        self.set_connected(False)

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """« Déconnecter » / pastille verte si connecté, « Connecter GRBL »
        / pastille rouge sinon."""
        self.connect_button.setText(
            tr("laser.disconnect") if connected else tr("laser.connect")
        )
        self.connect_button.setIcon(
            status_dot_icon(
                CONNECTED_COLOR if connected else DISCONNECTED_COLOR
            )
        )

    # -- construction

    @staticmethod
    def _ports_combo(ports_model):
        """Liste des ports ; l'infobulle donne le port choisi."""
        combo = QComboBox()
        combo.setModel(ports_model)
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(16)
        combo.setToolTip(tr("usb.port"))
        combo.currentTextChanged.connect(
            lambda text: combo.setToolTip(text or tr("usb.port"))
        )
        return combo

    def _refresh_button(self):
        """Bouton icône seule, libellé en infobulle."""
        icon = QIcon.fromTheme(QIcon.ThemeIcon.ViewRefresh)
        if icon.isNull():
            icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_BrowserReload
            )
        button = QPushButton(icon, "")
        button.setToolTip(tr("usb.refresh_ports"))
        button.clicked.connect(self.refresh_requested)
        return button
