"""Fenêtre de réglage de l'imbrication automatique (placement des pièces sur la feuille)."""
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

import nesting
from i18n import tr


def _spin(minimum, maximum, value, decimals=1, step=1.0):
    s = QDoubleSpinBox()
    s.setRange(minimum, maximum)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(value)
    s.setSuffix(" mm")
    return s


class NestingDialog(QDialog):
    """Lit : `settings()` (valeurs à mémoriser) et `options()` (paramètres pour nesting.nest)."""

    def __init__(self, parent, bed_w_mm, bed_h_mm, n_selected, n_total, initial=None):
        super().__init__(parent)
        init = initial or {}
        self.setWindowTitle(tr("nest.title"))
        self.setMinimumWidth(460)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self.combo_scope = QComboBox()
        self.combo_scope.addItem(tr("nest.scope_selection"), "selection")
        self.combo_scope.addItem(tr("nest.scope_all"), "all")
        default_scope = init.get("scope") or ("selection" if n_selected > 0 else "all")
        self.combo_scope.setCurrentIndex(max(0, self.combo_scope.findData(default_scope)))
        self.spin_sheet_w = _spin(10, 5000, init.get("sheet_w", float(bed_w_mm)))
        self.spin_sheet_h = _spin(10, 5000, init.get("sheet_h", float(bed_h_mm)))
        self.spin_origin_x = _spin(0, 5000, init.get("origin_x", 0.0))
        self.spin_origin_y = _spin(0, 5000, init.get("origin_y", 0.0))
        self.spin_spacing = _spin(0, 50, init.get("spacing", 2.0), decimals=1, step=0.5)
        self.spin_margin = _spin(0, 100, init.get("margin", 3.0), decimals=1, step=0.5)
        self.combo_rotations = QComboBox()
        for key, name in (("none", "nest.rot_none"), ("flip", "nest.rot_flip"),
                          ("quarters", "nest.rot_quarters"), ("eighths", "nest.rot_eighths")):
            self.combo_rotations.addItem(tr(name), key)
        self.combo_rotations.setCurrentIndex(max(0, self.combo_rotations.findData(init.get("rotations", "quarters"))))
        self.combo_precision = QComboBox()
        for value, name in ((2.0, "nest.prec_fast"), (1.0, "nest.prec_normal"), (0.5, "nest.prec_precise")):
            self.combo_precision.addItem(tr(name), value)
        self.combo_precision.setCurrentIndex(max(0, self.combo_precision.findData(init.get("cell", 1.0))))

        info = QLabel(tr("nest.count_info").format(selected=n_selected, total=n_total))
        info.setWordWrap(True)
        form.addRow(info)
        form.addRow(tr("nest.scope"), self.combo_scope)
        form.addRow(tr("nest.sheet_w"), self.spin_sheet_w)
        form.addRow(tr("nest.sheet_h"), self.spin_sheet_h)
        form.addRow(tr("nest.origin_x"), self.spin_origin_x)
        form.addRow(tr("nest.origin_y"), self.spin_origin_y)
        form.addRow(tr("nest.spacing"), self.spin_spacing)
        form.addRow(tr("nest.margin"), self.spin_margin)
        form.addRow(tr("nest.rotations"), self.combo_rotations)
        form.addRow(tr("nest.precision"), self.combo_precision)
        hint = QLabel(tr("nest.hint"))
        hint.setWordWrap(True)
        form.addRow(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.buttons = buttons

    def scope(self):
        return self.combo_scope.currentData()

    def options(self):
        """Paramètres de nesting.nest (hors pièces)."""
        return {
            "sheet_w": self.spin_sheet_w.value(), "sheet_h": self.spin_sheet_h.value(),
            "origin": (self.spin_origin_x.value(), self.spin_origin_y.value()),
            "spacing": self.spin_spacing.value(), "margin": self.spin_margin.value(),
            "angles": nesting.ANGLE_SETS[self.combo_rotations.currentData()],
            "cell": self.combo_precision.currentData(),
        }

    def settings(self):
        return {"scope": self.scope(), "sheet_w": self.spin_sheet_w.value(), "sheet_h": self.spin_sheet_h.value(),
                "origin_x": self.spin_origin_x.value(), "origin_y": self.spin_origin_y.value(),
                "spacing": self.spin_spacing.value(), "margin": self.spin_margin.value(),
                "rotations": self.combo_rotations.currentData(), "cell": self.combo_precision.currentData()}
