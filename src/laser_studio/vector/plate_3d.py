"""Modèle 3D des pièces plates (porte-clés, boules de Noël), sans Qt : de quoi dessiner l'aperçu en perspective.

Les générateurs donnent des contours fermés à plat (mm, Y vers le haut). Ici on en fait une plaque de `thickness` mm :

  - `nest_contours` range les contours par imbrication (comme le remplissage « pair-impair » du laser : un contour
    dans un contour est un trou, un contour dans un trou est une île) ;
  - `extrude` en tire des faces planes (dessus, dessous, un quadrilatère par arête), au format de `box_3d.Face` ;
  - la gravure est une surcouche posée sur le dessus (`kind = "engrave"`), de la couleur de la matière brûlée ;
  - le porte-clés à 2 couches empile les lettres sur le fond (`tier` 0 puis 1).

Le tri (`visible_faces`) n'est pas celui de `box_3d` : une plaque est une pièce basse et large, que l'algorithme du
peintre pur mélangerait (les lettres collées au fond, les parois d'un trou sous le dessus). On dessine donc couche par
couche (la plus basse d'abord, vue de dessus), et dans une couche les parois de l'arrière vers l'avant, puis le dessus
qui recouvre ce qu'il doit cacher, puis la gravure.
"""
import math

from laser_studio.vector import box_3d
from laser_studio.vector.box_3d import DEFAULT_MATERIAL, Face

DEFAULT_THICKNESS = 3.0
MIN_THICKNESS = 0.5
MAX_THICKNESS = 25.0
SIMPLIFY_MM = 0.03                       # tolérance d'allègement des contours : invisible à l'écran
_ENGRAVE_LIFT = 0.01                     # la gravure flotte à peine au-dessus du dessus (pas de scintillement)
_ENGRAVE_TIER = 100
_LIGHT = tuple(c / math.sqrt(0.45 ** 2 + 0.6 ** 2 + 0.75 ** 2) for c in (-0.45, -0.6, 0.75))   # comme `box_3d`
_MIN_GRAIN_AREA = 60.0                   # mm² : sous cette taille, le veinage ne se verrait pas
_GRAIN_STEP = 2.2

# Gravure : couleur de la matière marquée par le laser (bois brûlé ; acrylique dépoli)
ENGRAVE_COLORS = {
    "plywood": (112, 78, 44),
    "birch": (150, 108, 64),
    "oak": (98, 66, 36),
    "walnut": (62, 38, 24),
    "mdf": (84, 60, 40),
    "acrylic_black": (176, 176, 186),
    "acrylic_clear": (236, 246, 252),
}


class PlateFace(Face):
    """Face d'une plaque : `tier` = couche (0 = la plus basse), `kind` = « body » (matière) ou « engrave »."""
    __slots__ = ("tier", "kind")

    def __init__(self, points, holes, normal, name, tier=0, kind="body"):
        super().__init__(points, holes, normal, name)
        self.tier, self.kind = tier, kind


def engrave_color(material):
    """Couleur de la gravure sur la matière `material` (clé de `box_3d.MATERIALS`)."""
    return ENGRAVE_COLORS.get(material, ENGRAVE_COLORS[DEFAULT_MATERIAL])


def clamp_thickness(value):
    return min(max(float(value), MIN_THICKNESS), MAX_THICKNESS)


# ----------------------------------------------------------------------
# Contours : allègement, imbrication
# ----------------------------------------------------------------------
def signed_area(loop):
    """Aire algébrique (positive : sens trigonométrique)."""
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1]))


def _rdp(pts, tol):
    """Ramer-Douglas-Peucker d'une chaîne ouverte (sans récursion : un contour de lettre a des milliers de points)."""
    n = len(pts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        (ax, ay), (bx, by) = pts[i], pts[j]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        best, index = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            d = math.hypot(px - ax, py - ay) if length < 1e-12 else abs(dx * (py - ay) - dy * (px - ax)) / length
            if d > best:
                best, index = d, k
        if best > tol:
            keep[index] = True
            stack.append((i, index))
            stack.append((index, j))
    return [p for p, k in zip(pts, keep) if k]


def simplify_loop(loop, tol=SIMPLIFY_MM):
    """Contour fermé allégé de ses points quasi alignés (à `tol` mm près) ; jamais moins de 3 points."""
    pts = [tuple(p) for p in loop]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if len(pts) <= 8:
        return pts
    x0, y0 = pts[0]
    far = max(range(1, len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
    out = _rdp(pts[:far + 1], tol)[:-1] + _rdp(pts[far:] + [pts[0]], tol)[:-1]
    return out if len(out) >= 3 else pts


def _inside(point, loop):
    """Le point est-il dans le contour ? (tir de rayon)"""
    x, y = point
    inside = False
    for a, b in zip(loop, loop[1:] + loop[:1]):
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            inside = not inside
    return inside


def nest_contours(contours):
    """[(contour extérieur, [trous])] : un contour a pour profondeur le nombre de contours qui le contiennent ;
    profondeur paire = matière, impaire = trou de son plus petit contenant. Les îles dans un trou (l'intérieur d'un
    « o » découpé dans un disque) sont de nouveau de la matière."""
    loops = [list(c) for c in contours if len(c) >= 3]
    areas = [abs(signed_area(c)) for c in loops]
    boxes = [(min(p[0] for p in c), min(p[1] for p in c), max(p[0] for p in c), max(p[1] for p in c)) for c in loops]
    parent, depth = [], []
    for i, loop in enumerate(loops):
        x, y = loop[0]
        owner, count = -1, 0
        for j, other in enumerate(loops):
            if j == i or areas[j] <= areas[i]:
                continue
            bx0, by0, bx1, by1 = boxes[j]
            if x < bx0 or x > bx1 or y < by0 or y > by1 or not _inside((x, y), other):
                continue
            count += 1
            if owner < 0 or areas[j] < areas[owner]:
                owner = j
        parent.append(owner)
        depth.append(count)
    holes = {i: [] for i in range(len(loops)) if depth[i] % 2 == 0}
    for i, loop in enumerate(loops):
        if depth[i] % 2 == 1 and parent[i] in holes:
            holes[parent[i]].append(loop)
    return [(loops[i], holes[i]) for i in sorted(holes)]


def regions_of(contours, tol=SIMPLIFY_MM):
    """Contours allégés puis imbriqués : [(extérieur, [trous])]."""
    return nest_contours([simplify_loop(c, tol) for c in contours])


# ----------------------------------------------------------------------
# Faces
# ----------------------------------------------------------------------
def extrude(regions, z0, z1, name, tier=0):
    """Faces de la plaque z0..z1 : dessous, dessus (avec leurs trous) et une paroi par arête de chaque contour."""
    faces = []
    for outer, holes in regions:
        for z, sign in ((z0, -1.0), (z1, 1.0)):
            faces.append(PlateFace([(x, y, z) for x, y in outer], [[(x, y, z) for x, y in h] for h in holes],
                                   (0.0, 0.0, sign), name, tier))
        for loop, is_hole in [(outer, False)] + [(h, True) for h in holes]:
            side = 1.0 if signed_area(loop) > 0 else -1.0
            if is_hole:
                side = -side                       # la matière est autour d'un trou : la normale rentre dans le trou
            for a, b in zip(loop, loop[1:] + loop[:1]):
                du, dv = b[0] - a[0], b[1] - a[1]
                length = math.hypot(du, dv)
                if length < 1e-9:
                    continue
                faces.append(PlateFace([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], [],
                                       (side * dv / length, -side * du / length, 0.0), name, tier))
    return faces


def engraving(regions, z, name="engrave"):
    """Surcouche gravée posée à la hauteur `z` (le dessus de la pièce)."""
    return [PlateFace([(x, y, z + _ENGRAVE_LIFT) for x, y in outer],
                      [[(x, y, z + _ENGRAVE_LIFT) for x, y in h] for h in holes],
                      (0.0, 0.0, 1.0), name, _ENGRAVE_TIER, "engrave")
            for outer, holes in regions]


def plate_faces(cut, engrave=(), thickness=DEFAULT_THICKNESS):
    """Plaque découpée selon `cut` (extérieur, trous, îles), gravée selon `engrave`."""
    t = clamp_thickness(thickness)
    faces = extrude(regions_of(cut), 0.0, t, "plate")
    if engrave:
        faces += engraving(regions_of(engrave), t)
    return faces


def keychain_faces(result, thickness=DEFAULT_THICKNESS):
    """Porte-clés (`keychain_generator.KeychainResult` d'UN prénom). Classique : plaque gravée du prénom. 2 couches :
    le fond plein, et par-dessus la plaque du dessus (même contour, même épaisseur) dont le prénom est découpé de
    part en part : on voit le fond à travers les lettres. Les lettres sont des contours dans le contour de la
    plaque : l'imbrication pair-impair en fait des trous. Lettres à coller : la plaque, et les lettres découpées à
    part, collées par-dessus (la gravure de placement est cachée dessous)."""
    t = clamp_thickness(thickness)
    if getattr(result, "glue_letters", False):
        faces = extrude(regions_of(result.base_contours), 0.0, t, "base", 0)
        return faces + extrude(regions_of(result.text_contours), t, 2.0 * t, "letters", 1)
    if getattr(result, "two_layers", False):
        faces = extrude(regions_of(result.base_contours), 0.0, t, "base", 0)
        top = regions_of(list(result.base_contours) + list(result.text_contours))
        return faces + extrude(top, t, 2.0 * t, "top", 1)
    return plate_faces(result.base_contours, result.text_contours, t)


def ornament_faces(parts, thickness=DEFAULT_THICKNESS):
    """Boule de Noël (`ornament_region.OrnamentParts`) : plaque découpée, prénom et filet gravés s'il y en a."""
    return plate_faces(parts.cut, list(parts.name) + list(parts.frame), thickness)


def extent(faces):
    """(centre, rayon) d'une sphère qui contient toutes les faces : l'échelle ne bouge pas quand on tourne."""
    pts = [q for face in faces for q in face.points]
    if not pts:
        return (0.0, 0.0, 0.0), 1.0
    lo = [min(q[i] for q in pts) for i in range(3)]
    hi = [max(q[i] for q in pts) for i in range(3)]
    centre = tuple((a + b) / 2.0 for a, b in zip(lo, hi))
    return centre, max(max(math.dist(centre, q) for q in pts), 1.0)


# ----------------------------------------------------------------------
# Ordre de dessin
# ----------------------------------------------------------------------
def visible_faces(faces, yaw, pitch):
    """[(face, points écran, trous écran, luminosité 0..1)] dans l'ordre de dessin, faces de dos écartées.

    Vue de dessus (pitch >= 0) : couche par couche en montant ; dans une couche les parois de l'arrière vers
    l'avant (un dessus recouvre le bas des parois d'un trou, jamais l'inverse), puis le dessus ; la gravure en
    dernier. Vue de dessous : l'inverse (la couche haute est la plus loin)."""
    grad = box_3d.view_gradient(yaw, pitch)
    above = pitch >= 0.0
    out = []
    for face in faces:
        if sum(a * b for a, b in zip(face.normal, grad)) >= -1e-9:
            continue
        pts = [box_3d.project_point(q, yaw, pitch) for q in face.points]
        depth = sum(q[2] for q in pts) / len(pts)
        shade = 0.45 + 0.55 * max(0.0, sum(a * b for a, b in zip(face.normal, _LIGHT)))
        holes = [[box_3d.project_point(q, yaw, pitch)[:2] for q in h] for h in face.holes]
        cap = 1 if abs(face.normal[2]) > 0.5 else 0
        out.append(((face.tier if above else -face.tier, cap, -depth), face, [q[:2] for q in pts], holes, shade))
    out.sort(key=lambda item: item[0])
    return [(face, pts, holes, shade) for _key, face, pts, holes, shade in out]


# ----------------------------------------------------------------------
# Veinage du bois
# ----------------------------------------------------------------------
def grain_lines(face, grain):
    """Veinage d'un dessus ou d'un dessous : [(point 3D, point 3D, opacité 0..255)], lignes parallèles à X (le fil du
    bois suit la longueur de la feuille), un peu irrégulières. Rien pour une petite face ou un matériau uni."""
    if grain <= 0.0 or face.kind != "body" or abs(face.normal[2]) < 0.5:
        return []
    xs = [q[0] for q in face.points]
    ys = [q[1] for q in face.points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if (x1 - x0) * (y1 - y0) < _MIN_GRAIN_AREA:
        return []
    z = face.points[0][2]
    lines = []
    for i in range(int((y1 - y0) / _GRAIN_STEP) + 1):
        y = y0 + i * _GRAIN_STEP + 0.35 * math.sin(i * 1.7) + 0.2 * math.sin(i * 0.43)
        alpha = int(18 + 30 * grain * (0.5 + 0.5 * math.sin(i * 2.3 + 1.0)))
        lines.append(((x0, y, z), (x1, y, z), alpha))
    return lines
