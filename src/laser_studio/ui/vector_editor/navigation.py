"""Navigation dans le canevas : zoom (molette, loupes, Ctrl++ / Ctrl+-) et cadrage sur des objets, différé tant
que la fenêtre change de taille (plein écran, changement d'onglet). Le calcul du zoom est dans
vector.work_area.fit_scale.

    nav = ViewNavigator(view, plate=lambda: grid.bounds(), items=lambda: selection or everything)
    nav.zoom_in()
    nav.request_recenter([item])     # cadré une fois la vue à sa taille définitive
    nav.view_resized()               # depuis resizeEvent de la vue
"""
from PyQt6.QtCore import QRectF, QTimer
from PyQt6.QtWidgets import QGraphicsView

from laser_studio.vector.work_area import fit_scale

# Facteur de zoom d'un cran de molette, et d'un clic sur les loupes (ou Ctrl++ / Ctrl+-).
WHEEL_ZOOM_STEP = 1.15
BUTTON_ZOOM_STEP = 1.25
# Attente après le dernier redimensionnement avant de cadrer (ms) : la taille du viewport est enfin juste.
RECENTER_DELAY_MS = 120
# Marge (px de scène) gardée autour du plateau et du contenu dans la zone de défilement.
SCENE_MARGIN = 50


class ViewNavigator:
    """Zoom et cadrage de `view` (QGraphicsView). `plate()` : rectangle du plateau dans la scène ; `items()` :
    éléments à cadrer par défaut (la sélection, sinon tous les objets)."""

    def __init__(self, view, plate, items):
        self.view = view
        self._plate = plate
        self._default_items = items
        self._pending_items = None
        self._pending = False
        self._timer = QTimer(view)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._recenter_now)

    # -- zoom

    def wheel(self, delta_y):
        """Cran de molette (angleDelta().y()) : zoom autour du curseur (ancre de la vue)."""
        factor = WHEEL_ZOOM_STEP if delta_y > 0 else 1 / WHEEL_ZOOM_STEP
        self.view.scale(factor, factor)

    def zoom_in(self):
        """Zoom avant, centré sur le milieu de la vue."""
        self._zoom_centered(BUTTON_ZOOM_STEP)

    def zoom_out(self):
        """Zoom arrière, centré sur le milieu de la vue."""
        self._zoom_centered(1 / BUTTON_ZOOM_STEP)

    def _zoom_centered(self, factor):
        view = self.view
        center = view.mapToScene(view.viewport().rect().center())
        anchor = view.transformationAnchor()
        view.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        view.scale(factor, factor)
        view.centerOn(center)
        view.setTransformationAnchor(anchor)

    # -- cadrage

    def request_recenter(self, items=None):
        """Cadre `items` (sinon la sélection, sinon tous les objets) une fois les redimensionnements terminés :
        chaque redimensionnement repousse le cadrage (view_resized)."""
        self._pending_items = list(items) if items else None
        self._pending = True
        self._timer.start(RECENTER_DELAY_MS)

    def view_resized(self):
        if self._pending:
            self._timer.start(RECENTER_DELAY_MS)

    def _recenter_now(self):
        items, self._pending_items, self._pending = self._pending_items, None, False
        self.center_on(items)

    def center_on(self, items=None, margin_px=60, max_scale=6.0):
        """Cadre la vue sur la boîte englobante de `items` (sinon les éléments par défaut, sinon le plateau) :
        zoom qui la fait tenir dans la fenêtre avec une marge (plafonné à `max_scale`), centrée."""
        view = self.view
        scene = view.scene()
        rect = QRectF()
        for item in items or self._default_items():
            try:
                if item.scene() is scene:
                    rect = rect.united(item.sceneBoundingRect())
            except RuntimeError:                        # objet supprimé entre-temps
                pass
        plate = self._plate()
        if rect.isNull():
            rect = plate
        if rect.isNull():
            return
        viewport = view.viewport().size()
        target = fit_scale(rect.width(), rect.height(), viewport.width(), viewport.height(), margin_px, max_scale)
        if target is None:
            return                                     # vue pas encore affichée à sa taille définitive
        # Une QGraphicsView ne défile pas au-delà de sa sceneRect : elle est agrandie pour que la cible soit
        # vraiment centrée (un objet près de l'origine resterait sinon décentré), recalculée depuis le plateau
        # pour ne pas grossir indéfiniment.
        half_w, half_h = viewport.width() / 2.0 / target, viewport.height() / 2.0 / target
        center = rect.center()
        needed = QRectF(center.x() - half_w, center.y() - half_h, 2 * half_w, 2 * half_h)
        base = plate.adjusted(-SCENE_MARGIN, -SCENE_MARGIN, SCENE_MARGIN, SCENE_MARGIN) if not plate.isNull() \
            else QRectF()
        scene.setSceneRect(base.united(rect.adjusted(-SCENE_MARGIN, -SCENE_MARGIN, SCENE_MARGIN, SCENE_MARGIN))
                           .united(needed))
        view.resetTransform()
        view.scale(target, target)
        view.centerOn(center)
