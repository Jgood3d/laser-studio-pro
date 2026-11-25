"""Photo et cadre de découpe, comme la vue source de la page web (drawSource, computeView, souris).

Outils (`tool`, comme les boutons de la page) :
- « move » : glisser déplace le cadre, la poignée au-dessus le fait tourner (Maj : crans de 15°) ; la molette
  change sa taille, Alt + molette le fait tourner ; en format personnalisé, les poignées des coins et des côtés
  le redimensionnent (Maj : proportions gardées) et le double-clic lui donne toute la photo (custom_size_changed) ;
- « box » : rectangle autour du sujet (subject_box_drawn) ;
- « fg » / « bg » / « erase » : repères peints, vert = sujet, rouge = fond, gomme (hints_painted, PNG à la
  taille de la photo affichée, comme la page l'envoie à /api/hints).
Ce qui sort du cadre est assombri ; les repères s'affichent en transparence.

    view = SourceView(state)
    view.frame_changed.connect(lambda moving: ...)       # moving : glissement en cours
    view.rotation_changed.connect(lambda deg: ...)

Le cadre ({"cx", "cy", "w"}, fractions de la photo) appartient à la fenêtre (`frame()` / `set_frame()`) ;
les limites et les dimensions viennent de models/frame.py, comme dans la page.
"""
import math

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF, QTransform
from PyQt6.QtWidgets import QApplication, QWidget

from ...models import frame as frame_model

HANDLES = ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))   # coins et côtés du cadre


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
    subject_box_drawn = pyqtSignal(object)        # {"x", "y", "w", "h"} (fractions de la photo), ou None
    hints_painted = pyqtSignal(bytes)             # repères peints, PNG
    custom_size_changed = pyqtSignal()            # custom_w, custom_h et size_mm changés dans `state`
    message = pyqtSignal(str)                     # texte (anglais, à traduire) pour la barre d'état

    def __init__(self, state, placeholder="", parent=None):
        super().__init__(parent)
        self.state = state
        self.placeholder = placeholder
        self.pixmap = None
        self.iw = self.ih = 0
        self._frame = {"cx": 0.5, "cy": 0.5, "w": 1.0}
        self._drag = None
        self._rotating = False
        self._resize = None
        self._box_start = None
        self._painting = None             # dernier point peint (pixels de la photo)
        self.tool = "move"
        self.subject_box = None           # rectangle du sujet (B de la page)
        self.hints = None                 # repères peints (QImage à la taille de la photo affichée)
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)

    # -- image et cadre

    def set_image(self, qimage):
        """Nouvelle photo : cadre de départ, centré (loadDisplay de la page)."""
        self.pixmap = QPixmap.fromImage(qimage)
        self.iw, self.ih = qimage.width(), qimage.height()
        self.subject_box = None
        self.hints = QImage(self.iw, self.ih, QImage.Format.Format_ARGB32)
        self.hints.fill(Qt.GlobalColor.transparent)
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
        if frame_model.free_on(self.state):               # placement libre : bords de la photo en pointillés
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1 / s, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(0, 0, self.iw, self.ih))
        painter.setOpacity(0.6)
        painter.drawImage(0, 0, self.hints)
        painter.setOpacity(1.0)
        fw, fh = frame_model.dims(self.state, self.iw, self.ih, self._frame)
        frame_path = self._outline().map(shape_path(self.state.get("shape"), fw, fh))
        shade = QPainterPath()
        shade.addRect(QRectF(-1e5, -1e5, 2e5, 2e5))
        painter.fillPath(shade.subtracted(frame_path), QColor(0, 0, 0, 158))   # hors du cadre : assombri
        accent = QApplication.palette().color(QPalette.ColorRole.Highlight)
        painter.setPen(QPen(accent, 2 / s))
        painter.drawPath(frame_path)
        if self._resizable():                          # poignées de redimensionnement : coins et côtés
            painter.setBrush(accent)
            painter.setPen(QPen(Qt.GlobalColor.white, 1.5 / s))
            t = self._outline()
            for hx, hy in HANDLES:
                c = t.map(QPointF(hx * fw / 2, hy * fh / 2))
                painter.drawRect(QRectF(c.x() - 5 / s, c.y() - 5 / s, 10 / s, 10 / s))
        if not frame_model.is_full(self.state):         # poignée de rotation au-dessus du cadre
            top, handle = self._rotation_handle(s)
            painter.drawLine(top, handle)
            painter.setBrush(accent)
            painter.setPen(QPen(Qt.GlobalColor.white, 1.5 / s))
            painter.drawEllipse(handle, 6 / s, 6 / s)
        if self.subject_box:                            # rectangle du sujet, en pointillés
            b = self.subject_box
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#35d0ff"), 2 / s, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(b["x"] * self.iw, b["y"] * self.ih, b["w"] * self.iw, b["h"] * self.ih))

    def _resizable(self):
        s = self.state
        return s.get("aspect") == "custom" and s.get("shape") != "circle" and not frame_model.is_full(s)

    def _handle_at(self, x, y, scale):
        """Poignée (coin / côté) sous le point (x, y) de la photo, ou None (frameHit)."""
        fw, fh = frame_model.dims(self.state, self.iw, self.ih, self._frame)
        local = self._outline().inverted()[0].map(QPointF(x, y))
        best, distance = None, 11 / scale
        for hx, hy in HANDLES:
            d = math.hypot(local.x() - hx * fw / 2, local.y() - hy * fh / 2)
            if d < distance:
                best, distance = (hx, hy), d
        return best

    def _outline(self):
        """Repère du cadre : son centre, tourné."""
        t = QTransform()
        t.translate(self._frame["cx"] * self.iw, self._frame["cy"] * self.ih)
        t.rotate(frame_model.rotation(self.state))
        return t

    def _rotation_handle(self, scale):
        """(haut du cadre, poignée) en pixels de la photo : 22 px d'écran au-dessus du cadre."""
        _fw, fh = frame_model.dims(self.state, self.iw, self.ih, self._frame)
        t = self._outline()
        return t.map(QPointF(0, -fh / 2)), t.map(QPointF(0, -fh / 2 - 22 / scale))

    # -- souris (glisser : déplacer ; molette : taille ; Alt + molette : rotation)

    def mousePressEvent(self, event):
        if self.pixmap is None or event.button() != Qt.MouseButton.LeftButton:
            return
        x, y = self._to_image(event.position())
        if self.tool == "move":
            scale = self._view()[0]
            if not frame_model.is_full(self.state):
                handle = self._rotation_handle(scale)[1]
                if math.hypot(x - handle.x(), y - handle.y()) * scale < 12:
                    self._rotating = True
                    return
            hit = self._handle_at(x, y, scale) if self._resizable() else None
            if hit:
                fw, fh = frame_model.dims(self.state, self.iw, self.ih, self._frame)
                self._resize = {"h": hit, "fw": fw, "fh": fh, "cx": self._frame["cx"] * self.iw,
                                "cy": self._frame["cy"] * self.ih,
                                "mm": frame_model.frame_width_mm(self.state, self.iw, self.ih) / max(1.0, fw)}
                return
            self._drag = (x, y, self._frame["cx"], self._frame["cy"])
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self.tool == "box":
            self._box_start = (min(max(x / self.iw, 0), 1), min(max(y / self.ih, 0), 1))
            self.subject_box = None
        else:
            self._painting = (x, y)
            self._paint(x, y, x, y)

    def mouseMoveEvent(self, event):
        if self.pixmap is None:
            return
        x, y = self._to_image(event.position())
        if self._resize is not None:
            self._resize_to(x, y, bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        elif self._rotating:
            cx, cy = self._frame["cx"] * self.iw, self._frame["cy"] * self.ih
            angle = math.degrees(math.atan2(x - cx, -(y - cy)))         # 0 : poignée en haut, sens horaire
            step = 15 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            self.rotation_changed.emit(max(-180.0, min(180.0, float(round(angle / step) * step))))
        elif self._drag is not None:
            x0, y0, cx, cy = self._drag
            self.set_frame({"cx": cx + (x - x0) / self.iw, "cy": cy + (y - y0) / self.ih, "w": self._frame["w"]})
            self.frame_changed.emit(True)
        elif self._box_start is not None:
            bx, by = min(max(x / self.iw, 0), 1), min(max(y / self.ih, 0), 1)
            x0, y0 = self._box_start
            self.subject_box = {"x": min(x0, bx), "y": min(y0, by), "w": abs(bx - x0), "h": abs(by - y0)}
            self.update()
        elif self._painting is not None:
            self._paint(*self._painting, x, y)
            self._painting = (x, y)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.tool == "move" else Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event):
        if self._resize is not None:
            self._resize = None
            self.frame_changed.emit(False)
        elif self._rotating:
            self._rotating = False
        elif self._drag is not None:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.frame_changed.emit(False)
        elif self._box_start is not None:
            self._box_start = None
            b = self.subject_box
            if b and (b["w"] < 0.03 or b["h"] < 0.03):    # trop petit : pas de rectangle (comme la page)
                self.subject_box = None
            self.update()
            self.subject_box_drawn.emit(self.subject_box)
        elif self._painting is not None:
            self._painting = None
            self.hints_painted.emit(self.hints_png())

    def _resize_to(self, x, y, keep_ratio):
        """Redimensionne le cadre par la poignée tenue (rsDrag de la page) : le côté opposé reste en place ;
        20 à 400 mm pour le plus grand côté, 5 mm au moins pour le plus petit."""
        d = self._resize
        rr = math.radians(frame_model.rotation(self.state))
        dx, dy = x - d["cx"], y - d["cy"]
        qx, qy = dx * math.cos(rr) + dy * math.sin(rr), -dx * math.sin(rr) + dy * math.cos(rr)
        fw, fh, lcx, lcy = d["fw"], d["fh"], 0.0, 0.0
        smallest = 20 / d["mm"] * 0.25
        hx, hy = d["h"]
        if hx:
            fixed = -hx * d["fw"] / 2
            fw, lcx = max(smallest, (qx - fixed) * hx), (qx + fixed) / 2
        if hy:
            fixed = -hy * d["fh"] / 2
            fh, lcy = max(smallest, (qy - fixed) * hy), (qy + fixed) / 2
        if keep_ratio and hx and hy:
            k = max(fw / d["fw"], fh / d["fh"])
            fw, fh = d["fw"] * k, d["fh"] * k
            lcx, lcy = -hx * d["fw"] / 2 + hx * fw / 2, -hy * d["fh"] / 2 + hy * fh / 2
        wmm, hmm = round(fw * d["mm"] * 10) / 10, round(fh * d["mm"] * 10) / 10
        if max(wmm, hmm) > 400 or min(wmm, hmm) < 5:
            return
        self.state.update(custom_w=wmm, custom_h=hmm, size_mm=max(20.0, max(wmm, hmm)))
        self.set_frame({"cx": (d["cx"] + lcx * math.cos(rr) - lcy * math.sin(rr)) / self.iw,
                        "cy": (d["cy"] + lcx * math.sin(rr) + lcy * math.cos(rr)) / self.ih, "w": fw / self.iw})
        self.custom_size_changed.emit()
        self.frame_changed.emit(True)

    def mouseDoubleClickEvent(self, event):
        """Format personnalisé : le cadre prend toute la photo, à l'échelle actuelle (dblclick de la page)."""
        if self.pixmap is None or self.tool != "move" or not self._resizable():
            return
        mm = frame_model.image_width_mm(self.state, self.iw, self.ih, self._frame) / self.iw
        wmm, hmm = round(self.iw * mm * 10) / 10, round(self.ih * mm * 10) / 10
        if max(wmm, hmm) > 400 or min(wmm, hmm) < 5:
            self.message.emit("The whole image is larger than 400 mm at this scale: reduce the image width first.")
            return
        self.state.update(custom_w=wmm, custom_h=hmm, size_mm=max(20.0, wmm, hmm))
        self.set_frame({"cx": 0.5, "cy": 0.5, "w": 1.0})
        self.custom_size_changed.emit()
        self.frame_changed.emit(False)

    # -- repères peints

    def _paint(self, x0, y0, x1, y1):
        """Trait de pinceau sur les repères (brushStyle / paintLine de la page) : vert, rouge ou gomme, de la
        largeur « brush » en pixels d'écran."""
        painter = QPainter(self.hints)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.tool == "erase":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        color = QColor(0, 255, 0) if self.tool == "fg" else QColor(255, 0, 0)
        width = float(self.state.get("brush") or 30) / self._view()[0]
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        painter.end()
        self.update()

    def hints_png(self):
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self.hints.save(buffer, "PNG")
        return bytes(data)

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
