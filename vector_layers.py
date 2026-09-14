# -*- coding: utf-8 -*-
"""
vector_layers.py — Extension "Calques + Texte/Formes" pour Laser Studio Pro
============================================================================

Ce module est 100% additif : il ne modifie ni ne remplace le pipeline
existant (image tramée + découpe SVG). Il ajoute :

  1) LaserLayer / LayerManager / LayerManagerWidget
     -> Calques façon LightBurn : couleur, mode (Découpe / Gravure Remplie /
        Marquage), puissance, vitesse, passes, activé/désactivé.

  2) VectorObject (TextObject / ShapeObject) + VectorCanvasView
     -> Un éditeur vectoriel (QGraphicsScene en mm) où l'on place du texte
        (n'importe quelle police installée, miroir H/V, orientation
        horizontale/verticale) et des formes (rectangle, ellipse, ligne,
        polygone régulier), chaque objet étant rattaché à un calque.

  3) extract_vector_layer_data() / build_vector_layers_gcode()
     -> Conversion des objets vectoriels en données géométriques "pures"
        (listes de points, thread-safe) puis en G-Code, calque par calque,
        avec la même convention de coordonnées que le reste de l'appli
        (Y inversé, origine bas-gauche ou centre).

Toute la géométrie lourde (aplatissement des courbes de Bézier, remplissage
par balayage de lignes) est faite une seule fois lors de la génération du
job, dans le thread de calcul existant (AdvancedGCodeWorker) : aucune perte
de fluidité de l'interface.
"""

import math
import re
import uuid

from svg.path import parse_path, Move, Line, Close, CubicBezier, QuadraticBezier, Arc

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QFontMetricsF, QPainterPath, QPen,
                          QBrush, QTransform, QPolygonF, QPainter, QKeySequence)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPathItem, QGraphicsItem,
    QGraphicsRectItem, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QTableWidget, QHeaderView,
    QColorDialog, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QDialog,
    QDialogButtonBox, QLineEdit, QFontComboBox, QRadioButton, QButtonGroup,
    QMessageBox, QAbstractItemView, QToolButton, QMenu, QInputDialog
)


# ============================================================================
# 1) CALQUES (LAYERS)
# ============================================================================

LAYER_MODES = ["Découpe", "Gravure Remplie", "Marquage (Contour)"]

DEFAULT_LAYER_COLORS = [
    "#ff3b30", "#34c759", "#0a84ff", "#ff9f0a",
    "#bf5af2", "#64d2ff", "#ffd60a", "#ff375f",
]


class LaserLayer:
    """Un calque = une couleur + un jeu de réglages laser, comme dans LightBurn."""

    def __init__(self, name="Calque", color="#ff3b30", mode="Découpe",
                 power=80.0, speed=300, passes=1, line_interval=0.10,
                 enabled=True, layer_id=None):
        self.id = layer_id or uuid.uuid4().hex[:8]
        self.name = name
        self.color = color
        self.mode = mode                    # cf. LAYER_MODES
        self.power = float(power)           # %
        self.speed = int(speed)             # mm/min
        self.passes = int(passes)
        self.line_interval = float(line_interval)  # mm (pas du remplissage)
        self.enabled = bool(enabled)

    def to_dict(self):
        return dict(self.__dict__)

    @staticmethod
    def from_dict(d):
        layer = LaserLayer()
        layer.__dict__.update(d)
        return layer


class LayerManager:
    """Conteneur ordonné de LaserLayer, avec un signal Qt-free (callbacks simples)."""

    def __init__(self):
        self.layers = [
            LaserLayer(name="Découpe", color=DEFAULT_LAYER_COLORS[0],
                       mode="Découpe", power=90, speed=250, passes=2),
            LaserLayer(name="Gravure Texte", color=DEFAULT_LAYER_COLORS[2],
                       mode="Gravure Remplie", power=35, speed=2000, passes=1),
        ]

    def add_layer(self):
        idx = len(self.layers)
        color = DEFAULT_LAYER_COLORS[idx % len(DEFAULT_LAYER_COLORS)]
        layer = LaserLayer(name=f"Calque {idx + 1}", color=color)
        self.layers.append(layer)
        return layer

    def remove_layer(self, layer_id):
        self.layers = [l for l in self.layers if l.id != layer_id]

    def get(self, layer_id):
        for l in self.layers:
            if l.id == layer_id:
                return l
        return None

    def to_list(self):
        return [l.to_dict() for l in self.layers]

    def load_list(self, data):
        self.layers = [LaserLayer.from_dict(d) for d in data] if data else []


class LayerManagerWidget(QWidget):
    """Table façon LightBurn : Couleur | Nom | Mode | Puissance | Vitesse | Passes | Actif"""

    layers_changed = pyqtSignal()

    COLUMNS = ["Couleur", "Nom", "Mode", "Puissance (%)", "Vitesse (mm/min)",
               "Passes", "Pas remplissage (mm)", "Actif"]

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.mgr = layer_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Calque")
        btn_add.clicked.connect(self.on_add)
        btn_del = QPushButton("Supprimer Calque")
        btn_del.clicked.connect(self.on_remove)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.refresh()

    # -- construction des lignes -------------------------------------------------
    def refresh(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for layer in self.mgr.layers:
            self._add_row(layer)
        self.table.blockSignals(False)

    def _add_row(self, layer: LaserLayer):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Couleur (bouton pastille)
        btn_color = QToolButton()
        btn_color.setStyleSheet(f"background-color:{layer.color}; border:1px solid #222;")
        btn_color.setFixedSize(28, 22)
        btn_color.clicked.connect(lambda _, l=layer, b=btn_color: self._pick_color(l, b))
        self.table.setCellWidget(row, 0, btn_color)

        name_edit = QLineEdit(layer.name)
        name_edit.textChanged.connect(lambda t, l=layer: self._set(l, "name", t))
        self.table.setCellWidget(row, 1, name_edit)

        combo_mode = QComboBox()
        combo_mode.addItems(LAYER_MODES)
        combo_mode.setCurrentText(layer.mode)
        combo_mode.currentTextChanged.connect(lambda t, l=layer: self._set(l, "mode", t))
        self.table.setCellWidget(row, 2, combo_mode)

        spin_power = QDoubleSpinBox(); spin_power.setRange(0, 100); spin_power.setValue(layer.power)
        spin_power.valueChanged.connect(lambda v, l=layer: self._set(l, "power", v))
        self.table.setCellWidget(row, 3, spin_power)

        spin_speed = QSpinBox(); spin_speed.setRange(1, 20000); spin_speed.setValue(layer.speed)
        spin_speed.valueChanged.connect(lambda v, l=layer: self._set(l, "speed", v))
        self.table.setCellWidget(row, 4, spin_speed)

        spin_passes = QSpinBox(); spin_passes.setRange(1, 50); spin_passes.setValue(layer.passes)
        spin_passes.valueChanged.connect(lambda v, l=layer: self._set(l, "passes", v))
        self.table.setCellWidget(row, 5, spin_passes)

        spin_fill = QDoubleSpinBox(); spin_fill.setRange(0.02, 5.0); spin_fill.setSingleStep(0.02)
        spin_fill.setDecimals(2); spin_fill.setValue(layer.line_interval)
        spin_fill.valueChanged.connect(lambda v, l=layer: self._set(l, "line_interval", v))
        self.table.setCellWidget(row, 6, spin_fill)

        chk_enabled = QCheckBox(); chk_enabled.setChecked(layer.enabled)
        chk_enabled.stateChanged.connect(lambda v, l=layer: self._set(l, "enabled", bool(v)))
        self.table.setCellWidget(row, 7, chk_enabled)

        self.table.setRowHeight(row, 30)
        self.table.setProperty(f"row_layer_{row}", layer.id)

    def _pick_color(self, layer, button):
        color = QColorDialog.getColor(QColor(layer.color), self, "Couleur du calque")
        if color.isValid():
            layer.color = color.name()
            button.setStyleSheet(f"background-color:{layer.color}; border:1px solid #222;")
            self.layers_changed.emit()

    def _set(self, layer, attr, value):
        setattr(layer, attr, value)
        self.layers_changed.emit()

    def on_add(self):
        self.mgr.add_layer()
        self.refresh()
        self.layers_changed.emit()

    def on_remove(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.mgr.layers):
            return
        layer = self.mgr.layers[row]
        self.mgr.remove_layer(layer.id)
        self.refresh()
        self.layers_changed.emit()

    def current_layer_id(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.mgr.layers):
            return self.mgr.layers[row].id
        return self.mgr.layers[0].id if self.mgr.layers else None


# ============================================================================
# 2) OBJETS VECTORIELS (TEXTE / FORMES)
# ============================================================================

class VectorObject:
    """Classe de base : position (mm), rotation, miroirs, calque associé.
    Le repère utilisé est identique à celui du SVG existant dans l'appli :
    origine en haut-gauche de la zone de travail, Y croissant vers le bas.
    """
    kind = "generic"

    def __init__(self, x_mm=10.0, y_mm=10.0, rotation_deg=0.0,
                 mirror_h=False, mirror_v=False, layer_id=None, obj_id=None):
        self.id = obj_id or uuid.uuid4().hex[:8]
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.rotation_deg = rotation_deg
        self.mirror_h = mirror_h
        self.mirror_v = mirror_v
        self.layer_id = layer_id

    def local_path(self) -> QPainterPath:
        """Doit renvoyer un QPainterPath en mm, centré sur l'origine locale (0,0)."""
        raise NotImplementedError

    def world_transform(self) -> QTransform:
        """Repère 'monde' = origine en BAS-GAUCHE de la zone de travail, Y croissant
        vers le HAUT (comme le repère machine / GRBL), directement exploitable pour
        le G-Code sans inversion supplémentaire. Les tracés locaux (police de
        caractères, formes) sont eux nativement en Y descendant (convention Qt) :
        on applique donc par défaut une inversion verticale (sy=-1) pour les faire
        correspondre au repère monde Y-haut, ce qui replace aussi correctement
        l'ancre du texte (le haut du texte reste 'en haut'). Cocher 'Miroir
        Vertical' annule cette inversion, produisant un miroir par rapport au
        rendu normal, comme attendu.
        """
        t = QTransform()
        t.translate(self.x_mm, self.y_mm)
        t.rotate(self.rotation_deg)
        sx = -1.0 if self.mirror_h else 1.0
        sy = 1.0 if self.mirror_v else -1.0
        t.scale(sx, sy)
        return t

    def world_path(self) -> QPainterPath:
        return self.world_transform().map(self.local_path())

    def to_dict(self):
        d = dict(self.__dict__)
        d["kind"] = self.kind
        return d

    @staticmethod
    def from_dict(d):
        kind = d.get("kind")
        if kind == "text":
            obj = TextObject.__new__(TextObject)
            obj.__dict__.update({k: v for k, v in d.items() if k != "kind"})
        elif kind == "shape":
            obj = ShapeObject.__new__(ShapeObject)
            obj.__dict__.update({k: v for k, v in d.items() if k != "kind"})
        elif kind == "svg_path":
            obj = SvgPathObject.from_dict(d)
        else:
            raise ValueError(f"Type d'objet vectoriel inconnu : {kind}")
        return obj


class TextObject(VectorObject):
    """Texte vectoriel basé sur une vraie police système (contours réels, pas de
    police 5x7). Prend en charge miroir H/V et orientation horizontale/verticale."""
    kind = "text"
    _REF_PT = 200.0  # taille de référence (grande) pour un rendu de courbes précis

    def __init__(self, text="TEXTE", font_family="Arial", size_mm=10.0,
                 bold=False, italic=False, vertical=False,
                 letter_spacing_mm=0.0, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.font_family = font_family
        self.size_mm = size_mm
        self.bold = bold
        self.italic = italic
        self.vertical = vertical
        self.letter_spacing_mm = letter_spacing_mm

    def _font(self):
        font = QFont(self.font_family)
        font.setPointSizeF(self._REF_PT)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        return font

    def local_path(self) -> QPainterPath:
        font = self._font()
        metrics = QFontMetricsF(font)
        ref_height = metrics.ascent() if metrics.ascent() > 0 else self._REF_PT
        scale = self.size_mm / ref_height

        raw_path = QPainterPath()
        if not self.vertical:
            raw_path.addText(0, 0, font, self.text)
            if self.letter_spacing_mm:
                # Espacement additionnel : reconstruit lettre par lettre
                raw_path = QPainterPath()
                cursor_x = 0.0
                extra_advance = self.letter_spacing_mm / max(scale, 1e-6)
                for ch in self.text:
                    p = QPainterPath()
                    p.addText(cursor_x, 0, font, ch)
                    raw_path.addPath(p)
                    cursor_x += metrics.horizontalAdvance(ch) + extra_advance
        else:
            # Orientation verticale : une lettre sous l'autre
            line_height = metrics.ascent() + metrics.descent()
            extra = self.letter_spacing_mm / max(scale, 1e-6)
            cursor_y = 0.0
            for ch in self.text:
                if ch == " ":
                    cursor_y += line_height + extra
                    continue
                p = QPainterPath()
                p.addText(0, cursor_y, font, ch)
                raw_path.addPath(p)
                cursor_y += line_height + extra

        # Réancre l'origine locale (0,0) sur le coin BAS-GAUCHE du texte
        # (cohérent avec les formes et le repère machine bas-gauche/Y-haut) :
        # X/Y désignent le coin bas-gauche du bloc de texte, pas son centre.
        bbox = raw_path.boundingRect()
        reanchor = QTransform()
        reanchor.translate(-bbox.left(), -bbox.bottom())
        path = reanchor.map(raw_path)
        return QTransform().scale(scale, scale).map(path)


class ShapeObject(VectorObject):
    """Formes géométriques simples : rectangle, ellipse, ligne, polygone régulier."""
    kind = "shape"
    SHAPE_TYPES = ["Rectangle", "Ellipse", "Ligne", "Polygone Régulier"]

    def __init__(self, shape_type="Rectangle", width_mm=20.0, height_mm=15.0,
                 sides=6, **kwargs):
        super().__init__(**kwargs)
        self.shape_type = shape_type
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.sides = sides  # utilisé pour le polygone régulier

    def local_path(self) -> QPainterPath:
        path = QPainterPath()
        w, h = self.width_mm, self.height_mm
        if self.shape_type == "Rectangle":
            path.addRect(0, 0, w, h)
        elif self.shape_type == "Ellipse":
            path.addEllipse(0, 0, w, h)
        elif self.shape_type == "Ligne":
            path.moveTo(0, 0)
            path.lineTo(w, 0)
        elif self.shape_type == "Polygone Régulier":
            n = max(3, self.sides)
            r = min(w, h) / 2.0
            poly = QPolygonF()
            for i in range(n):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                poly.append(QPointF(r * math.cos(angle), r * math.sin(angle)))
            path.addPolygon(poly)
            path.closeSubpath()

        # Réancre l'origine locale (0,0) sur le coin BAS-GAUCHE du bounding
        # box de la forme (cohérent avec le repère machine bas-gauche/Y-haut).
        # X/Y désignent ainsi le COIN de la forme, pas son centre — c'est ce
        # qui manquait : avec un centrage, taper X=10 plaçait le CENTRE à
        # 10mm, donc le bord gauche réel à 10 - largeur/2, ce qui donnait
        # l'impression que la position tapée n'était jamais respectée.
        bbox = path.boundingRect()
        reanchor = QTransform()
        reanchor.translate(-bbox.left(), -bbox.bottom())
        return reanchor.map(path)


class SvgPathObject(VectorObject):
    """Objet issu d'un import SVG « dégroupé » : un tracé FIXE (contrairement
    au texte ou aux formes simples, il n'est pas régénéré à partir de
    paramètres — c'est la géométrie exacte extraite du fichier SVG source).
    Redimensionnable via scale_x/scale_y (voir AssignLayerDialog)."""
    kind = "svg_path"

    def __init__(self, local_path_data=None, source_tag="", scale_x=1.0, scale_y=1.0, **kwargs):
        super().__init__(**kwargs)
        self._local_path_data = local_path_data if local_path_data is not None else QPainterPath()
        self.source_tag = source_tag  # ex: "path", "rect"... juste informatif
        self.scale_x = scale_x
        self.scale_y = scale_y

    def local_path(self) -> QPainterPath:
        sx = getattr(self, "scale_x", 1.0)
        sy = getattr(self, "scale_y", 1.0)
        if sx == 1.0 and sy == 1.0:
            return QPainterPath(self._local_path_data)
        t = QTransform()
        t.scale(sx, sy)
        return t.map(self._local_path_data)

    def to_dict(self):
        d = dict(self.__dict__)
        d["kind"] = self.kind
        # Le QPainterPath ne se sérialise pas tel quel : on le réduit en une
        # liste de polygones (mêmes points, robuste pour un save/load JSON).
        polys = self._local_path_data.toSubpathPolygons(QTransform())
        d["_local_polys"] = [[(p.x(), p.y()) for p in poly] for poly in polys]
        d.pop("_local_path_data", None)
        return d

    @staticmethod
    def from_dict(d):
        obj = SvgPathObject.__new__(SvgPathObject)
        data = dict(d)
        polys = data.pop("_local_polys", [])
        data.pop("kind", None)
        path = QPainterPath()
        for poly in polys:
            if not poly:
                continue
            path.moveTo(poly[0][0], poly[0][1])
            for (x, y) in poly[1:]:
                path.lineTo(x, y)
        obj.__dict__.update(data)
        obj._local_path_data = path
        obj.scale_x = data.get("scale_x", 1.0)
        obj.scale_y = data.get("scale_y", 1.0)
        return obj


def _svg_path_element_to_subpaths(d):
    """Convertit le 'd' d'un <path> SVG en une liste de QPainterPath
    INDÉPENDANTS, un par sous-tracé (une commande M/m démarre un nouveau
    sous-tracé). Nécessaire pour pouvoir « dégrouper » un <path> combiné —
    très courant pour un texte vectorisé ou un logo exporté depuis
    Illustrator/Inkscape, où plusieurs formes visuellement séparées sont
    en réalité un seul élément <path> avec plusieurs M/Z internes.

    Les courbes de Bézier sont converties EXACTEMENT (cubicTo/quadTo, pas
    d'échantillonnage) ; seuls les arcs (rares en pratique) sont échantillonnés
    faute d'équivalent direct dans QPainterPath."""
    parsed = parse_path(d)
    paths = []
    current = None
    for seg in parsed:
        if isinstance(seg, Move):
            if current is not None and current.elementCount() > 0:
                paths.append(current)
            current = QPainterPath()
            current.moveTo(seg.end.real, seg.end.imag)
            continue
        if current is None:
            current = QPainterPath()
            current.moveTo(seg.start.real, seg.start.imag)
        if isinstance(seg, (Line, Close)):
            current.lineTo(seg.end.real, seg.end.imag)
        elif isinstance(seg, CubicBezier):
            current.cubicTo(seg.control1.real, seg.control1.imag,
                             seg.control2.real, seg.control2.imag,
                             seg.end.real, seg.end.imag)
        elif isinstance(seg, QuadraticBezier):
            current.quadTo(seg.control.real, seg.control.imag,
                            seg.end.real, seg.end.imag)
        elif isinstance(seg, Arc):
            try:
                length = seg.length()
            except Exception:
                length = 0
            n = max(4, int(length / 0.3)) if length else 8
            for i in range(1, n + 1):
                pt = seg.point(i / n)
                current.lineTo(pt.real, pt.imag)
    if current is not None and current.elementCount() > 0:
        paths.append(current)
    return paths


def extract_svg_objects(svg_path, layer_id, bed_h_mm):
    """Importe un fichier SVG comme objets vectoriels INDÉPENDANTS — un objet
    par tracé/forme du fichier (« dégroupé ») — assignables individuellement à
    des calques différents (ex : certaines parties en découpe, d'autres en
    gravure remplie), avec aperçu visuel immédiat dans l'éditeur vectoriel.

    Convention : 1 unité SVG = 1 mm (même convention que l'ancien mode de
    découpe SVG global de cette application). L'origine du SVG (0,0, coin
    haut-gauche) est alignée sur le coin haut-gauche de la zone de travail
    machine ; les positions relatives entre les tracés sont conservées (le
    dessin reste visuellement intact juste après import).
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(svg_path)
    root = tree.getroot()

    def local_tag(elem):
        return elem.tag.split('}')[-1]

    raw = []  # (QPainterPath en coordonnées SVG brutes Y-bas, tag)

    for elem in root.iter():
        tag = local_tag(elem)
        try:
            if tag == 'path':
                d = elem.attrib.get('d')
                if not d:
                    continue
                # Un seul <path> peut contenir plusieurs sous-tracés (M/m
                # multiples) — on les sépare pour permettre de les
                # sélectionner/assigner à des calques indépendamment
                # (« dégroupement »).
                for qp in _svg_path_element_to_subpaths(d):
                    raw.append((qp, tag))
            elif tag == 'rect':
                x = float(elem.attrib.get('x', 0)); y = float(elem.attrib.get('y', 0))
                w = float(elem.attrib.get('width', 0)); h = float(elem.attrib.get('height', 0))
                if w > 0 and h > 0:
                    qp = QPainterPath()
                    qp.addRect(x, y, w, h)
                    raw.append((qp, tag))
            elif tag == 'circle':
                cx = float(elem.attrib.get('cx', 0)); cy = float(elem.attrib.get('cy', 0))
                r = float(elem.attrib.get('r', 0))
                if r > 0:
                    qp = QPainterPath()
                    qp.addEllipse(cx - r, cy - r, 2 * r, 2 * r)
                    raw.append((qp, tag))
            elif tag == 'ellipse':
                cx = float(elem.attrib.get('cx', 0)); cy = float(elem.attrib.get('cy', 0))
                rx = float(elem.attrib.get('rx', 0)); ry = float(elem.attrib.get('ry', 0))
                if rx > 0 and ry > 0:
                    qp = QPainterPath()
                    qp.addEllipse(cx - rx, cy - ry, 2 * rx, 2 * ry)
                    raw.append((qp, tag))
            elif tag in ('polygon', 'polyline'):
                pts_str = elem.attrib.get('points', '')
                coords = [float(v) for v in re.split(r'[\s,]+', pts_str.strip()) if v]
                if len(coords) >= 4:
                    poly = QPolygonF([QPointF(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)])
                    qp = QPainterPath()
                    qp.addPolygon(poly)
                    if tag == 'polygon':
                        qp.closeSubpath()
                    raw.append((qp, tag))
            elif tag == 'line':
                x1 = float(elem.attrib.get('x1', 0)); y1 = float(elem.attrib.get('y1', 0))
                x2 = float(elem.attrib.get('x2', 0)); y2 = float(elem.attrib.get('y2', 0))
                qp = QPainterPath()
                qp.moveTo(x1, y1)
                qp.lineTo(x2, y2)
                raw.append((qp, tag))
        except Exception:
            continue

    objects = []
    for qp, tag in raw:
        bbox = qp.boundingRect()
        if bbox.width() <= 0 and bbox.height() <= 0:
            continue
        reanchor = QTransform()
        reanchor.translate(-bbox.left(), -bbox.bottom())
        local = reanchor.map(qp)

        world_x = bbox.left()
        world_y = bed_h_mm - bbox.bottom()

        obj = SvgPathObject(local_path_data=local, source_tag=tag,
                             layer_id=layer_id, x_mm=world_x, y_mm=world_y)
        objects.append(obj)

    return objects


# ============================================================================
# 3) CANEVAS VECTORIEL (édition à la souris)
# ============================================================================

class VectorGraphicsItem(QGraphicsPathItem):
    """QGraphicsItem qui représente un VectorObject sur le canevas (échelle px/mm).

    Le repère "monde" (VectorObject.world_transform) est bas-gauche / Y-haut,
    utilisé tel quel pour le G-Code. La scène Qt, elle, reste nativement
    Y-descendant (aucun flip au niveau de la QGraphicsView : fitInView() peut
    silencieusement annuler un flip posé sur la vue, ce qui cassait
    l'affichage). La conversion "monde -> écran" est donc calculée ici,
    objet par objet, directement dans la matrice de chaque item.
    """

    def __init__(self, obj: VectorObject, layer_manager: LayerManager, canvas: "VectorCanvasView"):
        super().__init__()
        self.obj = obj
        self.layer_manager = layer_manager
        self.canvas = canvas
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.double_click_callback = None  # défini par VectorCanvasView.add_object
        self.refresh()

    def mouseDoubleClickEvent(self, event):
        if self.double_click_callback:
            self.double_click_callback()
        super().mouseDoubleClickEvent(event)

    def refresh(self):
        """Recalcule la forme affichée (mm -> px, repère écran) à partir du VectorObject."""
        s = self.canvas.px_per_mm
        work_h_px = self.canvas.work_h_mm * s

        local_path_px = QTransform().scale(s, s).map(self.obj.local_path())
        self.prepareGeometryChange()
        self.setPath(local_path_px)

        sx = -1.0 if self.obj.mirror_h else 1.0
        sy = 1.0 if self.obj.mirror_v else -1.0

        # Construit, dans une seule matrice, la transformation monde (position,
        # rotation, miroir) PUIS le passage bas-gauche/Y-haut -> écran Qt
        # Y-descendant. Avec QTransform, des appels .translate()/.rotate()/
        # .scale() enchaînés s'appliquent à un point dans l'ordre INVERSE des
        # appels : ci-dessous, un point est donc d'abord mis à l'échelle
        # (miroir), puis pivoté, puis positionné (repère monde), puis
        # seulement là le flip écran + décalage de hauteur sont appliqués.
        t = QTransform()
        t.translate(0, work_h_px)         # 5) décale pour repère écran Qt
        t.scale(1, -1)                    # 4) inverse Y : monde Y-haut -> écran Y-bas
        t.translate(self.obj.x_mm * s, self.obj.y_mm * s)  # 3) position (repère monde)
        t.rotate(self.obj.rotation_deg)   # 2) rotation
        t.scale(sx, sy)                   # 1) miroir éventuel
        self.setTransform(t)
        self.setPos(0, 0)

        layer = self.layer_manager.get(self.obj.layer_id)
        color = QColor(layer.color) if layer else QColor("#dddddd")
        pen = QPen(color, 1.4)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged:
            pass
        return super().itemChange(change, value)

    def sync_position_from_scene(self):
        """À appeler après un déplacement souris : remet x_mm/y_mm à jour à
        partir de la position écran (en tenant compte du flip Y bas-gauche)."""
        pos = self.scenePos()
        s = self.canvas.px_per_mm
        work_h_px = self.canvas.work_h_mm * s
        self.obj.x_mm = pos.x() / s
        self.obj.y_mm = (work_h_px - pos.y()) / s


class VectorCanvasView(QGraphicsView):
    """Vue d'édition : zone de travail en mm, objets déplaçables à la souris,
    coloration selon le calque. Indépendante des vues image (aucun impact
    sur les performances du tramage)."""

    selection_changed = pyqtSignal(object)  # VectorObject ou None
    object_moved = pyqtSignal(object)       # VectorObject déplacé à la souris
    edit_requested = pyqtSignal(object)     # double-clic sur un objet

    def __init__(self, layer_manager: LayerManager, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.objects = []  # list[VectorObject]
        self.px_per_mm = 4.0
        self.grid_items = []

        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setBackgroundBrush(QColor("#1c1c1c"))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # Repère "machine" : origine en bas-gauche, Y croissant vers le haut.
        # (Le flip est calculé objet par objet et pour la grille — voir
        # VectorGraphicsItem.refresh et _draw_grid — plutôt qu'au niveau de la
        # vue : un flip posé sur la QGraphicsView pouvait être silencieusement
        # annulé par fitInView(), ce qui cassait tout l'alignement.)
        self._pan_last_pos = None
        self._undo_stack = []
        self._max_undo = 30

        self.work_rect_item = None
        self.set_work_area(100.0, 100.0)

        self.scene_obj.selectionChanged.connect(self._on_selection_changed)

    # -- zone de travail ----------------------------------------------------
    def set_work_area(self, w_mm, h_mm):
        self.work_w_mm, self.work_h_mm = w_mm, h_mm
        if self.work_rect_item:
            self.scene_obj.removeItem(self.work_rect_item)
        for item in self.grid_items:
            self.scene_obj.removeItem(item)
        self.grid_items = []

        s = self.px_per_mm
        rect = QRectF(0, 0, w_mm * s, h_mm * s)
        self.work_rect_item = QGraphicsRectItem(rect)
        pen = QPen(QColor("#666666"), 1)
        pen.setCosmetic(True)
        self.work_rect_item.setPen(pen)
        self.work_rect_item.setZValue(-100)
        self.scene_obj.addItem(self.work_rect_item)

        self._draw_grid(w_mm, h_mm)

        self.scene_obj.setSceneRect(rect.adjusted(-50, -50, 50, 50))
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_grid(self, w_mm, h_mm):
        """Grille en mm avec repères chiffrés le long des bords bas et gauche,
        pour se repérer facilement (origine = coin bas-gauche = 0,0). Les
        coordonnées écran sont calculées directement en Y inversé (bas-gauche
        -> Y-descendant Qt) : aucun flip de vue n'est utilisé (voir __init__),
        donc pas besoin de contre-flip sur les étiquettes non plus.
        """
        s = self.px_per_mm
        work_h_px = h_mm * s
        span = max(w_mm, h_mm)
        # Paliers plus fins qu'avant (l'ancien "50mm partout au-delà de 200mm"
        # était trop grossier pour se repérer précisément sur une zone de
        # travail courante de 200-400mm).
        if span <= 50:
            step = 5
        elif span <= 150:
            step = 10
        elif span <= 400:
            step = 20
        elif span <= 1000:
            step = 50
        else:
            step = 100
        minor_step = step / 4.0

        minor_pen = QPen(QColor("#262626"), 0)
        minor_pen.setCosmetic(True)

        grid_pen = QPen(QColor("#333333"), 0)
        grid_pen.setCosmetic(True)

        # Lignes mineures (sans étiquette) pour un repérage plus précis entre
        # deux graduations principales.
        xm = minor_step
        while xm < w_mm - 1e-6:
            line = self.scene_obj.addLine(xm * s, 0, xm * s, work_h_px, minor_pen)
            line.setZValue(-95)
            self.grid_items.append(line)
            xm += minor_step
        ym = minor_step
        while ym < h_mm - 1e-6:
            screen_y = work_h_px - ym * s
            line = self.scene_obj.addLine(0, screen_y, w_mm * s, screen_y, minor_pen)
            line.setZValue(-95)
            self.grid_items.append(line)
            ym += minor_step

        x = 0.0
        while x <= w_mm + 1e-6:
            line = self.scene_obj.addLine(x * s, 0, x * s, work_h_px, grid_pen)
            line.setZValue(-90)
            self.grid_items.append(line)
            label = self.scene_obj.addSimpleText(f"{x:g}")
            label.setBrush(QColor("#999999"))
            label.setPos(x * s + 2, work_h_px - 16)
            label.setZValue(-80)
            self.grid_items.append(label)
            x += step

        y = 0.0
        while y <= h_mm + 1e-6:
            screen_y = work_h_px - y * s
            line = self.scene_obj.addLine(0, screen_y, w_mm * s, screen_y, grid_pen)
            line.setZValue(-90)
            self.grid_items.append(line)
            label = self.scene_obj.addSimpleText(f"{y:g}")
            label.setBrush(QColor("#999999"))
            label.setPos(2, screen_y - 16)
            label.setZValue(-80)
            self.grid_items.append(label)
            y += step

        origin_label = self.scene_obj.addSimpleText("0,0 (origine)")
        origin_label.setBrush(QColor("#ff8844"))
        origin_label.setPos(2, work_h_px - 32)
        origin_label.setZValue(-80)
        self.grid_items.append(origin_label)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            item_at = self.itemAt(event.pos())
            if isinstance(item_at, VectorGraphicsItem):
                # Sauvegarde avant un déplacement à la souris, pour pouvoir
                # l'annuler avec Ctrl+Z même si aucun autre bouton n'est utilisé.
                self.push_undo_snapshot()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_last_pos is not None and (event.buttons() & Qt.MouseButton.MiddleButton):
            new_pos = event.position().toPoint()
            delta = new_pos - self._pan_last_pos
            self._pan_last_pos = new_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    # -- gestion des objets ---------------------------------------------------
    def add_object(self, obj: VectorObject):
        self.objects.append(obj)
        item = VectorGraphicsItem(obj, self.layer_manager, self)
        item.double_click_callback = lambda o=obj: self.edit_requested.emit(o)
        self.scene_obj.addItem(item)
        return item

    def remove_selected(self):
        self.push_undo_snapshot()
        for item in list(self.scene_obj.selectedItems()):
            if isinstance(item, VectorGraphicsItem):
                self.objects.remove(item.obj)
                self.scene_obj.removeItem(item)

    def duplicate_selected(self):
        self.push_undo_snapshot()
        new_items = []
        for item in list(self.scene_obj.selectedItems()):
            if isinstance(item, VectorGraphicsItem):
                clone = VectorObject.from_dict(item.obj.to_dict())
                clone.id = uuid.uuid4().hex[:8]
                clone.x_mm += 5
                clone.y_mm += 5
                new_items.append(self.add_object(clone))
        return new_items

    def refresh_all(self):
        for item in self.scene_obj.items():
            if isinstance(item, VectorGraphicsItem):
                item.refresh()

    def selected_object(self):
        for item in self.scene_obj.selectedItems():
            if isinstance(item, VectorGraphicsItem):
                return item, item.obj
        return None, None

    def _on_selection_changed(self):
        _, obj = self.selected_object()
        self.selection_changed.emit(obj)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
        for item in self.scene_obj.selectedItems():
            if isinstance(item, VectorGraphicsItem):
                item.sync_position_from_scene()
                self.object_moved.emit(item.obj)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.SelectAll):
            for item in self.scene_obj.items():
                if isinstance(item, VectorGraphicsItem):
                    item.setSelected(True)
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selected()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_clipboard()
            event.accept()
            return
        if event.key() == Qt.Key.Key_D and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.duplicate_selected()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.remove_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def copy_selected(self):
        """Ctrl+C : copie les objets sélectionnés dans un presse-papiers
        interne (propre à l'éditeur, pas le presse-papiers système)."""
        selected = [it.obj for it in self.scene_obj.selectedItems() if isinstance(it, VectorGraphicsItem)]
        if selected:
            self._clipboard = [o.to_dict() for o in selected]

    def paste_clipboard(self):
        """Ctrl+V : colle les objets copiés, légèrement décalés pour rester
        visibles distinctement de l'original."""
        if not getattr(self, "_clipboard", None):
            return
        self.push_undo_snapshot()
        for item in list(self.scene_obj.selectedItems()):
            item.setSelected(False)
        for d in self._clipboard:
            try:
                clone = VectorObject.from_dict(d)
            except Exception:
                continue
            clone.id = uuid.uuid4().hex[:8]
            clone.x_mm += 5
            clone.y_mm += 5
            new_item = self.add_object(clone)
            new_item.setSelected(True)

    def push_undo_snapshot(self):
        """À appeler AVANT toute action qui modifie les objets (ajout,
        suppression, déplacement, redimensionnement...), pour pouvoir revenir
        en arrière avec Ctrl+Z ou le bouton Annuler."""
        try:
            snapshot = [o.to_dict() for o in self.objects]
        except Exception:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

    def undo(self):
        if not self._undo_stack:
            return
        snapshot = self._undo_stack.pop()
        for item in list(self.scene_obj.items()):
            if isinstance(item, VectorGraphicsItem):
                self.scene_obj.removeItem(item)
        self.objects = []
        for d in snapshot:
            try:
                self.add_object(VectorObject.from_dict(d))
            except Exception:
                continue

    def contextMenuEvent(self, event):
        """Clic droit : assigner un calque (découpe/gravure) ou redimensionner
        toute la sélection courante en une seule action — fonctionne aussi
        bien sur un seul objet que sur plusieurs (Ctrl+A ou rubber-band)."""
        selected = [it for it in self.scene_obj.selectedItems() if isinstance(it, VectorGraphicsItem)]
        if not selected:
            item_at = self.itemAt(event.pos())
            if isinstance(item_at, VectorGraphicsItem):
                item_at.setSelected(True)
                selected = [item_at]
        if not selected:
            return

        menu = QMenu(self)
        n = len(selected)
        label_suffix = f" ({n} objets)" if n > 1 else ""

        layer_menu = menu.addMenu(f"Assigner au calque{label_suffix}")
        for layer in self.layer_manager.layers:
            action = layer_menu.addAction(f"{layer.name}  [{layer.mode}]")
            action.triggered.connect(lambda checked=False, lid=layer.id, items=selected: self._bulk_assign_layer(items, lid))

        resize_action = menu.addAction(f"Redimensionner{label_suffix}…")
        resize_action.triggered.connect(lambda: self._bulk_resize(selected))

        menu.addSeparator()
        rotate_action = menu.addAction("↻ Pivoter 90°")
        rotate_action.triggered.connect(lambda: self._bulk_rotate(selected))
        dup_action = menu.addAction("Dupliquer")
        dup_action.triggered.connect(self.duplicate_selected)
        del_action = menu.addAction("Supprimer")
        del_action.triggered.connect(self.remove_selected)

        menu.exec(event.globalPos())

    def _bulk_assign_layer(self, items, layer_id):
        self.push_undo_snapshot()
        for it in items:
            it.obj.layer_id = layer_id
            it.refresh()

    def _bulk_resize(self, items):
        """Redimensionne toute la sélection COMME UN GROUPE : les proportions
        et positions relatives entre les objets sont conservées (comme un
        redimensionnement de groupe dans un éditeur vectoriel classique),
        en millimètres plutôt qu'en pourcentage abstrait."""
        boxes = [it.obj.world_path().boundingRect() for it in items]
        x_min = min(b.left() for b in boxes)
        x_max = max(b.right() for b in boxes)
        y_min = min(b.top() for b in boxes)
        y_max = max(b.bottom() for b in boxes)
        current_w = max(x_max - x_min, 1e-6)
        current_h = max(y_max - y_min, 1e-6)

        dialog = QDialog(self)
        dialog.setWindowTitle("Redimensionner la sélection (groupe)")
        layout = QFormLayout(dialog)
        layout.addRow(QLabel(f"Taille actuelle du groupe : {current_w:.2f} x {current_h:.2f} mm"))

        chk_keep_ratio = QCheckBox("Conserver le ratio largeur/hauteur")
        chk_keep_ratio.setChecked(True)
        layout.addRow("", chk_keep_ratio)

        spin_w = QDoubleSpinBox(); spin_w.setRange(0.1, 5000.0); spin_w.setDecimals(2)
        spin_w.setValue(current_w); spin_w.setSuffix(" mm")
        spin_h = QDoubleSpinBox(); spin_h.setRange(0.1, 5000.0); spin_h.setDecimals(2)
        spin_h.setValue(current_h); spin_h.setSuffix(" mm")
        layout.addRow("Nouvelle largeur :", spin_w)
        layout.addRow("Nouvelle hauteur :", spin_h)

        ratio = current_w / current_h if current_h else 1.0
        state = {"updating": False}

        def on_w_changed(val):
            if state["updating"] or not chk_keep_ratio.isChecked():
                return
            state["updating"] = True
            spin_h.setValue(val / ratio if ratio else val)
            state["updating"] = False

        def on_h_changed(val):
            if state["updating"] or not chk_keep_ratio.isChecked():
                return
            state["updating"] = True
            spin_w.setValue(val * ratio)
            state["updating"] = False

        spin_w.valueChanged.connect(on_w_changed)
        spin_h.valueChanged.connect(on_h_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if not dialog.exec():
            return

        self.push_undo_snapshot()
        factor_x = spin_w.value() / current_w
        factor_y = spin_h.value() / current_h

        for it in items:
            obj = it.obj
            # Repositionne l'objet proportionnellement à l'intérieur du groupe
            # (mise à l'échelle autour du coin bas-gauche du groupe entier).
            obj.x_mm = x_min + (obj.x_mm - x_min) * factor_x
            obj.y_mm = y_min + (obj.y_mm - y_min) * factor_y
            if isinstance(obj, ShapeObject):
                obj.width_mm *= factor_x
                obj.height_mm *= factor_y
            elif isinstance(obj, TextObject):
                obj.size_mm *= factor_y
                obj.letter_spacing_mm *= factor_x
            elif isinstance(obj, SvgPathObject):
                obj.scale_x = getattr(obj, "scale_x", 1.0) * factor_x
                obj.scale_y = getattr(obj, "scale_y", 1.0) * factor_y
            it.refresh()

    def _bulk_rotate(self, items):
        self.push_undo_snapshot()
        for it in items:
            it.obj.rotation_deg = (it.obj.rotation_deg + 90.0) % 360.0
            it.refresh()

    def set_object_position(self, obj: VectorObject, x_mm, y_mm, rotation_deg=None):
        """Positionnement précis par saisie numérique (offset X/Y en mm depuis
        l'origine de la zone de travail), utilisé par le panneau de propriétés."""
        obj.x_mm = x_mm
        obj.y_mm = y_mm
        if rotation_deg is not None:
            obj.rotation_deg = rotation_deg
        for item in self.scene_obj.items():
            if isinstance(item, VectorGraphicsItem) and item.obj is obj:
                item.refresh()
                break

    # -- (dé)sérialisation ----------------------------------------------------
    def serialize_objects(self):
        return [o.to_dict() for o in self.objects]

    def load_objects(self, data):
        for item in list(self.scene_obj.items()):
            if isinstance(item, VectorGraphicsItem):
                self.scene_obj.removeItem(item)
        self.objects = []
        for d in (data or []):
            self.add_object(VectorObject.from_dict(d))


# ============================================================================
# 4) BOITES DE DIALOGUE : INSERTION DE TEXTE / FORME
# ============================================================================

class TextInsertDialog(QDialog):
    """Boîte de dialogue façon LightBurn pour insérer/éditer un objet texte."""

    def __init__(self, layer_manager: LayerManager, text_obj: TextObject = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Texte" if text_obj is None else "Modifier le texte")
        self.layer_manager = layer_manager
        self.editing = text_obj

        layout = QFormLayout(self)

        self.edit_text = QLineEdit(text_obj.text if text_obj else "TEXTE")
        layout.addRow("Texte :", self.edit_text)

        self.combo_font = QFontComboBox()
        if text_obj:
            self.combo_font.setCurrentFont(QFont(text_obj.font_family))
        layout.addRow("Police :", self.combo_font)

        style_row = QHBoxLayout()
        self.chk_bold = QCheckBox("Gras"); self.chk_bold.setChecked(bool(text_obj and text_obj.bold))
        self.chk_italic = QCheckBox("Italique"); self.chk_italic.setChecked(bool(text_obj and text_obj.italic))
        style_row.addWidget(self.chk_bold); style_row.addWidget(self.chk_italic)
        layout.addRow("Style :", style_row)

        self.spin_size = QDoubleSpinBox(); self.spin_size.setRange(1.0, 500.0)
        self.spin_size.setValue(text_obj.size_mm if text_obj else 10.0)
        self.spin_size.setSuffix(" mm")
        layout.addRow("Taille (hauteur) :", self.spin_size)

        self.spin_spacing = QDoubleSpinBox(); self.spin_spacing.setRange(-5.0, 50.0)
        self.spin_spacing.setValue(text_obj.letter_spacing_mm if text_obj else 0.0)
        self.spin_spacing.setSuffix(" mm")
        layout.addRow("Espacement lettres :", self.spin_spacing)

        orient_row = QHBoxLayout()
        self.rb_horizontal = QRadioButton("Horizontal")
        self.rb_vertical = QRadioButton("Vertical")
        (self.rb_vertical if (text_obj and text_obj.vertical) else self.rb_horizontal).setChecked(True)
        grp = QButtonGroup(self); grp.addButton(self.rb_horizontal); grp.addButton(self.rb_vertical)
        orient_row.addWidget(self.rb_horizontal); orient_row.addWidget(self.rb_vertical)
        layout.addRow("Orientation :", orient_row)

        mirror_row = QHBoxLayout()
        self.chk_mirror_h = QCheckBox("Miroir Horizontal")
        self.chk_mirror_h.setChecked(bool(text_obj and text_obj.mirror_h))
        self.chk_mirror_v = QCheckBox("Miroir Vertical")
        self.chk_mirror_v.setChecked(bool(text_obj and text_obj.mirror_v))
        mirror_row.addWidget(self.chk_mirror_h); mirror_row.addWidget(self.chk_mirror_v)
        layout.addRow("Miroir :", mirror_row)

        self.combo_layer = QComboBox()
        for l in self.layer_manager.layers:
            self.combo_layer.addItem(f"{l.name}  [{l.mode}]", l.id)
        if text_obj and text_obj.layer_id:
            idx = self.combo_layer.findData(text_obj.layer_id)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        layout.addRow("Calque :", self.combo_layer)

        pos_row = QHBoxLayout()
        self.spin_x = QDoubleSpinBox(); self.spin_x.setRange(-1000.0, 1000.0)
        self.spin_x.setDecimals(2); self.spin_x.setSuffix(" mm")
        self.spin_x.setValue(text_obj.x_mm if text_obj else 10.0)
        self.spin_y = QDoubleSpinBox(); self.spin_y.setRange(-1000.0, 1000.0)
        self.spin_y.setDecimals(2); self.spin_y.setSuffix(" mm")
        self.spin_y.setValue(text_obj.y_mm if text_obj else 10.0)
        pos_row.addWidget(QLabel("X :")); pos_row.addWidget(self.spin_x)
        pos_row.addWidget(QLabel("Y :")); pos_row.addWidget(self.spin_y)
        layout.addRow("Coin bas-gauche de l'objet à (mm) :", pos_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_object(self) -> TextObject:
        layer_id = self.combo_layer.currentData()
        if self.editing:
            obj = self.editing
        else:
            obj = TextObject(layer_id=layer_id, x_mm=10.0, y_mm=10.0)
        obj.text = self.edit_text.text() or "TEXTE"
        obj.font_family = self.combo_font.currentFont().family()
        obj.bold = self.chk_bold.isChecked()
        obj.italic = self.chk_italic.isChecked()
        obj.size_mm = self.spin_size.value()
        obj.letter_spacing_mm = self.spin_spacing.value()
        obj.vertical = self.rb_vertical.isChecked()
        obj.mirror_h = self.chk_mirror_h.isChecked()
        obj.mirror_v = self.chk_mirror_v.isChecked()
        obj.layer_id = layer_id
        obj.x_mm = self.spin_x.value()
        obj.y_mm = self.spin_y.value()
        return obj


class AssignLayerDialog(QDialog):
    """Boîte de dialogue pour un objet importé depuis un SVG : calque, et
    redimensionnement (largeur/hauteur en mm, avec conservation du ratio en
    option). Sa géométrie de base reste fixe — seuls son échelle, son calque,
    sa position et sa rotation sont modifiables (position/rotation via le
    panneau dédié de l'éditeur vectoriel)."""

    def __init__(self, layer_manager: LayerManager, svg_obj=None, current_layer_id=None,
                 title="Propriétés de l'élément SVG", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.svg_obj = svg_obj
        layout = QFormLayout(self)

        self.combo_layer = QComboBox()
        for l in layer_manager.layers:
            self.combo_layer.addItem(f"{l.name}  [{l.mode}]", l.id)
        lid = current_layer_id if current_layer_id is not None else (svg_obj.layer_id if svg_obj else None)
        if lid:
            idx = self.combo_layer.findData(lid)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        layout.addRow("Calque :", self.combo_layer)

        self.spin_w = None
        self.spin_h = None
        self._updating = False
        if svg_obj is not None:
            orig_bbox = svg_obj._local_path_data.boundingRect()
            self._orig_w = max(orig_bbox.width(), 1e-6)
            self._orig_h = max(orig_bbox.height(), 1e-6)
            cur_w = self._orig_w * getattr(svg_obj, "scale_x", 1.0)
            cur_h = self._orig_h * getattr(svg_obj, "scale_y", 1.0)
            self._ratio = cur_w / cur_h if cur_h > 0 else 1.0

            self.chk_keep_ratio = QCheckBox("Conserver le ratio largeur/hauteur")
            self.chk_keep_ratio.setChecked(True)
            layout.addRow("", self.chk_keep_ratio)

            self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(0.1, 5000.0); self.spin_w.setDecimals(2)
            self.spin_w.setValue(cur_w); self.spin_w.setSuffix(" mm")
            self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(0.1, 5000.0); self.spin_h.setDecimals(2)
            self.spin_h.setValue(cur_h); self.spin_h.setSuffix(" mm")
            self.spin_w.valueChanged.connect(self._on_w_changed)
            self.spin_h.valueChanged.connect(self._on_h_changed)
            layout.addRow("Largeur :", self.spin_w)
            layout.addRow("Hauteur :", self.spin_h)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_w_changed(self, val):
        if self._updating or not self.chk_keep_ratio.isChecked():
            return
        self._updating = True
        if self._ratio:
            self.spin_h.setValue(val / self._ratio)
        self._updating = False

    def _on_h_changed(self, val):
        if self._updating or not self.chk_keep_ratio.isChecked():
            return
        self._updating = True
        self.spin_w.setValue(val * self._ratio)
        self._updating = False

    def selected_layer_id(self):
        return self.combo_layer.currentData()

    def apply_to(self, svg_obj):
        """Applique le calque choisi et, si applicable, la nouvelle taille."""
        svg_obj.layer_id = self.selected_layer_id()
        if self.spin_w is not None:
            svg_obj.scale_x = self.spin_w.value() / self._orig_w
            svg_obj.scale_y = self.spin_h.value() / self._orig_h


class ShapeInsertDialog(QDialog):
    """Boîte de dialogue pour insérer OU modifier une forme géométrique."""

    def __init__(self, layer_manager: LayerManager, shape_obj: "ShapeObject" = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insérer une forme" if shape_obj is None else "Modifier la forme")
        self.layer_manager = layer_manager
        self.editing = shape_obj

        layout = QFormLayout(self)

        self.combo_type = QComboBox()
        self.combo_type.addItems(ShapeObject.SHAPE_TYPES)
        if shape_obj:
            self.combo_type.setCurrentText(shape_obj.shape_type)
        layout.addRow("Type :", self.combo_type)

        self.spin_w = QDoubleSpinBox(); self.spin_w.setRange(0.5, 1000.0)
        self.spin_w.setValue(shape_obj.width_mm if shape_obj else 20.0); self.spin_w.setSuffix(" mm")
        self.spin_h = QDoubleSpinBox(); self.spin_h.setRange(0.5, 1000.0)
        self.spin_h.setValue(shape_obj.height_mm if shape_obj else 15.0); self.spin_h.setSuffix(" mm")
        layout.addRow("Largeur :", self.spin_w)
        layout.addRow("Hauteur :", self.spin_h)

        self.spin_sides = QSpinBox(); self.spin_sides.setRange(3, 24)
        self.spin_sides.setValue(shape_obj.sides if shape_obj else 6)
        layout.addRow("Côtés (polygone) :", self.spin_sides)

        self.combo_layer = QComboBox()
        for l in self.layer_manager.layers:
            self.combo_layer.addItem(f"{l.name}  [{l.mode}]", l.id)
        if shape_obj and shape_obj.layer_id:
            idx = self.combo_layer.findData(shape_obj.layer_id)
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)
        layout.addRow("Calque :", self.combo_layer)

        pos_row = QHBoxLayout()
        self.spin_x = QDoubleSpinBox(); self.spin_x.setRange(-1000.0, 1000.0)
        self.spin_x.setDecimals(2); self.spin_x.setSuffix(" mm")
        self.spin_x.setValue(shape_obj.x_mm if shape_obj else 10.0)
        self.spin_y = QDoubleSpinBox(); self.spin_y.setRange(-1000.0, 1000.0)
        self.spin_y.setDecimals(2); self.spin_y.setSuffix(" mm")
        self.spin_y.setValue(shape_obj.y_mm if shape_obj else 10.0)
        pos_row.addWidget(QLabel("X :")); pos_row.addWidget(self.spin_x)
        pos_row.addWidget(QLabel("Y :")); pos_row.addWidget(self.spin_y)
        layout.addRow("Coin bas-gauche de l'objet à (mm) :", pos_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_object(self) -> ShapeObject:
        layer_id = self.combo_layer.currentData()
        if self.editing:
            obj = self.editing
        else:
            obj = ShapeObject(layer_id=layer_id)
        obj.shape_type = self.combo_type.currentText()
        obj.width_mm = self.spin_w.value()
        obj.height_mm = self.spin_h.value()
        obj.sides = self.spin_sides.value()
        obj.layer_id = layer_id
        obj.x_mm = self.spin_x.value()
        obj.y_mm = self.spin_y.value()
        return obj


# ============================================================================
# 5) EXTRACTION GEOMETRIQUE (thread-safe) + GENERATION G-CODE PAR CALQUE
# ============================================================================

def extract_vector_layer_data(objects, layer_manager: LayerManager):
    """À appeler dans le thread principal (Qt). Convertit chaque VectorObject en
    polygones purement numériques (mm), groupés par calque. Aucun objet Qt
    n'est conservé ensuite -> peut être passé sans risque à un QThread.
    """
    layers_data = {}
    for layer in layer_manager.layers:
        if not layer.enabled:
            continue
        layers_data[layer.id] = {"layer": layer.to_dict(), "polygons": []}

    for obj in objects:
        if obj.layer_id not in layers_data:
            continue
        path = obj.world_path()
        polygons = path.toSubpathPolygons(QTransform())
        poly_points = []
        for poly in polygons:
            pts = [(p.x(), p.y()) for p in poly]
            if len(pts) >= 2:
                poly_points.append(pts)
        if poly_points:
            layers_data[obj.layer_id]["polygons"].extend(poly_points)

    return layers_data


def _scanline_fill_segments(polygons, y):
    """Algorithme de balayage (pair-impair) : renvoie les segments [x_debut, x_fin]
    remplis par la ligne horizontale y, toutes contours confondus (gère les trous,
    ex. l'intérieur des lettres 'o', 'a', 'e'...)."""
    xs = []
    for poly in polygons:
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if y1 == y2:
                continue
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
    xs.sort()
    segments = []
    for i in range(0, len(xs) - 1, 2):
        if xs[i + 1] - xs[i] > 1e-6:
            segments.append((xs[i], xs[i + 1]))
    return segments


def build_vector_layers_gcode(layers_data, base_offset_x, base_offset_y, h_mm,
                               laser_cmd, s_max, overscan_dist=0.0):
    """Construit le G-Code (Phase "Calques Vectoriels") pour tous les calques actifs,
    à partir des données géométriques déjà extraites (voir extract_vector_layer_data).
    Les coordonnées des objets vectoriels sont déjà exprimées dans le repère
    machine (origine bas-gauche, Y croissant vers le haut) via
    VectorObject.world_transform : aucune inversion supplémentaire n'est
    nécessaire ici (contrairement à la gravure image / découpe SVG importée,
    qui restent en haut-gauche/Y descendant).

    overscan_dist (mm) : distance de surbalayage appliquée aux lignes de
    remplissage (mode 'Gravure Remplie'), comme pour la gravure image —
    le laser reste éteint pendant le dépassement de part et d'autre."""
    gcode = []
    total_time_seconds = 0.0
    power_samples = []

    def to_gcode_xy(x_mm, y_mm):
        return base_offset_x + x_mm, base_offset_y + y_mm

    for layer_id, data in layers_data.items():
        layer = data["layer"]
        polygons = data["polygons"]
        if not polygons:
            continue

        gcode.append(f"; --- CALQUE '{layer['name']}' [{layer['mode']}] ---")
        speed = layer["speed"]
        power_val = int(round((layer["power"] / 100.0) * s_max))
        gcode.append(f"F{speed}")

        if layer["mode"] == "Gravure Remplie":
            ys = [p[1] for poly in polygons for p in poly]
            if not ys:
                continue
            y_min, y_max = min(ys), max(ys)
            step = max(layer["line_interval"], 0.02)
            y = y_min
            line_idx = 0
            while y <= y_max:
                segments = _scanline_fill_segments(polygons, y)
                if segments:
                    ordered = segments if line_idx % 2 == 0 else list(reversed(
                        [(b, a) for a, b in segments]))
                    for seg in ordered:
                        sx_mm, ex_mm = seg[0], seg[1]
                        direction = 1.0 if ex_mm >= sx_mm else -1.0
                        real_sx, real_sy = to_gcode_xy(sx_mm, y)
                        real_ex, real_ey = to_gcode_xy(ex_mm, y)

                        if overscan_dist > 0:
                            pre_x, pre_y = to_gcode_xy(sx_mm - direction * overscan_dist, y)
                            post_x, post_y = to_gcode_xy(ex_mm + direction * overscan_dist, y)
                            gcode.append(f"G0 X{pre_x:.3f} Y{pre_y:.3f}")
                            gcode.append(f"{laser_cmd} S0")
                            gcode.append(f"G1 X{real_sx:.3f} Y{real_sy:.3f} F{speed}")
                            gcode.append(f"{laser_cmd} S{power_val}")
                            gcode.append(f"G1 X{real_ex:.3f} Y{real_ey:.3f} F{speed}")
                            gcode.append(f"{laser_cmd} S0")
                            gcode.append(f"G1 X{post_x:.3f} Y{post_y:.3f} F{speed}")
                            total_time_seconds += (abs(post_x - pre_x) / max(speed, 1)) * 60.0
                        else:
                            gcode.append(f"G0 X{real_sx:.3f} Y{real_sy:.3f}")
                            gcode.append(f"{laser_cmd} S{power_val}")
                            gcode.append(f"G1 X{real_ex:.3f} Y{real_ey:.3f} F{speed}")
                            total_time_seconds += (abs(real_ex - real_sx) / max(speed, 1)) * 60.0
                        gcode.append("M5")
                        power_samples.append(layer["power"])
                y += step
                line_idx += 1
        else:
            # Découpe ou Marquage : contour(s) uniquement
            for pass_num in range(layer["passes"]):
                if layer["passes"] > 1:
                    gcode.append(f"; Passe {pass_num + 1}/{layer['passes']}")
                for poly in polygons:
                    if len(poly) < 2:
                        continue
                    sx, sy = to_gcode_xy(*poly[0])
                    gcode.append(f"G0 X{sx:.3f} Y{sy:.3f}")
                    gcode.append(f"{laser_cmd} S{power_val}")
                    cx, cy = sx, sy
                    pts = poly + [poly[0]] if poly[0] != poly[-1] else poly
                    for (px, py) in pts[1:]:
                        nx, ny = to_gcode_xy(px, py)
                        gcode.append(f"G1 X{nx:.3f} Y{ny:.3f}")
                        total_time_seconds += (math.hypot(nx - cx, ny - cy) / max(speed, 1)) * 60.0
                        power_samples.append(layer["power"])
                        cx, cy = nx, ny
                    gcode.append("M5")

    return gcode, total_time_seconds, power_samples
