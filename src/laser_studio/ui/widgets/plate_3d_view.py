"""Aperçu 3D d'une pièce plate (porte-clés, boule de Noël) : rendu logiciel (QPainter, aucun OpenGL).

Le calcul (extrusion des contours, tri, veinage) est dans `laser_studio.vector.plate_3d`, sans Qt. Ici :
  - `Plate3DView` : le widget, qui garde l'angle de vue (glisser pour tourner, molette pour zoomer, double-clic pour
    revenir à la vue de départ) et le matériau ;
  - `Plate3DPanel` : la vue et ses réglages (matière, épaisseur, export PNG), comme l'aperçu 3D de la boîte.
"""
import math

from PyQt6.QtCore import QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.widgets.auto_hide_label import AutoHideLabel
from laser_studio.vector import box_3d, plate_3d

DEFAULT_YAW = math.radians(-30.0)
DEFAULT_PITCH = math.radians(38.0)
_MAX_PITCH = math.radians(89.0)


class Plate3DView(QWidget):
    """Rendu 3D ; `set_faces()` fournit la pièce (`plate_3d.keychain_faces`, `ornament_faces`…)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.faces = []
        self._message = ""
        self._material = box_3d.DEFAULT_MATERIAL
        self._yaw, self._pitch, self._zoom = DEFAULT_YAW, DEFAULT_PITCH, 1.0
        self._centre, self._radius = (0.0, 0.0, 0.0), 1.0
        self._drag = None
        self.setMinimumSize(320, 280)

    # ------------------------------------------------------------------
    def set_faces(self, faces):
        self.faces, self._message = list(faces), ""
        self._centre, self._radius = plate_3d.extent(self.faces)
        self.update()

    def set_message(self, message):
        """Rien à montrer (erreur de saisie, lot…) : le texte remplace la pièce."""
        self.faces, self._message = [], message
        self.update()

    def set_material(self, key):
        self._material = key if key in box_3d.MATERIALS else box_3d.DEFAULT_MATERIAL
        self.update()

    def reset_view(self):
        self._yaw, self._pitch, self._zoom = DEFAULT_YAW, DEFAULT_PITCH, 1.0
        self.update()

    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        self._drag = (event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        x, y = event.position().x(), event.position().y()
        self._yaw -= (x - self._drag[0]) * 0.01
        self._pitch = min(max(self._pitch + (y - self._drag[1]) * 0.01, -_MAX_PITCH), _MAX_PITCH)
        self._drag = (x, y)
        self.update()

    def mouseReleaseEvent(self, _event):
        self._drag = None

    def mouseDoubleClickEvent(self, _event):
        self.reset_view()

    def wheelEvent(self, event):
        step = 1.0 + 0.0012 * event.angleDelta().y()
        self._zoom = min(max(self._zoom * step, 0.3), 6.0)
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _event):
        painter = QPainter(self)
        self._paint(painter, self.width(), self.height(), self.palette().window().color())

    def render_image(self, width=1600, height=1200, background=None):
        """Le rendu actuel (même angle, zoom et matériau) dans une QImage, pour l'export."""
        image = QImage(int(width), int(height), QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        self._paint(painter, int(width), int(height), background or QColor(255, 255, 255))
        painter.end()
        return image

    def save_png(self, path, width=1600, height=1200):
        return self.render_image(width, height).save(path, "PNG")

    def _paint(self, painter, width, height, background):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(0, 0, width, height, background)
        if not self.faces:
            painter.setPen(QColor(217, 83, 79))
            painter.drawText(QRect(0, 0, width, height).adjusted(14, 14, -14, -14),
                             int(Qt.AlignmentFlag.AlignCenter.value) | int(Qt.TextFlag.TextWordWrap.value),
                             self._message)
            return
        base, grain = box_3d.MATERIALS[self._material]
        burnt = plate_3d.engrave_color(self._material)
        scale = min(width, height) / (2.0 * self._radius) * 0.9 * self._zoom
        cx, cy, _ = box_3d.project_point(self._centre, self._yaw, self._pitch)
        mid_x, mid_y = width / 2.0, height / 2.0

        def screen(point):
            return QPointF(mid_x + (point[0] - cx) * scale, mid_y - (point[1] - cy) * scale)

        for face, pts, holes, shade in plate_3d.visible_faces(self.faces, self._yaw, self._pitch):
            path = QPainterPath()
            for loop in [pts] + holes:
                path.moveTo(screen(loop[0]))
                for q in loop[1:]:
                    path.lineTo(screen(q))
                path.closeSubpath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            engraved = face.kind == "engrave"
            fill = QColor(*(min(255, int(c * shade)) for c in (burnt if engraved else base)))
            if engraved:
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                painter.setPen(QPen(QColor(*(int(c * 0.5) for c in fill.getRgb()[:3])), 0.6))
            painter.setBrush(fill)
            painter.drawPath(path)
            if grain > 0.0:
                self._draw_grain(painter, path, face, grain, fill, screen)

    def _draw_grain(self, painter, path, face, grain, fill, screen):
        """Veinage : fines lignes parallèles au fil du bois, limitées à la face."""
        lines = plate_3d.grain_lines(face, grain)
        if not lines:
            return
        red, green, blue, _alpha = fill.getRgb()
        painter.save()
        painter.setClipPath(path)
        for start, end, alpha in lines:
            painter.setPen(QPen(QColor(int(red * 0.62), int(green * 0.6), int(blue * 0.55), alpha), 0.7))
            painter.drawLine(screen(box_3d.project_point(start, self._yaw, self._pitch)),
                             screen(box_3d.project_point(end, self._yaw, self._pitch)))
        painter.restore()


class Plate3DPanel(QWidget):
    """La vue 3D, la matière (comme pour la boîte), l'épaisseur de la plaque et l'export en PNG.

    `thickness_changed` : l'épaisseur a changé, la pièce est à reconstruire (`set_faces`). La matière, elle, ne
    change que le dessin. `settings()` rend ce qu'il faut mémoriser (« material », « thickness_mm »)."""

    thickness_changed = pyqtSignal()

    def __init__(self, saved=None, parent=None):
        super().__init__(parent)
        saved = saved or {}
        self.view3d = Plate3DView()
        self.view3d.setToolTip(tr("box.view3d_hint"))

        self.combo_material = QComboBox()
        for key in box_3d.MATERIALS:
            self.combo_material.addItem(tr(f"box.material_{key}"), key)
        index = self.combo_material.findData(saved.get("material", box_3d.DEFAULT_MATERIAL))
        self.combo_material.setCurrentIndex(max(0, index))
        self.view3d.set_material(self.combo_material.currentData())
        self.combo_material.currentIndexChanged.connect(
            lambda *_: self.view3d.set_material(self.combo_material.currentData()))

        self.spin_thickness = QDoubleSpinBox()
        self.spin_thickness.setRange(plate_3d.MIN_THICKNESS, plate_3d.MAX_THICKNESS)
        self.spin_thickness.setDecimals(2)
        self.spin_thickness.setSingleStep(0.1)
        self.spin_thickness.setSuffix(" mm")
        self.spin_thickness.setValue(saved.get("thickness_mm", plate_3d.DEFAULT_THICKNESS))
        self.spin_thickness.setToolTip(tr("plate3d.thickness_tip"))
        self.spin_thickness.valueChanged.connect(lambda *_: self.thickness_changed.emit())

        self.btn_export_png = QPushButton(tr("box.export_png"))
        self.btn_export_png.clicked.connect(self._export_png)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_note = AutoHideLabel()            # ex. « Lot : l'aperçu montre le premier prénom »
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setStyleSheet("color: #ffb86b;")
        layout.addWidget(self.lbl_note)
        layout.addWidget(self.view3d, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("box.material")))
        row.addWidget(self.combo_material, 1)
        row.addWidget(QLabel(tr("plate3d.thickness")))
        row.addWidget(self.spin_thickness)
        row.addWidget(self.btn_export_png)
        layout.addLayout(row)
        hint = QLabel(tr("box.view3d_hint"))
        hint.setStyleSheet("color: #8b93a7; font-size: 12px;")
        layout.addWidget(hint)

    def material(self):
        return self.combo_material.currentData()

    def thickness(self):
        return self.spin_thickness.value()

    def settings(self):
        return {"material": self.material(), "thickness_mm": self.thickness()}

    def set_faces(self, faces, note=""):
        """La pièce à montrer ; `note` : une remarque affichée au-dessus (vide : rien)."""
        self.lbl_note.setText(note)
        self.view3d.set_faces(faces)

    def set_message(self, message):
        """Pas de pièce : `message` (erreur de saisie…) prend la place de la vue."""
        self.lbl_note.setText("")
        self.view3d.set_message(message)

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("box.export_png"), tr("plate3d.default_png"),
                                              tr("box.png_filter"))
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.view3d.save_png(path)
