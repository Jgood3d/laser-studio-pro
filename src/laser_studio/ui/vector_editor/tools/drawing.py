"""Outils de dessin à la souris : ligne, rectangle (3 points), cercle, ellipse.

Ligne : deux points. Rectangle : base en deux clics, puis profondeur tirée (ou saisie). Cercle (du
centre vers le rayon) et ellipse (d'un coin du cadre à l'autre) : un seul clic-glisser, ou deux clics.
Après le premier point, des dimensions peuvent être tapées au clavier (« 25 », « 30x20 ») puis
validées par Entrée ; après la base d'un rectangle, sa profondeur.
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen

from laser_studio.models.vector_objects import ShapeObject

# Outils qui tracent une forme (la mesure est à part, voir measure.py).
SHAPE_TOOLS = ("line", "rect", "circle", "ellipse")


class DrawingTool:
    """`canvas` : VectorCanvasView (son outil actif : canvas.draw_tool) ; `snap` : EndpointSnap."""

    def __init__(self, canvas, snap):
        self.canvas = canvas
        self.snap = snap
        self.layer_id = None            # calque des formes dessinées (None : calque SVG par défaut)
        self.start_scene = None
        self.preview_item = None
        # Saisie de dimensions au clavier après le 1er point (ex: "25" ou "30x20")
        self.dim_buffer = ""
        self.last_cursor_scene = None
        # Phases : None → "p1" (2e clic) → "p2" (prêt à tirer) → "depth" (en train de tirer)
        self.phase = None
        self.base_p1 = None
        self.base_p2 = None
        self.awaiting_second = False
        self.awaiting_depth = False
        self.depth_dragging = False
        # Cercle / ellipse d'un seul geste : bouton enfoncé depuis le 1er point (clic-glisser), position du
        # clic à l'écran pour distinguer un simple clic (2 clics) d'un glissé.
        self.pressed = False
        self.press_screen = None

    @property
    def tool(self):
        return self.canvas.draw_tool

    def in_progress(self):
        """Vrai si une forme est commencée (Échap l'annule au lieu de quitter l'outil)."""
        return self.phase is not None or self.awaiting_depth or self.awaiting_second

    def cancel_preview(self):
        if self.preview_item is not None:
            try:
                self.canvas.scene_obj.removeItem(self.preview_item)
            except RuntimeError:
                pass
            self.preview_item = None
        self.snap.hide()
        self.start_scene = None
        self.dim_buffer = ""
        self.last_cursor_scene = None
        self.base_p1 = None
        self.base_p2 = None
        self.phase = None
        self.awaiting_second = False
        self.awaiting_depth = False
        self.depth_dragging = False
        self.pressed = False
        self.press_screen = None

    def default_layer_id(self):
        if self.layer_id:
            return self.layer_id
        layers = self.canvas.layer_manager
        layer = layers.default_svg_layer()
        return layer.id if layer else (layers.layers[0].id if layers.layers else None)

    def preview_pen(self):
        layer = self.canvas.layer_manager.get(self.default_layer_id())
        color = QColor(layer.color) if layer else QColor("#00aaff")
        pen = QPen(color, 1.5, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        return pen

    def _ensure_preview_item(self):
        if self.preview_item is None:
            self.preview_item = self.canvas.scene_obj.addPath(QPainterPath(), self.preview_pen())
            self.preview_item.setZValue(1000)

    def _add(self, obj):
        """Forme terminée : une étape d'annulation, ajoutée au document et sélectionnée."""
        canvas = self.canvas
        canvas.push_undo_snapshot()
        item = canvas.add_object(obj)
        canvas.scene_obj.clearSelection()
        item.setSelected(True)

    # -- événements

    def press(self, event):
        """Clic gauche avec un outil de forme (SHAPE_TOOLS) : point suivant de la forme."""
        canvas = self.canvas
        if not canvas.layer_manager.layers:
            event.accept()
            return
        raw = canvas.mapToScene(event.position().toPoint())
        pt, snapped = self.snap.snap(raw)
        if snapped:
            self.snap.show(pt)

        phase = self.phase

        # --- Phase profondeur : début du TIRÉ (après les 2 clics nœuds) ---
        if phase in ("p2", "depth") and self.tool == "rect" and self.base_p1 is not None and self.base_p2 is not None:
            self.phase = "depth"
            self.depth_dragging = True
            self.awaiting_depth = True
            self.last_cursor_scene = pt
            event.accept()
            return

        # --- Phase p1 : 2e CLIC (pas de tiré) → place le 2e nœud ---
        if phase == "p1" and self.start_scene is not None:
            if self.tool in ("line", "circle", "ellipse"):
                start = self.start_scene
                self.cancel_preview()
                obj = self.create_drawn_object(start, pt)
                if obj is not None:
                    self._add(obj)
                event.accept()
                return
            # Rectangle : largeur figée, on n'autorise le tiré QU'après ce clic
            self.base_p1 = QPointF(self.start_scene)
            self.base_p2 = QPointF(pt)
            self.phase = "p2"
            self.awaiting_second = False
            self.awaiting_depth = True
            self.depth_dragging = False
            self.dim_buffer = ""
            self.last_cursor_scene = pt
            self._ensure_preview_item()
            # Aperçu = segment de base uniquement (pas encore de profondeur)
            path = QPainterPath()
            path.moveTo(self.base_p1)
            path.lineTo(self.base_p2)
            self.preview_item.setPath(path)
            self.preview_item.setPen(self.preview_pen())
            event.accept()
            return

        # --- Phase None : 1er CLIC ---
        if phase is None:
            self.start_scene = pt
            self.phase = "p1"
            self.pressed = self.tool in ("circle", "ellipse")
            self.press_screen = event.position().toPoint()
            self.awaiting_second = True
            self.awaiting_depth = False
            self.depth_dragging = False
            self.base_p1 = None
            self.base_p2 = None
            self.dim_buffer = ""
            self.last_cursor_scene = pt
            self._ensure_preview_item()
            event.accept()
            return

        event.accept()

    def move(self, event):
        """Aperçu de la forme en cours. Renvoie True si l'événement est traité."""
        canvas = self.canvas
        # Aperçu profondeur : UNIQUEMENT pendant le tiré (bouton enfoncé)
        if (self.tool == "rect" and self.depth_dragging and self.base_p1 is not None
                and self.base_p2 is not None and self.preview_item is not None):
            end = self.snap.follow(canvas.mapToScene(event.position().toPoint()))
            self.last_cursor_scene = end
            depth = self.depth_from_cursor(self.base_p1, self.base_p2, end)
            path = self.preview_path_base_depth(self.base_p1, self.base_p2, depth, ellipse=(self.tool == "ellipse"))
            self.preview_item.setPath(path)
            self.preview_item.setPen(self.preview_pen())
            event.accept()
            return True

        # Phase p2 (base fixée, pas encore de tiré) : segment fixe + accroche
        if (self.tool == "rect" and self.phase == "p2" and self.base_p1 is not None
                and self.base_p2 is not None and self.preview_item is not None):
            self.last_cursor_scene = self.snap.follow(canvas.mapToScene(event.position().toPoint()))
            path = QPainterPath()
            path.moveTo(self.base_p1)
            path.lineTo(self.base_p2)
            self.preview_item.setPath(path)
            self.preview_item.setPen(self.preview_pen())
            event.accept()
            return True

        # Phase p1 : ligne du 1er point vers le curseur (sans tenir le bouton)
        if (self.tool in SHAPE_TOOLS and self.phase == "p1" and self.start_scene is not None
                and self.preview_item is not None):
            end = self.snap.follow(canvas.mapToScene(event.position().toPoint()))
            self.last_cursor_scene = end
            if self.tool in ("circle", "ellipse"):
                path = self.shape_preview_path(self.tool, self.start_scene, end)
            else:
                path = QPainterPath()
                path.moveTo(self.start_scene)
                path.lineTo(end)
            self.preview_item.setPath(path)
            self.preview_item.setPen(self.preview_pen())
            event.accept()
            return True
        return False

    def release(self, event):
        """Fin d'un clic-glisser (cercle / ellipse d'un geste, profondeur d'un rectangle). Renvoie True si
        l'événement est traité."""
        canvas = self.canvas
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        # Cercle / ellipse : relâchement après un clic-glisser = forme terminée, d'un seul geste. Un simple
        # clic sans glisser laisse l'outil en attente du 2e clic.
        if self.tool in ("circle", "ellipse") and self.phase == "p1" and self.pressed:
            self.pressed = False
            moved = 0
            if self.press_screen is not None:
                moved = (event.position().toPoint() - self.press_screen).manhattanLength()
            if moved >= 4 and self.start_scene is not None:
                pt, _ = self.snap.snap(canvas.mapToScene(event.position().toPoint()))
                start = self.start_scene
                self.cancel_preview()
                obj = self.create_drawn_object(start, pt)
                if obj is not None:
                    self._add(obj)
            event.accept()
            return True

        # Rectangle : fin du TIRÉ de profondeur (relâchement)
        if self.tool == "rect" and self.depth_dragging and self.base_p1 is not None and self.base_p2 is not None:
            pt, _ = self.snap.snap(canvas.mapToScene(event.position().toPoint()))
            depth = self.depth_from_cursor(self.base_p1, self.base_p2, pt)
            obj = self.create_rect_from_base(self.base_p1, self.base_p2, depth, ellipse=(self.tool == "ellipse"))
            self.depth_dragging = False
            self.cancel_preview()
            if obj is not None:
                self._add(obj)
            event.accept()
            return True
        return False

    def key(self, event):
        """Saisie de dimensions après le 1er point, ou de la profondeur après la base. Renvoie True si la
        touche est prise."""
        if not ((self.awaiting_second or self.awaiting_depth) and self.tool in SHAPE_TOOLS):
            return False
        key = event.key()
        text = event.text() or ""
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.commit_dimensions():
                event.accept()
                return True
        if key == Qt.Key.Key_Backspace:
            self.dim_buffer = self.dim_buffer[:-1]
            event.accept()
            return True
        if text and (text.isdigit() or text in ".,xX*-+"):
            if text in "X*":
                text = "x"
            if text == ",":
                text = "."
            self.dim_buffer += text
            event.accept()
            return True
        return False

    # -- formes

    def create_drawn_object(self, start_scene, end_scene):
        """Crée un ShapeObject (ligne / rect / ellipse) à partir de deux points scène."""
        canvas = self.canvas
        x1, y1 = canvas.scene_to_mm(start_scene)
        x2, y2 = canvas.scene_to_mm(end_scene)
        layer_id = self.default_layer_id()
        if not layer_id:
            return None

        if self.tool == "line":
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 0.05:
                return None
            angle = math.degrees(math.atan2(dy, dx))
            return ShapeObject(shape_type="Ligne", width_mm=length, height_mm=0.1, layer_id=layer_id,
                               x_mm=x1, y_mm=y1, rotation_deg=angle)

        if self.tool == "circle":
            # Cercle : 1er point = centre, 2e point = un point du cercle.
            radius = math.hypot(x2 - x1, y2 - y1)
            if radius < 0.05:
                return None
            return ShapeObject(shape_type="Ellipse", width_mm=2 * radius, height_mm=2 * radius, layer_id=layer_id,
                               x_mm=x1 - radius, y_mm=y1 - radius)

        # Rectangle / ellipse : coin bas-gauche + largeur / hauteur positives
        left, right = (x1, x2) if x1 <= x2 else (x2, x1)
        bottom, top = (y1, y2) if y1 <= y2 else (y2, y1)
        w, h = right - left, top - bottom
        if w < 0.05 and h < 0.05:
            return None
        w = max(w, 0.05)
        h = max(h, 0.05)
        shape_type = "Ellipse" if self.tool == "ellipse" else "Rectangle"
        return ShapeObject(shape_type=shape_type, width_mm=w, height_mm=h, layer_id=layer_id, x_mm=left, y_mm=bottom)

    def create_drawn_object_from_dims(self, start_scene, dims, direction_scene=None):
        """Crée une forme à partir du 1er point + dimensions clavier.

        Ligne : dims = (length_mm,) — direction = curseur ou horizontale.
        Rect/ellipse : dims = (width_mm, height_mm) — signe selon quadrant curseur.
        Cercle : dims = (rayon_mm,) — le 1er point est le centre.
        """
        canvas = self.canvas
        x1, y1 = canvas.scene_to_mm(start_scene)
        layer_id = self.default_layer_id()
        if not layer_id:
            return None

        if self.tool == "line":
            length = float(dims[0])
            if length < 0.05:
                return None
            # Direction : vers le curseur si dispo, sinon +X
            if direction_scene is not None:
                x2, y2 = canvas.scene_to_mm(direction_scene)
                dx, dy = x2 - x1, y2 - y1
                norm = math.hypot(dx, dy)
                if norm < 1e-9:
                    dx, dy = 1.0, 0.0
                else:
                    dx, dy = dx / norm, dy / norm
            else:
                dx, dy = 1.0, 0.0
            angle = math.degrees(math.atan2(dy, dx))
            return ShapeObject(shape_type="Ligne", width_mm=length, height_mm=0.1, layer_id=layer_id,
                               x_mm=x1, y_mm=y1, rotation_deg=angle)

        if self.tool == "circle":
            # Cercle : la valeur saisie est le rayon, le 1er point est le centre.
            radius = abs(float(dims[0]))
            if radius < 0.05:
                return None
            return ShapeObject(shape_type="Ellipse", width_mm=2 * radius, height_mm=2 * radius, layer_id=layer_id,
                               x_mm=x1 - radius, y_mm=y1 - radius)

        if len(dims) < 2:
            return None
        w, h = abs(float(dims[0])), abs(float(dims[1]))
        if w < 0.05 and h < 0.05:
            return None
        w, h = max(w, 0.05), max(h, 0.05)
        # Quadrant selon le curseur par rapport au 1er point
        sx = sy = 1.0
        if direction_scene is not None:
            x2, y2 = canvas.scene_to_mm(direction_scene)
            if x2 < x1:
                sx = -1.0
            if y2 < y1:
                sy = -1.0
        left = x1 if sx >= 0 else x1 - w
        bottom = y1 if sy >= 0 else y1 - h
        shape_type = "Ellipse" if self.tool == "ellipse" else "Rectangle"
        return ShapeObject(shape_type=shape_type, width_mm=w, height_mm=h, layer_id=layer_id, x_mm=left, y_mm=bottom)

    @staticmethod
    def parse_dimensions(text):
        """Parse '25', '25mm', '30x20', '30 x 20', '30,20' → tuple de floats (mm)."""
        t = (text or "").strip().lower().replace(",", "x").replace(" ", "")
        t = t.replace("mm", "")
        if not t:
            return None
        if "x" in t:
            parts = [p for p in t.split("x") if p]
            try:
                vals = tuple(float(p) for p in parts[:2])
            except ValueError:
                return None
            return vals if vals else None
        try:
            return (float(t),)
        except ValueError:
            return None

    def commit_dimensions(self):
        """Valide le buffer de dimensions et crée l'objet."""
        dims = self.parse_dimensions(self.dim_buffer)
        if not dims:
            return False

        # Profondeur seule après base 2 nœuds (rect / ellipse)
        if self.awaiting_depth and self.base_p1 is not None and self.base_p2 is not None and self.tool == "rect":
            depth = float(dims[0])
            # Signe : côté du curseur par rapport à la base
            if self.last_cursor_scene is not None:
                auto = self.depth_from_cursor(self.base_p1, self.base_p2, self.last_cursor_scene)
                depth = -abs(depth) if auto < 0 else abs(depth)
            obj = self.create_rect_from_base(self.base_p1, self.base_p2, depth, ellipse=(self.tool == "ellipse"))
            self.cancel_preview()
            if obj is None:
                return False
            self._add(obj)
            return True

        if not self.awaiting_second or self.start_scene is None:
            return False
        if self.tool == "line" and len(dims) >= 1:
            pass
        elif self.tool == "circle" and len(dims) >= 1:
            pass
        elif self.tool in ("rect", "ellipse") and len(dims) >= 2:
            pass
        elif self.tool in ("rect", "ellipse") and len(dims) == 1:
            dims = (dims[0], dims[0])  # carré / cercle
        else:
            return False
        obj = self.create_drawn_object_from_dims(self.start_scene, dims, self.last_cursor_scene)
        self.cancel_preview()
        if obj is None:
            return False
        self._add(obj)
        return True

    @staticmethod
    def shape_preview_path(tool, start_scene, end_scene):
        """Aperçu scène d'un cercle (centre = 1er point, passe par le curseur) ou d'une ellipse (cadre
        d'un coin à l'autre)."""
        path = QPainterPath()
        if tool == "circle":
            radius = math.hypot(end_scene.x() - start_scene.x(), end_scene.y() - start_scene.y())
            path.addEllipse(start_scene, radius, radius)
        else:
            path.addEllipse(QRectF(start_scene, end_scene).normalized())
        return path

    def depth_from_cursor(self, p1_scene, p2_scene, cursor_scene):
        """Distance signée du curseur à la droite p1→p2, en mm (Y machine)."""
        canvas = self.canvas
        x1, y1 = canvas.scene_to_mm(p1_scene)
        x2, y2 = canvas.scene_to_mm(p2_scene)
        cx, cy = canvas.scene_to_mm(cursor_scene)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return 0.0
        # Normale unitaire à gauche de p1→p2 : (-dy, dx) / length
        nx, ny = -dy / length, dx / length
        # Projection du vecteur p1→cursor sur la normale
        return (cx - x1) * nx + (cy - y1) * ny

    def preview_path_base_depth(self, p1_scene, p2_scene, depth_mm, ellipse=False):
        """Aperçu scène d'un rectangle défini par base + profondeur (le cadre aussi pour une ellipse)."""
        canvas = self.canvas
        x1, y1 = canvas.scene_to_mm(p1_scene)
        x2, y2 = canvas.scene_to_mm(p2_scene)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return QPainterPath()
        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux  # normale
        # 4 coins en mm monde
        corners = ((x1, y1), (x2, y2), (x2 + nx * depth_mm, y2 + ny * depth_mm),
                   (x1 + nx * depth_mm, y1 + ny * depth_mm))
        s0, s1, s2, s3 = (canvas.mm_to_scene(*c) for c in corners)
        path = QPainterPath()
        path.moveTo(s0)
        path.lineTo(s1)
        path.lineTo(s2)
        path.lineTo(s3)
        path.closeSubpath()
        return path

    def create_rect_from_base(self, p1_scene, p2_scene, depth_mm, ellipse=False):
        """Rectangle/ellipse : largeur = |p1p2|, hauteur = |depth|, orientation = angle p1→p2."""
        canvas = self.canvas
        x1, y1 = canvas.scene_to_mm(p1_scene)
        x2, y2 = canvas.scene_to_mm(p2_scene)
        dx, dy = x2 - x1, y2 - y1
        width = math.hypot(dx, dy)
        # Refuse les « rectangles plats » (souvent un 3e clic trop proche de la base)
        if width < 0.05 or abs(depth_mm) < 0.2:
            return None
        layer_id = self.default_layer_id()
        if not layer_id:
            return None
        angle = math.degrees(math.atan2(dy, dx))
        # Toujours ancrer l'origine (x_mm,y_mm) sur le 1er point p1. Si la profondeur est de l'autre côté
        # de la normale, on inverse le sens local via mirror_v pour que le corps du rectangle suive
        # l'aperçu tout en gardant p1 comme point d'ancrage (1er point).
        return ShapeObject(shape_type="Ellipse" if ellipse else "Rectangle", width_mm=width,
                           height_mm=abs(depth_mm), layer_id=layer_id, x_mm=x1, y_mm=y1, rotation_deg=angle,
                           mirror_v=depth_mm < 0)
