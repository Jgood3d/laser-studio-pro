"""Liste « Matière » de l'onglet « Graver une image »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox

from laser_studio.i18n import tr


class MaterialComboBox(QComboBox):
    """Matière : fond noir ("dark") ou fond clair ("light").

    Elle ne fait que choisir ; la fenêtre coche ou décoche « Inverser
    Couleurs » en conséquence (la case reste modifiable).

        combo = MaterialComboBox()
        combo.material_changed.connect(self._on_material_bg_changed)
    """

    # Matière choisie : "dark" ou "light".
    material_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addItem(tr("img.bg_dark"), "dark")
        self.addItem(tr("img.bg_light"), "light")
        # Fond clair = négatif désactivé (comportement historique).
        self.setCurrentIndex(1)
        self.setToolTip(tr("img.material_bg_tooltip"))
        # Les libellés sont longs (exemples de matières : 62 caractères en
        # français, 85 en allemand). Par défaut, une liste déroulante prend
        # la largeur de son élément le PLUS LONG comme largeur minimale. On
        # fixe donc une largeur minimale courte ; la liste ouverte, elle,
        # reste assez large pour tout lire.
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(12)
        for i in range(self.count()):
            self.setItemData(i, self.itemText(i), Qt.ItemDataRole.ToolTipRole)
        popup = self.view()
        popup.setMinimumWidth(popup.sizeHintForColumn(0) + 24)
        self.currentIndexChanged.connect(
            lambda _index: self.material_changed.emit(self.material())
        )

    def material(self):
        """Matière choisie : "dark" ou "light"."""
        return self.currentData()
