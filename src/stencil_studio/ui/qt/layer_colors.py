"""Couleurs du relief en couches (séparation par couleur), comme la page web (pickAt, setPicks, renderPick,
renderPalette) : pipette sur la photo (jusqu'à 8 couleurs préférées), couleurs piquées retirables, et plaques
du dernier calcul (de l'arrière vers l'avant) à réordonner ou à affiner à la pipette.

    panel = LayerColorsPanel(tr)
    panel.picker_requested.connect(...)      # (active, plaque à affiner ou None)
    panel.picks_changed.connect(...)         # liste de couleurs « #rrggbb »
    panel.order_changed.connect(...)         # « ml_order » : identifiants des plaques, de l'arrière vers l'avant
"""
import re

import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

HEX = re.compile(r"#[0-9a-fA-F]{6}")
MAX_PICKS = 8


def picks_list(text):
    """Couleurs piquées valides de « ml_picks » (picksList)."""
    return [t.strip() for t in str(text or "").split(",") if HEX.fullmatch(t.strip())]


def merge_picks(colors):
    """Couleurs sans doublons trop proches (distance RGB < 35), 8 au plus (setPicks)."""
    kept = []
    for c in colors:
        if not HEX.fullmatch(c):
            continue
        rgb = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
        if any(sum((a - int(k[i:i + 2], 16)) ** 2 for a, i in zip(rgb, (1, 3, 5))) < 35 * 35 for k in kept):
            continue
        kept.append(c)
    return kept[:MAX_PICKS]


def pick_color(rgb, x, y):
    """Couleur « #rrggbb » au point (x, y) de la photo : médiane 7 × 7, qui résiste à l'anticrénelage (pickAt) ;
    None hors de la photo."""
    h, w = rgb.shape[:2]
    x, y = int(round(x)), int(round(y))
    if not (0 <= x < w and 0 <= y < h):
        return None
    patch = rgb[max(0, y - 3):y + 4, max(0, x - 3):x + 4, :3].reshape(-1, 3)
    median = np.sort(patch, axis=0)[len(patch) // 2]
    return "#" + "".join(f"{int(v):02x}" for v in median)


class LayerColorsPanel(QWidget):
    """`tr(texte, **valeurs)` : traduction du catalogue de la page."""

    picker_requested = pyqtSignal(bool, object)
    picks_changed = pyqtSignal(list)
    order_changed = pyqtSignal(str)

    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self.tr = tr
        self.picking, self.target = False, None
        self.picks = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def show_colors(self, picks, plates, palette, order_ids):
        """Redessine le panneau : couleurs piquées, nombre de plaques, palette du dernier calcul."""
        self.picks = list(picks)
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear(item.layout())
        top = QHBoxLayout()
        picker = QToolButton()
        picker.setText(self.tr("Colour picker"))
        picker.setToolTip(self.tr("Click colours on the picture (up to 8). They become preferred centres; the number "
                                  "of plates stays free."))
        picker.setCheckable(True)
        picker.setChecked(self.picking and self.target is None)
        picker.clicked.connect(lambda on: self.request_picker(on, None))
        top.addWidget(picker)
        if picks:
            clear = QToolButton()
            clear.setText(self.tr("Clear picked colours"))
            clear.clicked.connect(lambda: (self.request_picker(False, None), self.picks_changed.emit([])))
            top.addWidget(clear)
        top.addStretch()
        self._layout.addLayout(top)
        if self.picking and self.target is not None:
            caption = self.tr("Click on the image to refine plate colour #{n}. Esc to cancel.", n=self.target + 1)
        elif not picks:
            caption = self.tr("No pick: the colours are found automatically. Click a plate colour above to refine it.")
        elif len(picks) == 1:
            caption = self.tr("Pick at least one more colour (or clear). Number of plates stays free.")
        else:
            caption = self.tr("{n} preferred colours — number of plates remains free (currently {p})",
                              n=len(picks), p=plates)
        label = QLabel(caption)
        label.setWordWrap(True)
        label.setEnabled(False)                        # texte d'aide, en gris
        self._layout.addWidget(label)
        row = QHBoxLayout()
        for i, color in enumerate(picks):
            row.addWidget(self._swatch(color, i, lambda i=i: self.request_picker(True, i)))
            remove = QToolButton()
            remove.setText("×")
            remove.clicked.connect(lambda _c=False, i=i: self.picks_changed.emit([c for j, c in enumerate(picks)
                                                                                    if j != i]))
            row.addWidget(remove)
        row.addStretch()
        self._layout.addLayout(row)
        if palette:
            self._layout.addWidget(QLabel(self.tr("Plates from back to front (use the arrows to reorder)")))
            plates_row = QHBoxLayout()
            for i, color in enumerate(palette):
                plates_row.addWidget(self._swatch(color, i, lambda i=i: self.request_picker(True, i, palette)))
                for text, step in (("◀", -1), ("▶", 1)):
                    arrow = QToolButton()
                    arrow.setText(text)
                    arrow.setEnabled(0 <= i + step < len(order_ids))
                    arrow.clicked.connect(lambda _c=False, i=i, step=step: self._move(order_ids, i, step))
                    plates_row.addWidget(arrow)
            plates_row.addStretch()
            self._layout.addLayout(plates_row)

    def request_picker(self, active, target, palette=None):
        """Pipette en marche (ajout, ou plaque `target` à affiner) ; avec moins de 2 couleurs piquées, on part de
        la palette du calcul pour pouvoir en remplacer une (renderPalette de la page)."""
        self.picking, self.target = bool(active), target if active else None
        self.picker_requested.emit(self.picking, self.target)
        if palette and self.picking and len(self.picks) < 2:
            self.picks_changed.emit(list(palette))

    def _move(self, order_ids, i, step):
        ids = list(order_ids)
        ids[i], ids[i + step] = ids[i + step], ids[i]
        self.order_changed.emit(",".join(str(v) for v in ids))

    def _swatch(self, color, i, on_click):
        button = QToolButton()
        button.setFixedSize(34, 26)
        active = self.picking and self.target == i
        border = "palette(highlight)" if active else "palette(mid)"
        button.setStyleSheet(f"background-color: {color}; border: 2px solid {border}; border-radius: 5px;")
        button.setToolTip(f"{color} — {self.tr('click to refine with pipette')}")
        button.clicked.connect(on_click)
        return button

    @staticmethod
    def _clear(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
