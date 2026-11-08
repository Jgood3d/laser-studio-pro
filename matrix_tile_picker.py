"""Aperçu d'image avec un cadre à déplacer, pour choisir la zone de la matrice de test."""
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QSizePolicy, QWidget

from i18n import tr

_PREVIEW_MAX_PX = 800


class TilePicker(QWidget):
    """Affiche une image et un cadre rouge (la zone à graver). Un clic ou un glissé de la
    souris place le centre du cadre ; le cadre reste toujours dans l'image."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._pixmap = None
        self._aspect = 1.0           # largeur / hauteur de l'image
        self._frame = (0.2, 0.2)     # taille du cadre, en fraction de l'image
        self._center = (0.5, 0.5)    # centre du cadre, en fraction de l'image

    # --- données ---------------------------------------------------------------------------
    def set_image(self, pil_gray):
        """Image PIL en niveaux de gris (ou None pour effacer l'aperçu)."""
        if pil_gray is None:
            self._pixmap = None
            self.update()
            return
        img = pil_gray.convert("L")
        img.thumbnail((_PREVIEW_MAX_PX, _PREVIEW_MAX_PX))
        w, h = img.size
        qimg = QImage(img.tobytes(), w, h, w, QImage.Format.Format_Grayscale8).copy()
        self._pixmap = QPixmap.fromImage(qimg)
        self._aspect = w / h
        self._center = self._clamped(*self._center)
        self.update()

    def set_frame_fraction(self, fw, fh):
        self._frame = (min(max(fw, 0.001), 1.0), min(max(fh, 0.001), 1.0))
        self._center = self._clamped(*self._center)
        self.update()

    def center(self):
        """Centre du cadre, en fraction de l'image (origine : coin haut-gauche)."""
        return self._center

    # --- géométrie -------------------------------------------------------------------------
    def _clamped(self, cx, cy):
        fw, fh = self._frame
        cx = 0.5 if fw >= 1.0 else min(max(cx, fw / 2.0), 1.0 - fw / 2.0)
        cy = 0.5 if fh >= 1.0 else min(max(cy, fh / 2.0), 1.0 - fh / 2.0)
        return cx, cy

    def _image_rect(self):
        """Zone du widget occupée par l'image (ratio conservé, centrée)."""
        avail = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        if avail.width() <= 0 or avail.height() <= 0:
            return QRectF()
        w = avail.width()
        h = w / self._aspect
        if h > avail.height():
            h = avail.height()
            w = h * self._aspect
        return QRectF(avail.center().x() - w / 2.0, avail.center().y() - h / 2.0, w, h)

    def _set_center_from_pos(self, pos: QPointF):
        rect = self._image_rect()
        if self._pixmap is None or rect.isEmpty():
            return
        cx = (pos.x() - rect.left()) / rect.width()
        cy = (pos.y() - rect.top()) / rect.height()
        new_center = self._clamped(cx, cy)
        if new_center != self._center:
            self._center = new_center
            self.update()
            self.changed.emit()

    # --- événements ------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_center_from_pos(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._set_center_from_pos(event.position())

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self._image_rect()
        if self._pixmap is None or rect.isEmpty():
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                             tr("ui.mat_image_none"))
            return
        painter.drawPixmap(rect, self._pixmap, QRectF(self._pixmap.rect()))
        fw, fh = self._frame
        cx, cy = self._center
        frame = QRectF(rect.left() + (cx - fw / 2.0) * rect.width(),
                       rect.top() + (cy - fh / 2.0) * rect.height(),
                       fw * rect.width(), fh * rect.height())
        # Hors du cadre : assombri, pour que la zone gravée ressorte.
        shade = QColor(0, 0, 0, 120)
        for part in (QRectF(rect.left(), rect.top(), rect.width(), frame.top() - rect.top()),
                     QRectF(rect.left(), frame.bottom(), rect.width(), rect.bottom() - frame.bottom()),
                     QRectF(rect.left(), frame.top(), frame.left() - rect.left(), frame.height()),
                     QRectF(frame.right(), frame.top(), rect.right() - frame.right(), frame.height())):
            if part.width() > 0 and part.height() > 0:
                painter.fillRect(part, shade)
        pen = QPen(QColor("#ff3030"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(frame)
