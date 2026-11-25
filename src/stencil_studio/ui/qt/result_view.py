"""Image d'aperçu, et ce qui se trace dessus comme dans la page web (MB, GV, mbDraw, segDist) : ponts manuels
(trait court en travers d'une découpe à garder) et guides du low poly (sommets et arêtes). Tout est en fractions
de l'image (0..1), comme la page l'envoie au calcul (« mbr », « lpg »).

    view = ResultView()
    view.set_image(qimage)
    view.mode = "bridge"            # ou "guide", ou None
    view.edited.connect(...)        # pont ou guide ajouté / retiré
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy

GUIDE_VIEWS = ("result", "overlay", "original")      # vues où les guides se voient et se posent (GUIDE_VIEWS)
GUIDE_COLOR, BRIDGE_COLOR = QColor("#35d0ff"), QColor("#d83a3a")


class ImageView(QLabel):
    """Image toujours ajustée à la place disponible, proportions gardées."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self._pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(200, 200)
        self.setWordWrap(True)

    def set_image(self, qimage):
        self._pixmap = QPixmap.fromImage(qimage)
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        if self._pixmap is not None:
            self.setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))


def segment_distance(p, s, w, h):
    """Distance en pixels d'écran du point `p` (x, y) au segment `s` (x1, y1, x2, y2), en fractions (segDist)."""
    ax, ay, bx, by, px, py = s[0] * w, s[1] * h, s[2] * w, s[3] * h, p[0] * w, p[1] * h
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy or 1
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class ResultView(ImageView):
    edited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.mode = None                 # None, "bridge" ou "guide"
        self.view = "result"
        self.lowpoly = False
        self.bridges = []                # ponts manuels [[x1, y1, x2, y2]]
        self.guides = {"pts": [], "edges": []}
        self._drag = None

    def clear(self):
        """Nouvelle image : plus de ponts ni de guides (loadDisplay de la page)."""
        self.bridges, self.guides = [], {"pts": [], "edges": []}
        self.update()

    def mode_ok(self):
        """Le tracé n'a lieu que dans la vue où il se voit (modeOK)."""
        if self.mode == "bridge":
            return self.view == "result"
        return self.mode == "guide" and self.view in GUIDE_VIEWS

    def image_rect(self):
        """Rectangle de l'image affichée dans le widget (resRect), ou None."""
        if self._pixmap is None:
            return None
        size = self._pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        return QRectF((self.width() - size.width()) / 2, (self.height() - size.height()) / 2,
                      size.width(), size.height())

    def _fraction(self, pos):
        r = self.image_rect()
        return (min(1.0, max(0.0, (pos.x() - r.x()) / r.width())), min(1.0, max(0.0, (pos.y() - r.y()) / r.height())))

    # -- dessin

    def paintEvent(self, event):
        super().paintEvent(event)
        r = self.image_rect()
        if r is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        point = lambda x, y: QPointF(r.x() + x * r.width(), r.y() + y * r.height())     # noqa: E731
        if self.lowpoly and self.view in GUIDE_VIEWS:
            painter.setPen(QPen(GUIDE_COLOR, 2.5, cap=Qt.PenCapStyle.RoundCap))
            for s in self.guides["edges"]:
                painter.drawLine(point(s[0], s[1]), point(s[2], s[3]))
            painter.setBrush(GUIDE_COLOR)
            painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
            for q in self.guides["pts"]:
                painter.drawEllipse(point(q[0], q[1]), 5, 5)
        if self._drag:
            guide = self.mode == "guide"
            painter.setPen(QPen(GUIDE_COLOR if guide else BRIDGE_COLOR, 2.5 if guide else 4,
                                Qt.PenStyle.DashLine if guide else Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            (ax, ay), (bx, by) = self._drag
            painter.drawLine(point(ax, ay), point(bx, by))

    # -- souris

    def mousePressEvent(self, event):
        if self.mode_ok() and self.image_rect() is not None and event.button() == Qt.MouseButton.LeftButton:
            p = self._fraction(event.position())
            self._drag = [p, p]

    def mouseMoveEvent(self, event):
        if self._drag:
            self._drag[1] = self._fraction(event.position())
            self.update()
        else:
            self.setCursor(Qt.CursorShape.CrossCursor if self.mode_ok() else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if not self._drag:
            return
        (ax, ay), (bx, by) = self._drag
        self._drag = None
        r = self.image_rect()
        w, h = r.width(), r.height()
        length = math.hypot((bx - ax) * w, (by - ay) * h)
        f = lambda v: round(v, 4)                       # noqa: E731
        if self.mode == "bridge":
            if length < 6:                              # simple clic : retire le pont le plus proche
                near = [(segment_distance((ax, ay), s, w, h), i) for i, s in enumerate(self.bridges)]
                near = [n for n in near if n[0] < 12]
                if not near:
                    self.update()
                    return
                del self.bridges[min(near)[1]]
            else:
                self.bridges.append([f(ax), f(ay), f(bx), f(by)])
        elif self.mode == "guide":
            if length < 6:                              # clic : retire un sommet ou une arête, sinon pose un sommet
                pts, edges = self.guides["pts"], self.guides["edges"]
                pi = next((i for i, q in enumerate(pts) if math.hypot((q[0] - ax) * w, (q[1] - ay) * h) < 10), None)
                ei = next((i for i, s in enumerate(edges) if segment_distance((ax, ay), s, w, h) < 8), None)
                if pi is not None:
                    del pts[pi]
                elif ei is not None:
                    del edges[ei]
                else:
                    pts.append([f(ax), f(ay)])
            else:
                self.guides["edges"].append([f(ax), f(ay), f(bx), f(by)])
        self.update()
        self.edited.emit()
