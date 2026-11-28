"""Modèle 3D de la boîte assemblée, sans Qt : de quoi dessiner un rendu en perspective de l'aperçu.

Chaque panneau du résultat de `box_generator.build_box` est une plaque de `thickness` mm : on la replace dans
l'espace de la boîte (X largeur, Y profondeur, Z hauteur, Y = 0 sur la façade) et on en tire des faces planes
(deux faces larges, un quadrilatère par arête de contour ou de trou). Le dessin les trie de l'arrière vers l'avant
(`visible_faces`) et les remplit : algorithme du peintre, suffisant pour un aperçu.

Le couvercle s'ouvre : charnière à axe (plaques rigides tournant autour de la tige), charnière vivante
(la zone de charnière se courbe, longueur constante) ; angle 0 = fermé."""
import math

from laser_studio.vector import box_generator as bg

OPENABLE_LIDS = ("hinged", "pinned")
MAX_OPEN_DEG = 110.0
_ZONE_SLICES = 10                       # tranches de la zone courbe de la charnière vivante


class Face:
    """Polygone plan de l'espace (`points`, avec éventuellement des `holes`), de normale sortante `normal`."""
    __slots__ = ("points", "holes", "normal", "name")

    def __init__(self, points, holes, normal, name):
        self.points, self.holes, self.normal, self.name = points, holes, normal, name


# ----------------------------------------------------------------------
# Placement d'un panneau (u, v, f) -> (x, y, z) ; f = 0..1 dans l'épaisseur
# ----------------------------------------------------------------------
def panel_mapping(name, p, result):
    """Fonction (u, v, f) -> (x, y, z) du panneau `name`, boîte fermée."""
    W, D, H = result.outer
    t, cl = p.thickness, p.clearance
    kind = bg.lid_kind(p)
    half = cl / 2.0
    if name == "front":
        return lambda u, v, f: (u, f * t, v)
    if name == "back":
        return lambda u, v, f: (W - u, D - t + f * t, v)
    if name == "left":
        return lambda u, v, f: (f * t, D - u, v)
    if name == "right":
        return lambda u, v, f: (W - t + f * t, u, v)
    if name == "bottom":
        return lambda u, v, f: (W - u, v, f * t)
    if name == "top":
        if kind == "sliding":
            _, front_h = bg.wall_heights(p, H)
            return lambda u, v, f: (half + u, v, front_h + half + f * t)
        return lambda u, v, f: (u, v, H - t + f * t)
    if name == "lip":
        return lambda u, v, f: (t + half + u, t + half + v, H - 2 * t + f * t)
    if name.startswith("hinge"):                        # plaque de charnière à axe : plan YZ
        i, j = (int(x) - 1 for x in name[len("hinge"):].split("_"))
        x0 = bg.pin_hinge_columns(p, W)[i][j][0]
        return lambda u, v, f: (x0 + f * t, u, v)
    if name.startswith("magnet_"):                      # plaques d'aimant : plan XY
        side, number = name[len("magnet_"):].rstrip("0123456789"), int(name[len("magnet_"):].lstrip("lidwa"))
        size, xs = bg.magnet_layout(p, W)
        x0 = xs[number - 1] - size / 2.0
        if side == "lid":
            return lambda u, v, f: (x0 + u, t + half + v, H - 2 * t + f * t)
        return lambda u, v, f: (x0 + u, t + v, H - 3 * t + f * t)
    if name.startswith("foot"):                         # pieds : plaques empilées sous le fond (z < 0)
        i, layer = (int(x) for x in name[len("foot"):].split("_"))
        x0, y0 = bg.foot_origins(p, W, D)[i - 1]
        return lambda u, v, f: (x0 + u, y0 + v, -layer * t + f * t)
    if name.startswith("divider_x"):
        pos = bg.divider_positions(W, int(p.dividers_x), t, p.ratios_x)[int(name[len("divider_x"):]) - 1]
        return lambda u, v, f: (pos + f * t, u, v)
    if name.startswith("divider_y"):
        pos = bg.divider_positions(D, int(p.dividers_y), t, p.ratios_y)[int(name[len("divider_y"):]) - 1]
        return lambda u, v, f: (u, pos + f * t, v)
    raise KeyError(name)


def _is_lid_part(name, p, result):
    """Vrai pour une pièce qui suit le couvercle quand il s'ouvre."""
    kind = bg.lid_kind(p)
    if name == "top":
        return kind == "pinned"
    if name.startswith("magnet_lid"):
        return kind in OPENABLE_LIDS
    if name.startswith("hinge") and kind == "pinned":
        i, j = (int(x) - 1 for x in name[len("hinge"):].split("_"))
        return not bg.pin_hinge_columns(p, result.outer[0])[i][j][1]
    return False


def _rotation(axis, degrees):
    """Rotation autour d'un axe parallèle à X passant par (y, z) = axis : le bord avant du couvercle monte."""
    phi = -math.radians(degrees)
    c, s = math.cos(phi), math.sin(phi)
    ay, az = axis

    def apply(point):
        x, y, z = point
        dy, dz = y - ay, z - az
        return (x, ay + dy * c - dz * s, az + dy * s + dz * c)

    def apply_vec(vec):
        x, dy, dz = vec
        return (x, dy * c - dz * s, dy * s + dz * c)

    return apply, apply_vec


# ----------------------------------------------------------------------
# Charnière vivante : la zone de charnière se courbe (longueur constante)
# ----------------------------------------------------------------------
class LivingHinge:
    """Ligne moyenne de la zone de charnière, dans le plan (y, z) : part du haut de la paroi arrière, cap vers +Z,
    et tourne vers l'avant (-Y) de (90° - ouverture) en tout."""

    def __init__(self, p, result, open_deg):
        W, D, H = result.outer
        self.t = p.thickness
        self.length = p.hinge_length
        self.wall_top = bg.wall_heights(p, H)[1]
        self.y0 = D - self.t / 2.0
        self.bend = math.radians(90.0 - open_deg)            # courbure totale ; 0 = tout droit
        self.start = self.wall_top + self.length             # v du début du couvercle

    def centre(self, s):
        """(y, z, cap) du point d'abscisse s sur la ligne moyenne (cap : angle de la tangente depuis +Y)."""
        psi0 = math.pi / 2.0
        k = self.bend / self.length
        psi = psi0 + k * s
        if abs(k) < 1e-9:
            return self.y0, self.wall_top + s, psi0
        return (self.y0 + (math.sin(psi) - math.sin(psi0)) / k,
                self.wall_top + (math.cos(psi0) - math.cos(psi)) / k, psi)

    def point(self, v, f):
        """(y, z) du point de la paroi arrière placé en (v, f), pour v >= le début de la zone."""
        t = self.t
        if v <= self.wall_top + 1e-12:
            return self.y0 + (f - 0.5) * t, v
        s = min(v - self.wall_top, self.length)
        y, z, psi = self.centre(s)
        extra = max(0.0, v - self.start)                      # suite à plat : le couvercle
        y += extra * math.cos(psi)
        z += extra * math.sin(psi)
        nx, nz = math.cos(psi - math.pi / 2.0), math.sin(psi - math.pi / 2.0)
        return y + (f - 0.5) * t * nx, z + (f - 0.5) * t * nz

    def lid_transform(self):
        """Mouvement rigide qui amène le repère du couvercle fermé à sa position ouverte."""
        y_end, z_end, _ = self.centre(self.length)
        y_closed = LivingHinge.__new__(LivingHinge)
        y_closed.__dict__.update(self.__dict__)
        y_closed.bend = math.pi / 2.0
        y_c, z_c, _ = y_closed.centre(self.length)
        phi = self.bend - math.pi / 2.0                       # = -ouverture
        c, s = math.cos(phi), math.sin(phi)
        ty = y_end - (y_c * c - z_c * s)
        tz = z_end - (y_c * s + z_c * c)

        def apply(point):
            x, y, z = point
            return (x, y * c - z * s + ty, y * s + z * c + tz)

        def apply_vec(vec):
            x, dy, dz = vec
            return (x, dy * c - dz * s, dy * s + dz * c)

        return apply, apply_vec


# ----------------------------------------------------------------------
# Géométrie plane
# ----------------------------------------------------------------------
def _clip_loop(loop, v0, v1):
    """Contour fermé découpé à v0 <= v <= v1 (Sutherland-Hodgman). Peut être vide."""
    def clip(points, keep, edge):
        out = []
        for i, cur in enumerate(points):
            prev = points[i - 1]
            a, b = keep(prev), keep(cur)
            if a != b:
                k = (edge - prev[1]) / (cur[1] - prev[1])
                out.append((prev[0] + k * (cur[0] - prev[0]), edge))
            if b:
                out.append(cur)
        return out

    pts = list(loop)
    if v0 > -1e8:
        pts = clip(pts, lambda q: q[1] >= v0 - 1e-12, v0)
    if pts and v1 < 1e8:
        pts = clip(pts, lambda q: q[1] <= v1 + 1e-12, v1)
    return pts if len(pts) >= 3 else []


def _clip_segment(a, b, v0, v1):
    """Segment ab restreint à v0 <= v <= v1, ou None."""
    lo, hi = 0.0, 1.0
    dv = b[1] - a[1]
    if abs(dv) < 1e-12:
        return (a, b) if v0 - 1e-9 <= a[1] <= v1 + 1e-9 else None
    for edge, sign in ((v0, 1), (v1, -1)):
        k = (edge - a[1]) / dv
        if sign * dv > 0:
            lo = max(lo, k)
        else:
            hi = min(hi, k)
    if hi - lo < 1e-9:
        return None
    return ((a[0] + lo * (b[0] - a[0]), a[1] + lo * dv), (a[0] + hi * (b[0] - a[0]), a[1] + hi * dv))


def _unit(vec):
    n = math.sqrt(sum(c * c for c in vec))
    return tuple(c / n for c in vec) if n > 1e-12 else (0.0, 0.0, 0.0)


def _faces_of_slice(panel, fn, v0, v1, after, after_vec):
    """Faces de la tranche v0..v1 du panneau, placées par `fn` puis par le mouvement `after` (ou None)."""
    place = (lambda u, v, f: after(fn(u, v, f))) if after else fn
    loops = [panel.cut] + list(panel.holes)
    faces = []
    clipped = [_clip_loop(loop, v0, v1) for loop in loops]
    if clipped[0]:
        cu = sum(q[0] for q in clipped[0]) / len(clipped[0])
        cv = sum(q[1] for q in clipped[0]) / len(clipped[0])
        a, b = place(cu, cv, 0.0), place(cu, cv, 1.0)
        thick = _unit((b[0] - a[0], b[1] - a[1], b[2] - a[2]))
        holes = [h for h in clipped[1:] if h]
        for f, sign in ((0.0, -1.0), (1.0, 1.0)):
            faces.append(Face([place(u, v, f) for u, v in clipped[0]],
                              [[place(u, v, f) for u, v in h] for h in holes],
                              tuple(sign * c for c in thick), panel.name))
    for loop in loops:                                          # matière à gauche du sens de parcours
        for i, a in enumerate(loop):
            b = loop[(i + 1) % len(loop)]
            seg = _clip_segment(a, b, v0, v1)
            if seg is None:
                continue
            (au, av), (bu, bv) = seg
            du, dv = bu - au, bv - av
            length = math.hypot(du, dv)
            if length < 1e-9:
                continue
            mu, mv = (au + bu) / 2.0, (av + bv) / 2.0
            nu, nv = dv / length, -du / length                  # normale sortante de la matière
            o = place(mu, mv, 0.5)
            p2 = place(mu + 0.05 * nu, mv + 0.05 * nv, 0.5)
            normal = _unit((p2[0] - o[0], p2[1] - o[1], p2[2] - o[2]))
            faces.append(Face([place(au, av, 0.0), place(bu, bv, 0.0), place(bu, bv, 1.0), place(au, av, 1.0)],
                              [], normal, panel.name))
    return faces


# ----------------------------------------------------------------------
# Modèle complet
# ----------------------------------------------------------------------
# Matériaux : clé -> (couleur RVB, veinage 0..1 : 0 = uni comme l'acrylique)
MATERIALS = {
    "plywood": ((217, 172, 115), 1.0),
    "birch": ((233, 208, 163), 0.7),
    "oak": ((196, 152, 96), 1.0),
    "walnut": ((118, 82, 56), 0.9),
    "mdf": ((166, 130, 94), 0.25),
    "acrylic_black": ((46, 46, 52), 0.0),
    "acrylic_clear": ((176, 214, 232), 0.0),
}
DEFAULT_MATERIAL = "plywood"


def explode_faces(faces, centre, amount):
    """Écarte chaque pièce de `amount` mm du centre de la boîte, selon l'axe dominant de sa position
    (les cloisons, qui restent au centre, ne bougent pas)."""
    if amount <= 0.0:
        return faces
    boxes = {}
    for face in faces:
        for q in face.points:
            b = boxes.setdefault(face.name, [list(q), list(q)])
            for i in range(3):
                b[0][i], b[1][i] = min(b[0][i], q[i]), max(b[1][i], q[i])
    shift = {}
    for name, (lo, hi) in boxes.items():
        off = [(l + h) / 2.0 - c for l, h, c in zip(lo, hi, centre)]
        axis = max(range(3), key=lambda i: abs(off[i]))
        if abs(off[axis]) < 1.0:
            continue
        vec = [0.0, 0.0, 0.0]
        vec[axis] = amount if off[axis] > 0 else -amount
        shift[name] = tuple(vec)
    out = []
    for face in faces:
        d = shift.get(face.name)
        if d is None:
            out.append(face)
            continue
        out.append(Face([tuple(a + b for a, b in zip(q, d)) for q in face.points],
                        [[tuple(a + b for a, b in zip(q, d)) for q in h] for h in face.holes],
                        face.normal, face.name))
    return out


def build_faces(p, result, open_deg=0.0, explode=0.0):
    """Toutes les faces de la boîte assemblée ; `open_deg` ouvre le couvercle (charnière à axe ou vivante) ;
    `explode` (0..1) écarte les pièces pour voir l'assemblage."""
    faces = _build_closed_or_open(p, result, open_deg)
    if explode > 0.0:
        W, D, H = result.outer
        faces = explode_faces(faces, (W / 2.0, D / 2.0, H / 2.0), min(float(explode), 1.0) * 0.6 * max(W, D, H))
    return faces


def _build_closed_or_open(p, result, open_deg):
    kind = bg.lid_kind(p)
    W, D, H = result.outer
    t = p.thickness
    angle = min(max(float(open_deg), 0.0), MAX_OPEN_DEG) if kind in OPENABLE_LIDS else 0.0
    pin_motion = None
    living = None
    if kind == "pinned":
        pin_motion = _rotation((D - t / 2.0, H - t / 2.0), angle)
    elif kind == "hinged":
        living = LivingHinge(p, result, angle)
    faces = []
    for panel in result.panels:
        name = panel.name
        if living is not None and name == "back":
            faces += _living_back_faces(panel, p, result, living)
            continue
        fn = panel_mapping(name, p, result)
        motion = None
        if _is_lid_part(name, p, result):
            motion = pin_motion if kind == "pinned" else living.lid_transform()
        faces += _faces_of_slice(panel, fn, -1e9, 1e9, motion[0] if motion else None,
                                 motion[1] if motion else None)
    return faces


def _living_back_faces(panel, p, result, living):
    """Paroi arrière d'une charnière vivante : paroi droite, zone courbe (tranches), puis couvercle."""
    W = result.outer[0]
    base = panel_mapping("back", p, result)
    faces = _faces_of_slice(panel, base, -1e9, living.wall_top, None, None)

    def curved(u, v, f):
        y, z = living.point(v, f)
        return (W - u, y, z)

    n = _ZONE_SLICES
    cuts = [living.wall_top + living.length * k / n for k in range(n + 1)]
    for a, b in zip(cuts, cuts[1:]):
        faces += _faces_of_slice(panel, curved, a, b, None, None)
    faces += _faces_of_slice(panel, curved, living.start, 1e9, None, None)
    return faces


# ----------------------------------------------------------------------
# Caméra
# ----------------------------------------------------------------------
def project_point(point, yaw, pitch):
    """(x, y, z) -> (écran x, écran y vers le haut, profondeur) ; la profondeur croît en s'éloignant de l'observateur."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x, y, z = point
    rx = x * cy - y * sy
    ry = x * sy + y * cy
    return rx, z * cp + ry * sp, ry * cp - z * sp


def view_gradient(yaw, pitch):
    """Gradient de la profondeur : une face dont la normale lui est opposée regarde l'observateur."""
    return (math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), -math.sin(pitch))


def visible_faces(faces, yaw, pitch):
    """[(face, points écran, trous écran, luminosité 0..1)] de l'arrière vers l'avant, faces de dos écartées."""
    grad = view_gradient(yaw, pitch)
    light = _unit((-0.45, -0.6, 0.75))
    small = _small_parts(faces, yaw, pitch)
    out = []
    for face in faces:
        if sum(a * b for a, b in zip(face.normal, grad)) >= -1e-9:
            continue
        pts = [project_point(q, yaw, pitch) for q in face.points]
        depth = sum(q[2] for q in pts) / len(pts)
        if face.name in small:                    # une petite pièce se dessine d'un bloc, à la profondeur de son centre
            depth = small[face.name] + 1e-3 * depth
        shade = 0.45 + 0.55 * max(0.0, sum(a * b for a, b in zip(face.normal, light)))
        holes = [[project_point(q, yaw, pitch)[:2] for q in h] for h in face.holes]
        out.append((depth, face, [q[:2] for q in pts], holes, shade))
    out.sort(key=lambda item: -item[0])
    return [(face, pts, holes, shade) for _d, face, pts, holes, shade in out]


_SMALL_MM = 30.0


def _small_parts(faces, yaw, pitch):
    """{nom: profondeur du centre} des pièces de moins de _SMALL_MM dans toutes les directions (plaques de
    charnière, d'aimant) : trier leurs faces une à une les mélange."""
    boxes = {}
    for face in faces:
        for q in face.points:
            b = boxes.setdefault(face.name, [list(q), list(q)])
            for i in range(3):
                b[0][i], b[1][i] = min(b[0][i], q[i]), max(b[1][i], q[i])
    out = {}
    for name, (lo, hi) in boxes.items():
        if all(h - l < _SMALL_MM for l, h in zip(lo, hi)):
            out[name] = project_point(tuple((l + h) / 2.0 for l, h in zip(lo, hi)), yaw, pitch)[2]
    return out

