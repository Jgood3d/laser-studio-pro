"""Ancien mode SVG, conservé pour compatibilité."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
)
from i18n import tr


class LegacySvgBoxMixin:
    def _build_legacy_svg_box(self):
        """Ancien mode SVG : jamais affiché, ses champs restent lus."""
        legacy_svg_box = QGroupBox(tr("ui.svg_legacy_title"))
        legacy_svg_layout = QFormLayout()
        lbl_legacy_info = QLabel(
            "⚠ Ce mode charge un SVG entier avec UN SEUL réglage de "
            "puissance/vitesse,\n"
            "sans aperçu ni possibilité de mélanger découpe et gravure sur "
            "un même fichier.\n"
            "Préfère plutôt 'Importer SVG (multi-calques)' dans l'Éditeur "
            "Vectoriel, qui\n"
            "décompose le SVG en objets indépendants assignables à des "
            "calques différents,\n"
            "avec aperçu visuel. Conservé ici uniquement pour compatibilité."
        )
        lbl_legacy_info.setWordWrap(True)
        legacy_svg_layout.addRow(lbl_legacy_info)

        btn_svg = QPushButton(tr("ui.load_svg_legacy"))
        btn_svg.clicked.connect(self.load_svg)

        self.chk_enable_cut = QCheckBox(tr("ui.enable_cut"))
        self.chk_enable_cut.setChecked(False)

        self.spin_speed_cut = QSpinBox()
        self.spin_speed_cut.setRange(10, 5000)
        self.spin_speed_cut.setValue(300)
        self.spin_power_cut = QSpinBox()
        self.spin_power_cut.setValue(90)
        self.spin_passes_cut = QSpinBox()
        self.spin_passes_cut.setValue(2)

        legacy_svg_layout.addRow(tr("ui.vector_file_label"), btn_svg)
        legacy_svg_layout.addRow("", self.chk_enable_cut)
        legacy_svg_layout.addRow(tr("ui.cut_speed"), self.spin_speed_cut)
        legacy_svg_layout.addRow(tr("ui.cut_power"), self.spin_power_cut)
        legacy_svg_layout.addRow(tr("ui.cut_passes"), self.spin_passes_cut)
        legacy_svg_box.setLayout(legacy_svg_layout)

        # Ancien mode SVG, conservé pour compatibilité mais jamais affiché :
        # gardé en vie ici (ses champs sont encore lus par la génération).
        legacy_svg_box.setVisible(False)
        self.legacy_svg_box = legacy_svg_box
