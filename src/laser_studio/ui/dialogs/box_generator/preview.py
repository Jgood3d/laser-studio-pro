"""Aperçu 2D de la boîte : les panneaux tels qu'ils seront découpés (même disposition que sur le
plateau), avec les fentes de cloison et la position du décor. Mis à jour à chaque changement de réglage.

Le calcul de l'échelle (`fit_transform`) et les libellés (`panel_label`) sont de simples fonctions,
testables sans fenêtre."""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from laser_studio.i18n import tr

FACE_LABEL_KEYS = {
    "front": "box.face_front", "back": "box.face_back", "left": "box.face_left",
    "right": "box.face_right", "top": "box.face_top", "bottom": "box.face_bottom",
}
_MARGIN = 14.0
_DEFAULT_SVG_MM = 20.0


def panel_label(name):
    """Nom affiché d'un panneau : « Face avant », « Cloison X2 », « Rebord »…"""
    if name in FACE_LABEL_KEYS:
        return tr(FACE_LABEL_KEYS[name])
    if name == "lip":
        return tr("box.panel_lip")
    for prefix, key in (("divider_x", "box.panel_divider_x"), ("divider_y", "box.panel_divider_y")):
        if name.startswith(prefix):
            return tr(key).format(n=name[len(prefix):])
    return name


def fit_transform(width, height, view_w, view_h, margin=_MARGIN):
    """(échelle px/mm, décalage x, décalage y du bord HAUT) pour centrer width x height mm dans la vue."""
    if width <= 0 or height <= 0:
        return 1.0, margin, margin
    scale = min(max(view_w - 2 * margin, 1.0) / width, max(view_h - 2 * margin, 1.0) / height)
    return scale, (view_w - width * scale) / 2.0, (view_h - height * scale) / 2.0


class BoxPreview(QWidget):
    """Dessin des panneaux ; `set_result()` ou `set_error()` rafraîchit l'affichage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result = None
        self._decors = []
        self._too_big = False
        self._error = ""
        self.setMinimumSize(320, 280)

    def set_result(self, result, decors=(), too_big=False):
        self._result, self._decors, self._too_big, self._error = result, list(decors), bool(too_big), ""
        self.update()

    def set_error(self, message):
        self._result, self._error = None, message
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        background, ink = palette.window().color(), palette.windowText().color()
        painter.fillRect(self.rect(), background)
        if self._result is None:
            painter.setPen(QColor(217, 83, 79))
            painter.drawText(QRectF(self.rect()).adjusted(_MARGIN, _MARGIN, -_MARGIN, -_MARGIN),
                             int(Qt.AlignmentFlag.AlignCenter.value) | int(Qt.TextFlag.TextWordWrap.value), self._error)
            return
        result = self._result
        scale, ox, oy = fit_transform(result.width, result.height, self.width(), self.height())

        def screen(x, y):
            return QPointF(ox + x * scale, oy + (result.height - y) * scale)

        def polygon(points):
            path = QPainterPath()
            path.moveTo(screen(*points[0]))
            for point in points[1:]:
                path.lineTo(screen(*point))
            path.closeSubpath()
            return path

        fill = QColor(ink)
        fill.setAlpha(34)
        label_font = QFont(self.font())
        label_font.setPointSizeF(max(self.font().pointSizeF() - 1.0, 7.0))
        for panel in result.panels:
            path = polygon(panel.placed())
            for hole in panel.placed_holes():
                path.addPath(polygon(hole))              # remplissage pair-impair : le trou reste vide
            path.setFillRule(Qt.FillRule.OddEvenFill)
            painter.setPen(QPen(ink, 1.2))
            painter.setBrush(fill)
            painter.drawPath(path)
            x0, y0, x1, y1 = panel.bounds()
            painter.setFont(label_font)
            painter.setPen(ink)
            painter.drawText(QRectF(screen(x0, y1), screen(x1, y0)).adjusted(5, 3, -3, -3),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, panel_label(panel.name))
        self._paint_decors(painter, result, scale, screen)
        if self._too_big:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(240, 173, 78), 1.5, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(screen(0, result.height), screen(result.width, 0)).adjusted(-3, -3, 3, 3))
        painter.setFont(label_font)
        painter.setPen(ink)
        painter.drawText(QRectF(self.rect()).adjusted(4, 0, -4, -2),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                         tr("box.preview_footprint").format(fw=result.width, fh=result.height))

    def _paint_decors(self, painter, result, scale, screen):
        accent = QColor(217, 119, 6)
        by_name = {panel.name: panel for panel in result.panels}
        for decor in self._decors:
            panel = by_name.get(decor.face)
            if panel is None:
                continue                                  # face absente (ex. dessus d'une boîte ouverte)
            fx, fy = panel.face_center()
            centre = screen(fx + decor.dx, fy + decor.dy)
            painter.setPen(accent)
            if decor.kind == "text":
                font = QFont(decor.font_family)
                font.setPixelSize(max(int(decor.size_mm * scale), 5))
                font.setBold(decor.bold)
                font.setItalic(decor.italic)
                painter.setFont(font)
                painter.drawText(QRectF(centre.x() - 400, centre.y() - 200, 800, 400),
                                 Qt.AlignmentFlag.AlignCenter, decor.text)
            else:
                side = (decor.width_mm if decor.width_mm > 0 else _DEFAULT_SVG_MM) * scale
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(accent, 1.2, Qt.PenStyle.DashLine))
                box = QRectF(centre.x() - side / 2, centre.y() - side / 2, side, side)
                painter.drawRect(box)
                painter.drawText(box, Qt.AlignmentFlag.AlignCenter, "SVG")
