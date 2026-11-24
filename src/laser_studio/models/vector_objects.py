"""Objets du dessin vectoriel : texte, forme, tracé SVG (VectorObject et
ses sous-classes). Position en mm, rotation, miroirs, calque ; leur tracé
est un QPainterPath (QtGui), sans widget."""
import math
import uuid
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QFont, QFontMetricsF, QPainterPath, QTransform, QPolygonF
from laser_studio.vector import boolean_ops
from laser_studio.vector.text_on_arc import arc_placements
from laser_studio.vector.text_on_path import path_placements, anchor_offset_mm


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

    def engraving_parts(self):
        """[(calque, tracé monde)] à graver : l'objet entier sur son calque. Un simple groupe donne ceux de
        ses objets (chacun sur son calque, avec son remplissage)."""
        return [(self.layer_id, self.world_path())]

    def set_layer(self, layer_id):
        """Change le calque de l'objet (et de tous ceux d'un groupe)."""
        self.layer_id = layer_id

    def to_dict(self):
        d = dict(self.__dict__)
        d["kind"] = self.kind
        return d

    @staticmethod
    def from_dict(d):
        kind = d.get("kind")
        if kind == "group":
            return GroupObject.from_dict(d)
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
                 letter_spacing_mm=0.0, arc_radius_mm=0.0, arc_inside=False,
                 arc_center_deg=None, follow_points=None, follow_closed=False, follow_center=0.5,
                 follow_reverse=False, follow_gap_mm=0.0, text_anchor="above", follow_guide_id=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.font_family = font_family
        self.size_mm = size_mm
        self.bold = bold
        self.italic = italic
        self.vertical = vertical
        self.letter_spacing_mm = letter_spacing_mm
        # Texte sur un cercle : rayon de la ligne de base (0 = texte droit), côté (extérieur / intérieur)
        # et angle où le texte est centré (None = en haut pour l'extérieur, en bas pour l'intérieur).
        self.arc_radius_mm = arc_radius_mm
        self.arc_inside = arc_inside
        self.arc_center_deg = arc_center_deg
        # Texte le long d'un objet existant : copie du tracé (mm, relative à l'origine de l'objet, Y vers
        # le haut ; None = texte droit), position du centre du texte sur ce tracé (0 à 1), sens inversé et
        # décalage de la ligne de base. Prioritaire sur le texte sur un cercle.
        self.follow_points = follow_points
        self.follow_closed = follow_closed
        self.follow_center = follow_center
        self.follow_reverse = follow_reverse
        self.follow_gap_mm = follow_gap_mm
        # Position des lettres par rapport au trait (cercle ou contour) : "above" (posées sur le trait),
        # "center" (centrées sur le trait) ou "below" (accrochées sous le trait). Voir
        # vector.text_on_path.anchor_offset_mm.
        self.text_anchor = text_anchor
        # Identifiant de l'objet dont le contour a été copié : permet de resynchroniser le texte si cet objet
        # change (VectorCanvasView.resync_text_guide).
        self.follow_guide_id = follow_guide_id

    def _font(self):
        font = QFont(self.font_family)
        font.setPointSizeF(self._REF_PT)
        font.setBold(self.bold)
        font.setItalic(self.italic)
        return font

    def _font_metrics_scale(self):
        font = self._font()
        metrics = QFontMetricsF(font)
        ref_height = metrics.ascent() if metrics.ascent() > 0 else self._REF_PT
        return font, metrics, self.size_mm / ref_height

    def text_advances_mm(self):
        """Largeur de chaque lettre, en mm (sans espacement)."""
        _font, metrics, scale = self._font_metrics_scale()
        return [metrics.horizontalAdvance(ch) * scale for ch in self.text]

    def _anchor_shift_mm(self, metrics, scale):
        """Décalage de la ligne de base selon `text_anchor`, le long du haut des lettres."""
        cap = metrics.capHeight() if metrics.capHeight() > 0 else metrics.ascent() * 0.7
        return anchor_offset_mm(getattr(self, "text_anchor", "above"), cap * scale)

    def arc_baseline_radius_mm(self):
        """Rayon réel de la ligne de base d'un texte sur un cercle : le rayon réglé, corrigé de l'ancrage
        (le haut des lettres vise l'extérieur, ou le centre pour un texte à l'intérieur)."""
        _font, metrics, scale = self._font_metrics_scale()
        shift = self._anchor_shift_mm(metrics, scale)
        radius = self.arc_radius_mm - shift if getattr(self, "arc_inside", False) else self.arc_radius_mm + shift
        return max(radius, 0.1)

    def local_path(self) -> QPainterPath:
        font, metrics, scale = self._font_metrics_scale()

        # getattr : un projet enregistré avant le texte sur arc / sur tracé n'a pas ces champs.
        if not self.vertical and getattr(self, "follow_points", None):
            return self._follow_path(font, metrics, scale)
        if not self.vertical and getattr(self, "arc_radius_mm", 0.0) > 0:
            return self._arc_path(font, metrics, scale)

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


    def _arc_path(self, font, metrics, scale) -> QPainterPath:
        """Texte posé sur un cercle : chaque lettre reste rigide, placée et tournée selon
        `vector.text_on_arc.arc_placements` (le calcul pur est testé sans Qt). Le chemin est construit
        en Y vers le haut, comme le repère monde, puis remis en Y vers le bas (repère local Qt)."""
        chars = list(self.text)
        advances = [metrics.horizontalAdvance(ch) * scale for ch in chars]
        spots = arc_placements(advances, self.arc_baseline_radius_mm(),
                               getattr(self, "arc_center_deg", None),
                               bool(getattr(self, "arc_inside", False)),
                               self.letter_spacing_mm)
        out = QPainterPath()
        for ch, advance, (px, py, rotation) in zip(chars, advances, spots):
            if ch.isspace():
                continue
            glyph = QPainterPath()
            glyph.addText(0, 0, font, ch)
            t = QTransform()
            t.translate(px, py)
            t.rotate(rotation)
            t.translate(-advance / 2.0, 0)
            t.scale(scale, -scale)
            out.addPath(t.map(glyph))
        out = QTransform().scale(1, -1).map(out)
        bbox = out.boundingRect()
        reanchor = QTransform()
        reanchor.translate(-bbox.left(), -bbox.bottom())
        return reanchor.map(out)

    def _follow_path(self, font, metrics, scale) -> QPainterPath:
        """Texte posé le long d'un tracé quelconque (copie du contour d'un autre objet) : chaque lettre reste
        rigide, placée et tournée selon `vector.text_on_path.path_placements` (calcul pur, testé sans Qt).
        Pas de réancrage : l'origine de l'objet reste celle du tracé, donc modifier le texte ne le décale pas."""
        chars = list(self.text)
        advances = [metrics.horizontalAdvance(ch) * scale for ch in chars]
        try:
            spots = path_placements(advances, self.follow_points,
                                    getattr(self, "follow_center", None),
                                    self.letter_spacing_mm,
                                    bool(getattr(self, "follow_reverse", False)),
                                    getattr(self, "follow_gap_mm", 0.0) + self._anchor_shift_mm(metrics, scale))
        except ValueError:      # tracé inutilisable (un seul point, longueur nulle)
            return QPainterPath()
        out = QPainterPath()
        for ch, advance, (px, py, rotation) in zip(chars, advances, spots):
            if ch.isspace():
                continue
            glyph = QPainterPath()
            glyph.addText(0, 0, font, ch)
            t = QTransform()
            t.translate(px, py)
            t.rotate(rotation)
            t.translate(-advance / 2.0, 0)
            t.scale(scale, -scale)
            out.addPath(t.map(glyph))
        return QTransform().scale(1, -1).map(out)


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


class GroupObject(VectorObject):
    """Groupe d'objets qui restent entiers (un texte reste un texte, modifiable une fois dégroupé), avec
    une opération (vector/boolean_ops.py) :

    - GROUP : simple groupe, déplacé d'un bloc ; chaque objet garde son calque et son remplissage ;
    - UNION, DIFFERENCE, INTERSECTION, EXCLUSION : les objets, du dessous (`children[0]`) vers le dessus,
      ne forment plus qu'un tracé, rempli et gravé sur le calque du groupe (celui de l'objet du dessous).

    Les objets gardent leur place au moment du groupement (repère monde) ; `origin` est le coin bas-gauche
    de leur ensemble à ce moment-là. Le groupe se déplace, pivote ou se retourne comme un objet : son
    repère local est celui d'un tracé SVG (ancré sur `origin`, Y vers le bas), et placement() ramène les
    objets à leur place actuelle.

        group = GroupObject([dessous, dessus], operation=boolean_ops.DIFFERENCE)
    """
    kind = "group"

    def __init__(self, children=(), operation=boolean_ops.GROUP, origin=None, name="", **kwargs):
        children = list(children)
        if operation not in boolean_ops.OPERATIONS:
            raise ValueError(f"opération inconnue : {operation!r}")
        if origin is None:
            box = QPainterPath()
            for child in children:
                box.addPath(child.world_path())
            rect = box.boundingRect()
            origin = (rect.left(), rect.top())
        kwargs.setdefault("x_mm", origin[0])
        kwargs.setdefault("y_mm", origin[1])
        kwargs.setdefault("layer_id", children[0].layer_id if children else None)
        super().__init__(**kwargs)
        self.children = children
        self.operation = operation
        self.origin = (float(origin[0]), float(origin[1]))
        self.name = name
        self._combined = None

    # -- géométrie

    def is_boolean(self):
        return self.operation != boolean_ops.GROUP

    def invalidate(self):
        """À appeler après avoir changé les objets ou l'opération du groupe."""
        self._combined = None

    def set_operation(self, operation):
        if operation not in boolean_ops.OPERATIONS:
            raise ValueError(f"opération inconnue : {operation!r}")
        self.operation = operation
        if self.is_boolean() and self.children:
            self.layer_id = self.children[0].layer_id
        self.invalidate()

    def move_child(self, child, step):
        """Monte (`step` > 0) ou descend un objet du groupe ; True s'il a bougé."""
        index = next((i for i, c in enumerate(self.children) if c is child), None)
        if index is None:
            return False
        target = max(0, min(len(self.children) - 1, index + step))
        if target == index:
            return False
        self.children.insert(target, self.children.pop(index))
        if self.is_boolean():
            self.layer_id = self.children[0].layer_id
        self.invalidate()
        return True

    def _to_local(self):
        return QTransform(1, 0, 0, -1, -self.origin[0], self.origin[1])

    def placement(self):
        """Transformation qui mène les objets de leur place au groupement à leur place actuelle."""
        return self._to_local() * self.world_transform()

    def combined_path(self):
        """Tracé des objets à leur place au groupement, combinés selon l'opération (gardé en cache)."""
        if self._combined is None:
            self._combined = boolean_ops.combine([c.world_path() for c in self.children], self.operation)
        return QPainterPath(self._combined)

    def local_path(self) -> QPainterPath:
        return self._to_local().map(self.combined_path())

    def local_parts(self):
        """[(calque, tracé local)] de chaque objet d'un simple groupe (affichage de chacun dans la couleur
        de son calque) ; [] pour une opération booléenne."""
        if self.is_boolean():
            return []
        to_local = self._to_local()
        return [(layer, to_local.map(path)) for child in self.children for layer, path in child.engraving_parts()]

    def engraving_parts(self):
        if self.is_boolean():
            return [(self.layer_id, self.world_path())]
        placement = self.placement()
        return [(layer, placement.map(path)) for child in self.children for layer, path in child.engraving_parts()]

    def set_layer(self, layer_id):
        self.layer_id = layer_id
        for child in self.children:
            child.set_layer(layer_id)
        self.invalidate()

    def released_children(self):
        """Les objets du groupe, chacun à sa place actuelle (dégrouper). Un groupe retourné (miroir) donne
        des tracés figés ; sinon chaque objet garde sa nature (texte, forme…), déplacé et pivoté."""
        placement = self.placement()
        mirrored = placement.determinant() < 0
        angle = math.degrees(math.atan2(placement.m12(), placement.m11()))
        released = []
        for child in self.children:
            if mirrored:
                world = placement.map(child.world_path())
                rect = world.boundingRect()
                local = QTransform(1, 0, 0, -1, -rect.left(), rect.top()).map(world)
                released.append(SvgPathObject(local_path_data=local, source_tag=child.kind,
                                              layer_id=child.layer_id, x_mm=rect.left(), y_mm=rect.top()))
                continue
            position = placement.map(QPointF(child.x_mm, child.y_mm))
            child.x_mm, child.y_mm = position.x(), position.y()
            child.rotation_deg = (child.rotation_deg + angle) % 360.0
            released.append(child)
        return released

    # -- enregistrement

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["kind"] = self.kind
        d["children"] = [child.to_dict() for child in self.children]
        d["origin"] = list(self.origin)
        return d

    @staticmethod
    def from_dict(d):
        obj = GroupObject.__new__(GroupObject)
        data = {k: v for k, v in d.items() if k not in ("kind", "children")}
        obj.__dict__.update(data)
        obj.children = [VectorObject.from_dict(child) for child in d.get("children") or []]
        obj.operation = data.get("operation", boolean_ops.GROUP)
        obj.origin = tuple(data.get("origin") or (obj.x_mm, obj.y_mm))
        obj.name = data.get("name", "")
        obj._combined = None
        return obj
