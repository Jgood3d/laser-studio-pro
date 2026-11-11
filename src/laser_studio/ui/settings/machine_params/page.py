"""Page « Paramètres du graveur », ouverte depuis le menu Paramètres."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from laser_studio.i18n import tr


class MachineParamsPage(QScrollArea):
    """Profils machine, dimensions du lit, spot du laser et limites.

    Page défilante (QScrollArea) : la fenêtre de réglages l'affiche telle
    quelle, sans ajouter d'ascenseur. Elle ne gère pas les profils : ses
    boutons et ses champs émettent des signaux, auxquels la fenêtre (plus
    tard un contrôleur) s'abonne :

        page = MachineParamsPage()
        page.new_profile_requested.connect(self._new_machine_profile)
        page.focal_changed.connect(self._on_machine_focal_changed)

    Les champs restent lisibles directement (profile_combo, bed_width_spin,
    bed_height_spin, focal_spin, max_speed_spin, accel_spin).
    """

    profile_selected = pyqtSignal(int)
    new_profile_requested = pyqtSignal()
    update_profile_requested = pyqtSignal()
    delete_profile_requested = pyqtSignal()
    # Largeur et profondeur du lit, en mm.
    bed_size_changed = pyqtSignal(float, float)
    # Taille du spot du laser, en mm.
    focal_changed = pyqtSignal(float)
    # Vitesse maximale du graveur, en mm/min.
    max_speed_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self._profiles_box())
        layout.addWidget(self._bed_box())
        layout.addWidget(self._laser_box())
        layout.addWidget(self._limits_box())
        layout.addStretch()
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

    # -- profil machine

    def profile_values(self):
        """Champs de la page enregistrés dans un profil machine : lit
        (w, h, en mm), spot du laser (focal, mm), vitesse maximale
        (mm/min) et accélération."""
        return {
            "w": self.bed_width_spin.value(),
            "h": self.bed_height_spin.value(),
            "focal": self.focal_spin.value(),
            "max_speed": self.max_speed_spin.value(),
            "accel": self.accel_spin.value(),
        }

    def apply_profile_values(self, profile):
        """Réapplique les champs d'un profil. Lit et spot absents : valeurs
        actuelles gardées ; vitesse et accélération absentes : valeurs par
        défaut."""
        self.bed_width_spin.setValue(
            profile.get("w", self.bed_width_spin.value())
        )
        self.bed_height_spin.setValue(
            profile.get("h", self.bed_height_spin.value())
        )
        self.focal_spin.setValue(profile.get("focal", self.focal_spin.value()))
        self.max_speed_spin.setValue(profile.get("max_speed", 6000.0))
        self.accel_spin.setValue(profile.get("accel", 500.0))

    # -- construction

    def _profiles_box(self):
        """Choix du profil machine, et boutons nouveau / mettre à jour /
        supprimer."""
        box = QGroupBox(tr("mach.profiles_box"))
        layout = QVBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.profile_selected)
        layout.addWidget(self.profile_combo)
        buttons = QHBoxLayout()
        for key, signal in (
            ("mach.new_machine", self.new_profile_requested),
            ("mach.update", self.update_profile_requested),
            ("mach.delete", self.delete_profile_requested),
        ):
            button = QPushButton(tr(key))
            button.clicked.connect(signal)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(self._info_label("mach.profile_info"))
        box.setLayout(layout)
        return box

    def _bed_box(self):
        """Dimensions du lit (zone de travail physique)."""
        box = QGroupBox(tr("mach.bed_box"))
        layout = QFormLayout()
        self.bed_width_spin = self._mm_spin(300.0)
        self.bed_height_spin = self._mm_spin(200.0)
        for spin in (self.bed_width_spin, self.bed_height_spin):
            spin.valueChanged.connect(self._emit_bed_size)
        layout.addRow(tr("mach.bed_w"), self.bed_width_spin)
        layout.addRow(tr("mach.bed_h"), self.bed_height_spin)
        layout.addRow(self._info_label("mach.bed_info"))
        box.setLayout(layout)
        return box

    def _laser_box(self):
        """Taille du spot (focale) du laser."""
        box = QGroupBox(tr("mach.laser_box"))
        layout = QFormLayout()
        self.focal_spin = QDoubleSpinBox()
        self.focal_spin.setRange(0.01, 2.0)
        self.focal_spin.setSingleStep(0.01)
        self.focal_spin.setDecimals(3)
        self.focal_spin.setValue(0.10)
        self.focal_spin.setSuffix(" mm")
        self.focal_spin.valueChanged.connect(self.focal_changed)
        layout.addRow(tr("mach.focal_size"), self.focal_spin)
        layout.addRow(self._info_label("mach.focal_help"))
        box.setLayout(layout)
        return box

    def _limits_box(self):
        """Vitesse et accélération maximales (pour information)."""
        box = QGroupBox(tr("mach.limits_box"))
        layout = QFormLayout()
        self.max_speed_spin = QDoubleSpinBox()
        self.max_speed_spin.setRange(1.0, 50000.0)
        self.max_speed_spin.setValue(6000.0)
        self.max_speed_spin.setSuffix(" mm/min")
        self.max_speed_spin.valueChanged.connect(self.max_speed_changed)
        self.accel_spin = QDoubleSpinBox()
        self.accel_spin.setRange(1.0, 20000.0)
        self.accel_spin.setValue(500.0)
        self.accel_spin.setSuffix(" mm/s²")
        layout.addRow(tr("mach.max_speed"), self.max_speed_spin)
        layout.addRow(tr("mach.accel"), self.accel_spin)
        layout.addRow(self._info_label("mach.limits_info"))
        box.setLayout(layout)
        return box

    @staticmethod
    def _mm_spin(value):
        spin = QDoubleSpinBox()
        spin.setRange(1.0, 5000.0)
        spin.setValue(value)
        spin.setSuffix(" mm")
        return spin

    @staticmethod
    def _info_label(key):
        label = QLabel(tr(key))
        label.setWordWrap(True)
        return label

    def _emit_bed_size(self):
        self.bed_size_changed.emit(
            self.bed_width_spin.value(), self.bed_height_spin.value()
        )
