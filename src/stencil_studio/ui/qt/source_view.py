"""Photo et cadre de découpe, comme la vue source de la page web (drawSource, computeView, souris) : le cadre
(forme du pochoir) se déplace à la souris, la molette change sa taille, Alt + molette le fait tourner. Ce qui
sort du cadre est assombri.

    view = SourceView(state, frame_model)
    view.frame_changed.connect(lambda moving: ...)       # moving : glissement en cours
    view.rotation_changed.connect(lambda deg: ...)

Le cadre ({"cx", "cy", "w"}, fractions de la photo) appartient à la fenêtre (`frame()` / `set_frame()`) ;
les limites et les dimensions viennent de models/frame.py, comme dans la page.
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF, QTransform
from PyQt6.QtWidgets import QApplication, QWidget

from ...models import frame as frame_model


def shape_path(shape, w, h):
    """Contour de la forme du pochoir (framePath de la page), centré sur l'origine, de taille w × h."""
    path = QPainterPath()
    x, y = -w / 2, -h / 2
    if shape in ("circle", "oval"):
        path.addEllipse(QRectF(x, y, w, h))
    elif shape in ("heart", "star", "tree"):
        path.addPolygon(QPolygonF([QPointF(x + px * w, y + py * h) for px, py in frame_model.unit_polygon(shape)]))
        path.closeSubpath()
    elif shape == "rrect":
        r = 0.18 * min(w, h)
        path.addRoundedRect(QRectF(x, y, w, h), r, r)
    else:
        path.addRect(QRectF(x, y, w, h))
    return path


class SourceView(QWidget):
    """`state` : réglages de la fenêtre (dict partagé, lu à chaque dessin). Émet frame_changed(glissement en
    cours) et rotation_changed(degrés)."""

    frame_changed = pyqtSignal(bool)
    rotation_changed = pyqtSignal(float)

    def __init__(self, state, placeholder="", parent=None):
        super().__init__(parent)
        self.state = state
        self.placeholder = placeholder
        self.pixmap = None
        self.iw = self.ih = 0
        self._frame = {"cx": 0.5, "cy": 0.5, "w": 1.0}
        self._drag = None
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)

    # -- image et cadre

    def set_image(self, qimage):
        """Nouvelle photo : cadre de départ, centré (loadDisplay de la page)."""
        self.pixmap = QPixmap.fromImage(qimage)
        self.iw, self.ih = qimage.width(), qimage.height()
        self.set_frame({"cx": 0.5, "cy": 0.5, "w": 1.0})

    def frame(self):
        return dict(self._frame)

    def set_frame(self, f):
        """Cadre ramené dans ses limites (clampFrame) puis redessiné."""
        if self.iw:
            self._frame = frame_model.clamp(self.state, self.iw, self.ih, f)
        self.update()

    def refresh_frame(self):
        """Un réglage (forme, format, taille, rotation, placement libre) a changé : cadre recalé."""
        if frame_model.is_full(self.state):
            self._frame = {"cx": 0.5, "cy": 0.5, "w": 1.0}        # image complète : toute la photo
        self.set_frame(self._frame)

    # -- géométrie de l'affichage (computeView)

    def _view(self):
        """(échelle, décalage x, décalage y) de la photo dans le widget."""
        W, H = self.width(), self.height()
        if not frame_model.free_on(self.state):
            s = min(W / self.iw, H / self.ih)
            return s, (W - self.iw * s) / 2, (H - self.ih * s) / 2
        # placement libre : la vue montre la photo ET le cadre, avec une marge
        fw, fh = frame_model.dims(self.state, self.iw, self.ih, self._frame)
        ra = math.radians(frame_model.rotation(self.state))
        ex = abs(math.cos(ra)) * fw / 2 + abs(math.sin(ra)) * fh / 2
        ey = abs(math.sin(ra)) * fw / 2 + abs(math.cos(ra)) * fh / 2
        cx, cy = self._frame["cx"] * self.iw, self._frame["cy"] * self.ih
        x0, x1 = min(0, cx - ex), max(self.iw, cx + ex)
        y0, y1 = min(0, cy - ey), max(self.ih, cy + ey)
        pw, ph = (x1 - x0) * 0.1, (y1 - y0) * 0.1
        s = min(W / (x1 - x0 + 2 * pw), H / (y1 - y0 + 2 * ph))
        return s, (W - (x1 - x0) * s) / 2 - x0 * s, (H - (y1 - y0) * s) / 2 - y0 * s

    def _to_image(self, pos):
        s, ox, oy = self._view()
        return (pos.x() - ox) / s, (pos.y() - oy) / s

    # -- dessin

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.pixmap is None:
            painter.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.placeholder)
            return
        s, ox, oy = self._view()
        painter.translate(ox, oy)
        painter.scale(s, s)
        painter.drawPixmap(0, 0, self.pixmap)
        fw, fh = frame_model.dims(self.state, self.iw, self.ih, self._frame)
        outline = QTransform()
        outline.translate(self._frame["cx"] * self.iw, self._frame["cy"] * self.ih)
        outline.rotate(frame_model.rotation(self.state))
        frame_path = outline.map(shape_path(self.state.get("shape"), fw, fh))
        shade = QPainterPath()
        shade.addRect(QRectF(-1e5, -1e5, 2e5, 2e5))
        painter.fillPath(shade.subtracted(frame_path), QColor(0, 0, 0, 110))   # hors du cadre : assombri
        accent = QApplication.palette().color(QPalette.ColorRole.Highlight)
        painter.setPen(QPen(accent, 2 / s))
        painter.drawPath(frame_path)

    # -- souris (glisser : déplacer ; molette : taille ; Alt + molette : rotation)

    def mousePressEvent(self, event):
        if self.pixmap is not None and event.button() == Qt.MouseButton.LeftButton:
            x, y = self._to_image(event.position())
            self._drag = (x, y, self._frame["cx"], self._frame["cy"])
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._drag is None:
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.pixmap is not None else Qt.CursorShape.ArrowCursor)
            return
        x, y = self._to_image(event.position())
        x0, y0, cx, cy = self._drag
        self.set_frame({"cx": cx + (x - x0) / self.iw, "cy": cy + (y - y0) / self.ih, "w": self._frame["w"]})
        self.frame_changed.emit(True)

    def mouseReleaseEvent(self, event):
        if self._drag is not None:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.frame_changed.emit(False)

    def wheelEvent(self, event):
        if self.pixmap is None:
            return
        delta = -event.angleDelta().y() * 100 / 120           # même sens et même pas que la page (deltaY)
        if event.modifiers() & Qt.KeyboardModifier.AltModifier and not frame_model.is_full(self.state):
            delta = -event.angleDelta().x() * 100 / 120 or delta   # Alt : certaines souris passent en horizontal
            angle = max(-180.0, min(180.0, float(self.state.get("rot") or 0) + (1 if delta > 0 else -1)))
            self.rotation_changed.emit(angle)
            return
        self.set_frame({**self._frame, "w": max(0.05, self._frame["w"] * math.exp(delta * 0.0015))})
        self.frame_changed.emit(False)
