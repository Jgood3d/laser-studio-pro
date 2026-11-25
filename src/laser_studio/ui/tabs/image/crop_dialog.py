"""Fenêtre « Recadrer » de l'onglet « Graver une image » : l'image entière (telle que chargée ou pivotée)
et le cadre à garder, tracé à la souris.

- glisser hors du cadre : trace un nouveau cadre ;
- glisser dans le cadre : le déplace ;
- glisser un coin ou un bord : le redimensionne (proportions gardées si la case est cochée).

    dialog = CropDialog(image_pil, crop_box, mm_per_px, window)
    dialog.accepted.connect(lambda: image_controller.crop(dialog.box()))     # box() None : toute l'image
    dialog.show()        # non modale : se déplace seule, sans entraîner la fenêtre principale
"""
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout,
)

from laser_studio.i18n import tr
from laser_studio.ui.app.theme import theme_color

# Distance (pixels écran) à laquelle un clic attrape un coin ou un bord du cadre.
GRAB_PX = 10
# Plus petit cadre accepté (pixels de l'image).
MIN_SIZE_PX = 4


def pil_to_qimage(image):
    """Image PIL -> QImage (niveaux de gris), copiée : indépendante du tampon PIL."""
    gray = image if image.mode == "L" else image.convert("L")
    data = gray.tobytes()
    return QImage(data, gray.width, gray.height, gray.width, QImage.Format.Format_Grayscale8).copy()


class CropView(QGraphicsView):
    """Image et cadre de recadrage (`rect`, en pixels de l'image). Émet rect_changed(QRectF)."""

    rect_changed = pyqtSignal(QRectF)

    def __init__(self, qimage, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.pixmap_item = QGraphicsPixmapItem(QPixmap.fromImage(qimage))
        self.scene().addItem(self.pixmap_item)
        self.bounds = QRectF(0, 0, qimage.width(), qimage.height())
        self.setSceneRect(self.bounds)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setBackgroundBrush(theme_color("canvas", "#303030"))
        self.setMouseTracking(True)
        self.rect = QRectF(self.bounds)
        self.keep_ratio = False
        self._drag = None              # ("new" | "move" | "resize", point de départ, cadre de départ, bords)

    def showEvent(self, event):
        super().showEvent(event)
        self.fitInView(self.bounds, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.bounds, Qt.AspectRatioMode.KeepAspectRatio)

    def set_rect(self, rect):
        rect = QRectF(rect).normalized().intersected(self.bounds)
        if rect.width() < MIN_SIZE_PX or rect.height() < MIN_SIZE_PX:
            return
        self.rect = rect
        self.viewport().update()
        self.rect_changed.emit(QRectF(rect))

    # -- dessin : extérieur assombri, cadre et poignées

    def drawForeground(self, painter, _exposed):
        # Quatre bandes autour du cadre, assombries : on voit tout de suite ce qui sera retiré.
        shade = QBrush(QColor(0, 0, 0, 150))
        b, r = self.bounds, self.rect
        for band in (QRectF(b.left(), b.top(), b.width(), r.top() - b.top()),
                     QRectF(b.left(), r.bottom(), b.width(), b.bottom() - r.bottom()),
                     QRectF(b.left(), r.top(), r.left() - b.left(), r.height()),
                     QRectF(r.right(), r.top(), b.right() - r.right(), r.height())):
            if band.width() > 0 and band.height() > 0:
                painter.fillRect(band, shade)
        pen = QPen(QColor("#00d4ff"), 0)
        pen.setCosmetic(True)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect)
        size = GRAB_PX / max(self.transform().m11(), 1e-6) * 0.8
        painter.setBrush(QColor("#00d4ff"))
        for corner in (self.rect.topLeft(), self.rect.topRight(), self.rect.bottomLeft(), self.rect.bottomRight()):
            painter.drawRect(QRectF(corner.x() - size / 2, corner.y() - size / 2, size, size))

    # -- souris

    def _edges_at(self, scene_pos):
        """Bords du cadre sous la souris : ensemble parmi "l", "r", "t", "b"."""
        tol = GRAB_PX / max(self.transform().m11(), 1e-6)
        r = self.rect
        edges = set()
        if r.top() - tol <= scene_pos.y() <= r.bottom() + tol:
            if abs(scene_pos.x() - r.left()) <= tol:
                edges.add("l")
            elif abs(scene_pos.x() - r.right()) <= tol:
                edges.add("r")
        if r.left() - tol <= scene_pos.x() <= r.right() + tol:
            if abs(scene_pos.y() - r.top()) <= tol:
                edges.add("t")
            elif abs(scene_pos.y() - r.bottom()) <= tol:
                edges.add("b")
        return edges

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        pos = self.mapToScene(event.position().toPoint())
        edges = self._edges_at(pos)
        if edges:
            self._drag = ("resize", pos, QRectF(self.rect), edges)
        elif self.rect.contains(pos):
            self._drag = ("move", pos, QRectF(self.rect), set())
        else:
            self._drag = ("new", pos, QRectF(self.rect), set())
        event.accept()

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.position().toPoint())
        if self._drag is None:
            edges = self._edges_at(pos)
            cursors = {frozenset("lt"): Qt.CursorShape.SizeFDiagCursor, frozenset("rb"): Qt.CursorShape.SizeFDiagCursor,
                       frozenset("rt"): Qt.CursorShape.SizeBDiagCursor, frozenset("lb"): Qt.CursorShape.SizeBDiagCursor}
            if frozenset(edges) in cursors:
                self.viewport().setCursor(cursors[frozenset(edges)])
            elif edges & {"l", "r"}:
                self.viewport().setCursor(Qt.CursorShape.SizeHorCursor)
            elif edges & {"t", "b"}:
                self.viewport().setCursor(Qt.CursorShape.SizeVerCursor)
            elif self.rect.contains(pos):
                self.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            return
        kind, start, rect0, edges = self._drag
        pos = QPointF(min(max(pos.x(), 0.0), self.bounds.width()), min(max(pos.y(), 0.0), self.bounds.height()))
        if kind == "move":
            moved = rect0.translated(pos - start)
            dx = min(0.0, self.bounds.right() - moved.right()) + max(0.0, self.bounds.left() - moved.left())
            dy = min(0.0, self.bounds.bottom() - moved.bottom()) + max(0.0, self.bounds.top() - moved.top())
            self.set_rect(moved.translated(dx, dy))
        elif kind == "new":
            self.set_rect(self._with_ratio(QRectF(start, pos), rect0, "rb"))
        else:
            r = QRectF(rect0)
            if "l" in edges:
                r.setLeft(pos.x())
            if "r" in edges:
                r.setRight(pos.x())
            if "t" in edges:
                r.setTop(pos.y())
            if "b" in edges:
                r.setBottom(pos.y())
            self.set_rect(self._with_ratio(r, rect0, "".join(sorted(edges))))
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag = None
        event.accept()

    def _with_ratio(self, rect, reference, edges):
        """Avec « Garder les proportions » : même rapport largeur / hauteur que le cadre de départ. Un bord
        haut ou bas seul fixe la hauteur (la largeur suit) ; sinon la largeur fixe la hauteur."""
        if not self.keep_ratio or reference.height() <= 0:
            return rect
        ratio = reference.width() / reference.height()
        rect = rect.normalized()
        if edges and set(edges) <= {"t", "b"}:
            return QRectF(rect.left(), rect.top(), rect.height() * ratio, rect.height())
        return QRectF(rect.left(), rect.top(), rect.width(), rect.width() / ratio)


class CropDialog(QDialog):
    """`image` : image PIL entière ; `box` : cadre actuel (gauche, haut, droite, bas) ou None ;
    `mm_per_px` : échelle de gravure, pour afficher la taille du cadre en mm."""

    def __init__(self, image, box=None, mm_per_px=0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("img.crop_title"))
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(900, 680)
        self._mm_per_px = mm_per_px
        self.view = CropView(pil_to_qimage(image))
        if box is not None:
            self.view.set_rect(QRectF(QPointF(box[0], box[1]), QPointF(box[2], box[3])))
        hint = QLabel(tr("img.crop_hint"))
        hint.setWordWrap(True)
        self.size_label = QLabel()
        self.keep_ratio = QCheckBox(tr("img.crop_keep_ratio"))
        self.keep_ratio.toggled.connect(lambda on: setattr(self.view, "keep_ratio", on))
        whole = QPushButton(tr("img.crop_whole"))
        whole.clicked.connect(lambda: self.view.set_rect(self.view.bounds))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(self.keep_ratio)
        row.addWidget(whole)
        row.addStretch()
        row.addWidget(self.size_label)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.view, 1)
        layout.addLayout(row)
        layout.addWidget(buttons)
        self.view.rect_changed.connect(self._show_size)
        self._show_size(self.view.rect)

    def _show_size(self, rect):
        w, h = int(round(rect.width())), int(round(rect.height()))
        text = tr("img.crop_size").format(w=w, h=h)
        if self._mm_per_px > 0:
            text += f"  ({w * self._mm_per_px:.1f} × {h * self._mm_per_px:.1f} mm)"
        self.size_label.setText(text)

    def box(self):
        """Cadre choisi (gauche, haut, droite, bas) en pixels entiers, ou None pour toute l'image."""
        r = self.view.rect
        box = (int(round(r.left())), int(round(r.top())), int(round(r.right())), int(round(r.bottom())))
        bounds = self.view.bounds
        return None if box == (0, 0, int(bounds.width()), int(bounds.height())) else box
