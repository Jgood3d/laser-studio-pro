"""Page « Matériaux et connexion au graveur »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr

CONNECTED_STYLE = "background-color: #27ae60; color: white;"


class MachineProfilesPage(QWidget):
    """Connexion au graveur (port, connexion) et profils de matériaux.

    Elle ne se connecte pas et ne gère pas les matériaux : ses boutons et
    ses listes émettent des signaux, auxquels la fenêtre (plus tard un
    contrôleur) s'abonne. L'état de la connexion lui est transmis par
    set_connected() :

        page = MachineProfilesPage(ports_model, ["MDF 4mm", "Cuir 2mm"])
        page.connect_requested.connect(laser.toggle_connection)
        page.set_connected(True)

    `ports_model` : modèle de la liste des ports, partagé avec la barre
    d'outils (même liste). Les listes restent lisibles directement
    (ports_combo, material_combo).
    """

    port_selected = pyqtSignal(int)
    refresh_ports_requested = pyqtSignal()
    connect_requested = pyqtSignal()
    material_selected = pyqtSignal(int)
    save_material_requested = pyqtSignal()
    new_material_requested = pyqtSignal()
    delete_material_requested = pyqtSignal()
    export_materials_requested = pyqtSignal()
    import_materials_requested = pyqtSignal()

    def __init__(self, ports_model, material_names, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(self._usb_box(ports_model))
        layout.addWidget(self._materials_box(material_names))
        layout.addStretch()

    # -- état reçu de la fenêtre / du contrôleur

    def set_connected(self, connected):
        """Bouton « Déconnecter » vert si connecté, « Connecter » sinon."""
        self.connect_button.setText(
            tr("laser.disconnect") if connected else tr("laser.connect")
        )
        self.connect_button.setStyleSheet(CONNECTED_STYLE if connected else "")

    def set_port_index(self, index):
        """Sélectionne le port `index` (choisi dans la barre d'outils)."""
        self.ports_combo.setCurrentIndex(index)

    # -- construction

    def _usb_box(self, ports_model):
        """Port du graveur, actualisation de la liste, connexion."""
        box = QGroupBox(tr("usb.box_title"))
        layout = QFormLayout()
        self.ports_combo = QComboBox()
        self.ports_combo.setModel(ports_model)
        self.ports_combo.currentIndexChanged.connect(self.port_selected)
        refresh_button = QPushButton(tr("usb.refresh_ports"))
        refresh_button.clicked.connect(self.refresh_ports_requested)
        self.connect_button = QPushButton(tr("usb.connect"))
        self.connect_button.clicked.connect(self.connect_requested)
        layout.addRow(tr("usb.port"), self.ports_combo)
        layout.addRow("", refresh_button)
        layout.addRow("", self.connect_button)
        layout.addRow(self._driver_hint())
        box.setLayout(layout)
        return box

    def _materials_box(self, material_names):
        """Choix du matériau et gestion des profils de matériaux."""
        box = QGroupBox(tr("material.box_title"))
        layout = QFormLayout()
        self.material_combo = QComboBox()
        self.material_combo.addItems(list(material_names))
        self.material_combo.currentIndexChanged.connect(self.material_selected)
        layout.addRow(tr("material.select"), self.material_combo)
        for key, signal in (
            ("material.save", self.save_material_requested),
            ("material.new", self.new_material_requested),
            ("material.delete", self.delete_material_requested),
            ("material.export", self.export_materials_requested),
            ("material.import", self.import_materials_requested),
        ):
            button = QPushButton(tr(key))
            button.clicked.connect(signal)
            layout.addRow("", button)
        box.setLayout(layout)
        return box

    @staticmethod
    def _driver_hint():
        """Aide sur les pilotes USB, avec lien cliquable."""
        label = QLabel(tr("usb.driver_hint"))
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        label.setStyleSheet("color: #888888;")
        palette = label.palette()
        palette.setColor(QPalette.ColorRole.Link, QColor("#5aa9ff"))
        label.setPalette(palette)
        return label
