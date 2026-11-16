"""Aperçu 3D de la boîte assemblée : rendu logiciel (QPainter, aucun OpenGL), par l'algorithme du peintre.

Le calcul (faces, tri, projection) est dans `laser_studio.vector.box_3d`, sans Qt. Ici : le widget, qui garde
l'angle de vue (glisser pour tourner, molette pour zoomer, double-clic pour revenir à la vue de départ) et
l'ouverture du couvercle."""
import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from laser_studio.vector import box_3d
from laser_studio.vector import box_generator as bg

DEFAULT_YAW = math.radians(-35.0)
DEFAULT_PITCH = math.radians(25.0)
_MAX_PITCH = math.radians(89.0)


def view_extent(faces_list):
    """(centre (x, y, z), rayon) d'une sphère qui contient toutes les faces de toutes les listes données :
    l'échelle ne change plus quand on tourne la vue ou qu'on ouvre le couvercle."""
    pts = [q for faces in faces_list for face in faces for q in face.points]
    lo = [min(q[i] for q in pts) for i in range(3)]
    hi = [max(q[i] for q in pts) for i in range(3)]
    centre = tuple((a + b) / 2.0 for a, b in zip(lo, hi))
    radius = max(math.dist(centre, q) for q in pts)
    return centre, max(radius, 1.0)


class Box3DView(QWidget):
    """Rendu 3D ; `set_box()` fournit la boîte, `set_open_angle()` ouvre le couvercle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.faces = []
        self._params = None
        self._result = None
        self._open = 0.0
        self._explode = 0.0
        self._material = box_3d.DEFAULT_MATERIAL
        self._yaw, self._pitch, self._zoom = DEFAULT_YAW, DEFAULT_PITCH, 1.0
        self._centre, self._radius = (0.0, 0.0, 0.0), 1.0
        self._drag = None
        self._error = ""
        self.setMinimumSize(320, 280)

    # ------------------------------------------------------------------
    def set_box(self, params, result):
        self._params, self._result, self._error = params, result, ""
        self._rebuild(refit=True)

    def set_error(self, message):
        self._params = self._result = None
        self.faces, self._error = [], message
        self.update()

    def set_open_angle(self, degrees):
        self._open = float(degrees)
        if self._result is not None:
            self._rebuild(refit=False)

    def set_explode(self, percent):
        """Vue éclatée : 0 = boîte assemblée, 100 = pièces écartées au maximum."""
        self._explode = min(max(float(percent), 0.0), 100.0) / 100.0
        if self._result is not None:
            self._rebuild(refit=False)

    def set_material(self, key):
        self._material = key if key in box_3d.MATERIALS else box_3d.DEFAULT_MATERIAL
        self.update()

    def _rebuild(self, refit):
        self.faces = box_3d.build_faces(self._params, self._result, self._open, self._explode)
        if refit:
            lists = [box_3d.build_faces(self._params, self._result, 0.0, 1.0)]
            if bg.lid_kind(self._params) in box_3d.OPENABLE_LIDS:
                lists.append(box_3d.build_faces(self._params, self._result, 100.0, 1.0))
            self._centre, self._radius = view_extent(lists)
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
        """Le rendu actuel (même angle, ouverture, éclaté et matériau) dans une QImage, pour l'export."""
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
            painter.drawText(self.rect().adjusted(14, 14, -14, -14),
                             int(Qt.AlignmentFlag.AlignCenter.value) | int(Qt.TextFlag.TextWordWrap.value), self._error)
            return
        base, grain = box_3d.MATERIALS[self._material]
        scale = min(width, height) / (2.0 * self._radius) * 0.9 * self._zoom
        cx, cy, _ = box_3d.project_point(self._centre, self._yaw, self._pitch)
        mid_x, mid_y = width / 2.0, height / 2.0

        def screen(point):
            return QPointF(mid_x + (point[0] - cx) * scale, mid_y - (point[1] - cy) * scale)

        for _face, pts, holes, shade in box_3d.visible_faces(self.faces, self._yaw, self._pitch):
            path = QPainterPath()
            for loop in [pts] + holes:
                path.moveTo(screen(loop[0]))
                for q in loop[1:]:
                    path.lineTo(screen(q))
                path.closeSubpath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            fill = QColor(*(min(255, int(c * shade)) for c in base))
            painter.setPen(QPen(QColor(*(int(c * 0.5) for c in fill.getRgb()[:3])), 0.6))
            painter.setBrush(fill)
            painter.drawPath(path)
            if grain > 0.0:
                self._draw_grain(painter, path, pts, scale, fill, grain, screen)

    @staticmethod
    def _draw_grain(painter, path, pts, scale, fill, grain, screen):
        """Veinage : fines lignes parallèles au plus long côté de la face, limitées à la face (seulement les
        grandes faces : sur les tranches minces, elles ne se verraient pas)."""
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        if (max(xs) - min(xs)) * (max(ys) - min(ys)) * scale * scale < 900.0:
            return
        best, direction = 0.0, (1.0, 0.0)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            if length > best:
                best, direction = length, ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
        normal = (-direction[1], direction[0])
        cxm, cym = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
        half = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2.0
        step = 2.2
        n = int(half / step)
        r, g, b, _a = fill.getRgb()
        painter.save()
        painter.setClipPath(path)
        for i in range(-n, n + 1):
            wobble = 0.35 * math.sin(i * 1.7) + 0.2 * math.sin(i * 0.43)
            off = i * step + wobble
            alpha = int(18 + 30 * grain * (0.5 + 0.5 * math.sin(i * 2.3 + 1.0)))
            pen = QPen(QColor(int(r * 0.62), int(g * 0.6), int(b * 0.55), alpha), 0.7)
            painter.setPen(pen)
            ox, oy = cxm + normal[0] * off, cym + normal[1] * off
            painter.drawLine(screen((ox - direction[0] * half, oy - direction[1] * half)),
                             screen((ox + direction[0] * half, oy + direction[1] * half)))
        painter.restore()
