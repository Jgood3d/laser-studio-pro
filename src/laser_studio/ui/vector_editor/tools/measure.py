"""Outil mesure : distance entre deux points (deux clics, ou un trait tiré), affichée pendant qu'on
tire puis gardée en annotation (distance, ΔX, ΔY) jusqu'à ce qu'on les efface."""
import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsSimpleTextItem

# Glissé minimal (pixels écran) pour qu'un relâchement termine la mesure.
DRAG_MIN_PX = 8


class MeasureTool:
    """`canvas` : VectorCanvasView ; `snap` : EndpointSnap ; `pen()` : stylo du trait provisoire."""

    def __init__(self, canvas, snap, pen):
        self.canvas = canvas
        self.snap = snap
        self._pen = pen
        self.p1 = None
        self.preview = None
        self.labels = []       # annotations persistantes jusqu'à nouvel outil
        self.text = None       # texte qui suit le trait pendant qu'on le tire
        self.press_px = None   # position écran du premier appui (pour reconnaître un glissé)

    def clear_temp(self):
        self.p1 = None
        self.press_px = None
        for attr in ("preview", "text"):
            item = getattr(self, attr)
            if item is not None:
                try:
                    self.canvas.scene_obj.removeItem(item)
                except RuntimeError:
                    pass
                setattr(self, attr, None)

    def clear_labels(self):
        for it in self.labels:
            try:
                self.canvas.scene_obj.removeItem(it)
            except RuntimeError:
                pass
        self.labels = []

    # -- événements

    def press(self, event):
        """Clic gauche : premier point, ou fin de la mesure."""
        canvas = self.canvas
        pt, snapped = self.snap.snap(canvas.mapToScene(event.position().toPoint()))
        if snapped:
            self.snap.show(pt)
        if self.p1 is None:
            self.p1 = pt
            self.press_px = event.position().toPoint()
            if self.preview is None:
                self.preview = canvas.scene_obj.addPath(QPainterPath(), self._pen())
                self.preview.setZValue(1000)
        else:
            self.end(pt)
        event.accept()

    def move(self, event):
        """Trait et distance provisoires vers le curseur. Renvoie True si l'événement est traité."""
        if self.canvas.draw_tool != "measure" or self.p1 is None:
            return False
        end = self.snap.follow(self.canvas.mapToScene(event.position().toPoint()))
        if self.preview is not None:
            path = QPainterPath()
            path.moveTo(self.p1)
            path.lineTo(end)
            self.preview.setPath(path)
        # La mesure s'affiche pendant qu'on tire le trait, à côté de lui.
        self.update_text(self.p1, end)
        event.accept()
        return True

    def release(self, event):
        """Un trait tiré (appui, glissé, relâché) se termine au relâchement. Un simple clic ne termine
        rien : le second clic donne l'autre extrémité. Renvoie True si l'événement est traité."""
        if (event.button() != Qt.MouseButton.LeftButton or self.canvas.draw_tool != "measure"
                or self.p1 is None or self.press_px is None):
            return False
        released = event.position().toPoint()
        if (released - self.press_px).manhattanLength() < DRAG_MIN_PX:
            return False
        pt, _snapped = self.snap.snap(self.canvas.mapToScene(released))
        self.end(pt)
        event.accept()
        return True

    # -- annotations

    def label_text(self, p1_scene, p2_scene):
        """Texte d'une mesure : distance, puis ΔX / ΔY."""
        x1, y1 = self.canvas.scene_to_mm(p1_scene)
        x2, y2 = self.canvas.scene_to_mm(p2_scene)
        dx, dy = x2 - x1, y2 - y1
        label = f"{math.hypot(dx, dy):.2f} mm"
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            label += f"  (ΔX {dx:+.2f}  ΔY {dy:+.2f})"
        return label

    def place_text(self, text_item, p1_scene, p2_scene):
        """Taille constante à l'écran ; centré au-dessus du milieu du trait, ou à droite s'il est presque vertical."""
        view_scale = max(abs(self.canvas.transform().m11()), 0.01)
        text_item.setScale(1.0 / view_scale)
        rect = text_item.boundingRect()
        w, h = rect.width() / view_scale, rect.height() / view_scale
        gap = 8.0 / view_scale
        mx, my = (p1_scene.x() + p2_scene.x()) / 2, (p1_scene.y() + p2_scene.y()) / 2
        if abs(p2_scene.y() - p1_scene.y()) > 2.0 * abs(p2_scene.x() - p1_scene.x()):
            text_item.setPos(mx + gap, my - h / 2)
        else:
            text_item.setPos(mx - w / 2, my - h - gap)

    def update_text(self, p1_scene, p2_scene):
        """Met à jour (en le créant au besoin) le texte de mesure qui accompagne le trait en cours."""
        if self.text is None:
            self.text = QGraphicsSimpleTextItem()
            self.text.setBrush(QBrush(QColor("#ffcc66")))
            self.text.setZValue(1501)
            self.canvas.scene_obj.addItem(self.text)
        self.text.setText(self.label_text(p1_scene, p2_scene))
        self.place_text(self.text, p1_scene, p2_scene)

    def end(self, p2_scene):
        """Termine la mesure : l'annotation reste affichée, le trait et le texte provisoires disparaissent."""
        p1_scene = self.p1
        self.clear_temp()
        self.snap.hide()
        if p1_scene is not None:
            self.finalize(p1_scene, p2_scene)

    def finalize(self, p1_scene, p2_scene):
        """Ajoute une annotation de mesure (distance + ΔX / ΔY) sur le canevas."""
        scene = self.canvas.scene_obj
        path = QPainterPath()
        path.moveTo(p1_scene)
        path.lineTo(p2_scene)
        pen = QPen(QColor("#ffaa00"), 1.2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        line_item = scene.addPath(path, pen)
        line_item.setZValue(1500)
        text_item = QGraphicsSimpleTextItem(self.label_text(p1_scene, p2_scene))
        text_item.setBrush(QBrush(QColor("#ffcc66")))
        text_item.setZValue(1501)
        scene.addItem(text_item)
        self.place_text(text_item, p1_scene, p2_scene)
        self.labels.extend([line_item, text_item])
