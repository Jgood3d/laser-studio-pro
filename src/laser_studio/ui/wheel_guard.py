"""La molette ne change pas une valeur par accident : sur un champ numérique, une liste ou un curseur qui n'a pas
le focus (on fait défiler un panneau de réglages et la souris passe dessus), elle fait défiler la zone qui le
contient au lieu de changer la puissance ou la vitesse sans qu'on le voie. Après un clic dans le champ, la
molette le règle normalement.

    install_wheel_guard(QApplication.instance())     # une fois pour toute l'application
"""
import atexit

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import (QAbstractScrollArea, QAbstractSlider, QAbstractSpinBox, QApplication, QComboBox,
                             QScrollBar)

GUARDED = (QAbstractSpinBox, QComboBox, QAbstractSlider)


def _scroll_area(widget):
    """Zone défilante qui contient `widget` (panneau de réglages, onglet), ou None."""
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            return parent
        parent = parent.parentWidget()
    return None


class WheelGuard(QObject):
    """Filtre d'événements de l'application (voir install_wheel_guard)."""

    def eventFilter(self, watched, event):
        # Une barre de défilement est un curseur, mais c'est elle qui fait défiler la zone : jamais filtrée.
        if event.type() != QEvent.Type.Wheel or not isinstance(watched, GUARDED) or isinstance(watched, QScrollBar):
            return False
        if watched.focusPolicy() == Qt.FocusPolicy.WheelFocus:
            watched.setFocusPolicy(Qt.FocusPolicy.StrongFocus)     # la molette ne lui donne plus le focus
        if watched.hasFocus():
            return False                                            # champ choisi : la molette le règle
        area = _scroll_area(watched)
        if area is not None:
            QApplication.sendEvent(area.viewport(), event)          # la zone défile
        return True


def install_wheel_guard(app):
    """Installe le filtre sur toute l'application, une seule fois (il appartient à l'application). Il est retiré
    juste avant la fin de Python : un filtre Python resté sur l'application serait encore appelé par Qt pendant
    que Python se termine, et le ferait planter. Renvoie le filtre."""
    guard = app.findChild(WheelGuard)
    if guard is None:
        guard = WheelGuard(app)
        app.installEventFilter(guard)
        atexit.register(_remove, app, guard)
    return guard


def _remove(app, guard):
    try:
        app.removeEventFilter(guard)
    except RuntimeError:                       # application déjà détruite
        pass
