"""Compte à rebours avant la gravure : quelques secondes pour mettre ses lunettes de protection. Un anneau se
vide en continu autour du nombre de secondes, un « tic » doux marque chaque seconde et un accord le départ
(core/sounds.py). Annuler (ou Échap) arrête tout : la gravure ne part pas.

    if CountdownDialog(5, parent).exec() == QDialog.DialogCode.Accepted:
        ...   # la gravure peut démarrer
"""
import math

from PyQt6.QtCore import QElapsedTimer, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from laser_studio.core import sounds
from laser_studio.i18n import tr

FRAME_MS = 16                        # rafraîchissement de l'anneau (~60 images par seconde)
LAST_SECOND = QColor("#f39c12")      # dernière seconde : l'anneau passe à l'orange


class CountdownRing(QWidget):
    """Anneau de progression et nombre de secondes restantes. `remaining` : secondes restantes (décimales),
    `total` : durée du compte à rebours."""

    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.total = total
        self.remaining = float(total)
        self.setMinimumSize(220, 220)

    def set_remaining(self, remaining):
        self.remaining = max(0.0, remaining)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 24
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        width = side * 0.07
        track = QColor(self.palette().color(self.foregroundRole()))
        track.setAlphaF(0.12)
        painter.setPen(QPen(track, width, cap=Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(rect)
        color = LAST_SECOND if self.remaining <= 1.0 else self.palette().color(QPalette.ColorRole.Highlight)
        painter.setPen(QPen(color, width, cap=Qt.PenCapStyle.RoundCap))
        # Part restante, depuis midi dans le sens des aiguilles d'une montre (angles Qt : 1/16 de degré).
        span = int(-360 * 16 * self.remaining / self.total) if self.total else 0
        painter.drawArc(rect, 90 * 16, span)
        font = QFont(self.font())
        font.setPixelSize(int(side * 0.42))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(math.ceil(self.remaining)))


class CountdownDialog(QDialog):
    """Accepted à la fin du compte à rebours, Rejected si l'utilisateur annule. `play` : joue un son (TICK ou
    GO), renvoie False s'il n'a pas pu (un bip système le remplace)."""

    def __init__(self, seconds, parent=None, play=sounds.play):
        super().__init__(parent)
        self.setObjectName("countdown_dialog")
        self.setWindowTitle(tr("countdown.title"))
        self.seconds = seconds
        self._play = play
        self.ring = CountdownRing(seconds)
        title = QLabel(tr("countdown.glasses"))
        font = title.font()
        font.setPointSizeF(font.pointSizeF() * 1.5)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = QLabel()
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("countdown.cancel"))
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self.ring, 1)
        layout.addWidget(self.detail)
        layout.addWidget(buttons, 0, Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(420)
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)
        self._last_whole = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self._timer.isActive():
            self._clock.start()
            self._timer.start()
            self._tick()

    def done(self, result):
        self._timer.stop()
        super().done(result)

    def _sound(self, name):
        if not self._play(name):
            QApplication.beep()                         # pas de lecteur audio : bip système

    def _tick(self):
        remaining = self.seconds - self._clock.elapsed() / 1000.0
        if remaining <= 0:
            self._sound(sounds.GO)
            self.accept()
            return
        self.ring.set_remaining(remaining)
        whole = math.ceil(remaining)                # 5, 4, 3, 2, 1 : un « tic » à chaque nouvelle seconde
        if whole != self._last_whole:
            self._last_whole = whole
            self._sound(sounds.TICK)
            self.detail.setText(tr("countdown.detail").format(seconds=whole))
