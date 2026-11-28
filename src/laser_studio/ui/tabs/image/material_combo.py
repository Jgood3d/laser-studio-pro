"""Liste « Matière » de l'onglet « Graver une image »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox

from laser_studio.i18n import tr
from laser_studio.models.image_materials import BUILTIN, USER_PREFIX


class MaterialComboBox(QComboBox):
    """Matière : les matières fournies, puis celles de l'utilisateur (clé \"user:<nom>\"). Tant qu'aucune
    n'est choisie, la liste affiche un texte d'invite (aucune entrée « sans matière »).

    Elle ne fait que choisir ; liée au modèle ImageSettings (material), qui pose les réglages de la matière
    quand l'utilisateur la choisit (ImageSettings.choose_material ; les champs restent modifiables).

        combo = MaterialComboBox()
        combo.activated.connect(lambda _i: settings.choose_material(combo.material(), library.get(combo.material())))
        combo.set_materials([\"Mon bois\"])
    """

    # Matière choisie : sa clé.
    material_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Les libellés sont longs (exemples de matières : 62 caractères en
        # français, 85 en allemand). Par défaut, une liste déroulante prend
        # la largeur de son élément le PLUS LONG comme largeur minimale. On
        # fixe donc une largeur minimale courte ; la liste ouverte, elle,
        # reste assez large pour tout lire.
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(12)
        self.setPlaceholderText(tr("img.material_placeholder"))
        self.set_materials(())
        self.setToolTip(tr("img.material_bg_tooltip"))
        self.currentIndexChanged.connect(
            lambda _index: self.material_changed.emit(self.material())
        )

    def set_materials(self, user_names):
        """Remet la liste : matières fournies, puis les matières `user_names` de l'utilisateur. Sans signal ;
        la matière affichée est gardée si elle existe encore, sinon le texte d'invite revient."""
        current = self.currentData()
        blocked = self.blockSignals(True)
        self.clear()
        for key in BUILTIN:
            self.addItem(tr(f"img.mat.{key}"), key)
        if user_names:
            self.insertSeparator(self.count())
            for name in user_names:
                self.addItem(name, USER_PREFIX + name)
        for i in range(self.count()):
            if self.itemData(i) is not None:
                self.setItemData(i, self.itemText(i), Qt.ItemDataRole.ToolTipRole)
        index = self.findData(current) if current is not None else -1
        self.setCurrentIndex(index)                  # -1 : texte d'invite
        self.view().setMinimumWidth(self.view().sizeHintForColumn(0) + 24)
        self.blockSignals(blocked)

    def material(self):
        """Clé de la matière choisie (\"\" si aucune)."""
        return self.currentData() or ""
