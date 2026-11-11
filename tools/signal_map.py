#!/usr/bin/env python3
"""Carte des signaux : qui émet quoi, qui branche, qui exécute.

    python tools/signal_map.py         # docs/architecture/signaux.svg, .png
    python tools/signal_map.py --list     # la même chose, en texte

Lit le code (sans le lancer) : dans main_window.py et
ui/app/window_controller.py, chaque `émetteur.signal.connect(cible)` dont
l'émetteur est une classe de ui/ (page, onglet, panneau, menu). Pour
chaque connexion : la classe et son fichier, la méthode qui branche, la
fonction appelée et le fichier où elle est écrite.

L'image est rangée en deux colonnes : pages de réglages et onglets à
gauche, panneau machine et menu à droite ; chaque fonction est colorée
selon son fichier.
"""

import argparse
import ast
import glob
import os
import sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "architecture", "signaux")
# Fichiers où la fenêtre branche les signaux.
WIRING_FILES = (
    "main_window.py",
    os.path.join("ui", "app", "window_controller.py"),
)
# Paramètres de méthode dont le type ne se lit pas dans le code.
PARAMETER_CLASSES = {"actions": "AppActions"}


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def source_files():
    pattern = [
        glob.glob(os.path.join(ROOT, p), recursive=True)
        for p in (
            "*.py",
            "ui/**/*.py",
            "controllers/*.py",
            "stencil_studio/*.py",
        )
    ]
    return sorted(os.path.relpath(f, ROOT) for files in pattern for f in files)


class Index:
    """Classes, méthodes, fonctions et attributs `self.x = Classe(...)`."""

    def __init__(self):
        self.classes = {}  # classe -> fichier
        self.docs = {}  # fichier -> docstring du module
        self.methods = {}  # méthode -> [(classe, fichier)]
        self.functions = {}  # fonction de module -> fichier
        self.attributes = {}  # attribut -> (classe, fichier où il est créé)
        trees = {}
        for path in source_files():
            try:
                tree = ast.parse(read(path))
            except SyntaxError:
                continue
            trees[path] = tree
            self.docs[path] = ast.get_docstring(tree) or ""
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    self.classes[node.name] = path
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            self.methods.setdefault(item.name, []).append(
                                (node.name, path)
                            )
                elif isinstance(node, ast.FunctionDef):
                    self.functions.setdefault(node.name, path)
        for path, tree in trees.items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and ast.unparse(target.value) == "self"
                    ):
                        cls = self.class_of_call(node.value)
                        if cls or target.attr not in self.attributes:
                            self.attributes[target.attr] = (cls, path)

    def class_of_call(self, node):
        """`Classe(...)` -> "Classe" si c'est une classe du projet."""
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in self.classes
        ):
            return node.func.id
        return None

    def window_method(self, name):
        """Fichier de la méthode `name` de la fenêtre (mixin ou fenêtre)."""
        places = self.methods.get(name, [])
        for cls, path in places:
            if "Mixin" in cls or cls == "FullLaserStudio":
                return path
        return places[0][1] if places else None


def local_classes(method, index):
    """Variables de la méthode -> classe : `x = Classe()`, `x = self.a.b`."""
    found = dict(PARAMETER_CLASSES)
    for node in ast.walk(method):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target, value = node.targets[0], node.value
        cls = index.class_of_call(value)
        if cls is None and isinstance(value, ast.Attribute):
            cls = index.attributes.get(value.attr, (None, None))[0]
        if cls is None and isinstance(value, ast.Name):
            cls = found.get(value.id)
        name = ast.unparse(target)
        if cls:
            found[name] = cls
            if name.startswith("self."):
                index.attributes[name[5:]] = (cls, index.classes[cls])
    return found


def emitter_class(owner, local, index):
    if owner in local:
        return local[owner]
    if owner.startswith("self."):
        return index.attributes.get(owner.split(".")[-1], (None, None))[0]
    return None


def describe_target(node, owner_names, index):
    """(nom affiché, fichier) de la fonction appelée par le signal."""
    if isinstance(node, ast.Lambda):
        for sub in ast.walk(node.body):
            if isinstance(sub, ast.Call):
                return describe_target(sub.func, owner_names, index)
        return "lambda", "?"
    if isinstance(node, ast.Name):
        return node.id, index.functions.get(node.id, "?")
    if isinstance(node, ast.Attribute):
        owner = ast.unparse(node.value)
        if owner == "self":
            path = index.window_method(node.attr)
            return node.attr, path or f"Qt (QMainWindow.{node.attr})"
        if isinstance(node.value, ast.Call):
            cls = index.class_of_call(node.value)
            if cls:
                return f"{cls}(…).{node.attr}()", index.classes[cls]
        if owner.startswith("self.") and owner.count(".") == 1:
            # Méthode d'un objet de la fenêtre (contrôleur...) : self.x.f
            cls = index.attributes.get(owner[5:], (None, None))[0]
            if cls:
                return f"{owner[5:]}.{node.attr}", index.classes[cls]
        if owner in owner_names:  # variable locale : x = self.a.b
            source = owner_names[owner]
            attr = source.split(".")[-1]
            path = index.attributes.get(attr, (None, "?"))[1]
            return f"{source.replace('self.', '')}.{node.attr}", path
        return f"{owner}.{node.attr}", "Qt"
    return ast.unparse(node), "?"


def connections(index):
    rows = []
    methods = [
        m
        for path in WIRING_FILES
        for m in ast.walk(ast.parse(read(path)))
        if isinstance(m, ast.FunctionDef)
    ]
    # Première passe : `self.page = page` dans une méthode sert dans une autre.
    for method in methods:
        local_classes(method, index)
    for method in methods:
        local = local_classes(method, index)
        sources = {
            ast.unparse(n.targets[0]): ast.unparse(n.value)
            for n in ast.walk(method)
            if isinstance(n, ast.Assign)
            and len(n.targets) == 1
            and isinstance(n.value, ast.Attribute)
        }
        for call in ast.walk(method):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "connect"
                and isinstance(call.func.value, ast.Attribute)
            ):
                continue
            owner = ast.unparse(call.func.value.value)
            cls = emitter_class(owner, local, index)
            if cls is None or not index.classes[cls].startswith("ui"):
                continue
            target, target_file = describe_target(call.args[0], sources, index)
            rows.append(
                dict(
                    cls=cls,
                    cls_file=index.classes[cls],
                    signal=call.func.value.attr,
                    wired_in=method.name,
                    target=target,
                    target_file=target_file,
                )
            )
    return rows


def title_of(cls, index):
    """Nom affiché de la fenêtre : le texte entre « » de la docstring du
    module (« Paramètres du graveur »…), sinon la première ligne."""
    doc = index.docs.get(index.classes[cls], "")
    if "«" in doc and "»" in doc:
        return doc[doc.index("«") + 1 : doc.index("»")].strip()
    return doc.splitlines()[0].rstrip(".") if doc else ""


# -- dessin

PALETTE = {
    "laser_control_mixin.py": "#d9534f",
    "controllers/machine_profiles.py": "#8e44ad",
    "gcode_generation_mixin.py": "#e67e22",
    "image_processing_mixin.py": "#16a085",
    "vector_editing_mixin.py": "#2980b9",
    "controllers/matrix_image.py": "#c0392b",
    "controllers/job_queue.py": "#7f8c3d",
    "controllers/project.py": "#b8860b",
    "controllers/materials.py": "#9b59b6",
    "controllers/png2svg.py": "#1abc9c",
    "separation_mixin.py": "#6c5ce7",
    "main_window.py": "#34495e",
    "ui/app/window_controller.py": "#5d6d7e",
}
OTHER = "#95a5a6"
SECTIONS = (  # (colonne, titre, préfixe du fichier de la classe)
    ("left", "Pages de réglages (menu Paramètres)", "ui/settings/"),
    ("left", "Onglets", "ui/tabs/"),
    ("right", "Panneau machine (sous les onglets)", "ui/machine/"),
    ("right", "Menu et barre d'outils", "ui/app/"),
    ("right", "Autres", ""),
)
ROW, HEAD, GAP, SECTION = 22, 46, 14, 34
SIG_W, ARROW, FN_W = 300, 46, 300
COL_W = SIG_W + ARROW + FN_W + 250
TOP = 150


class Svg:
    def __init__(self):
        self.parts = []

    def text(
        self, x, y, s, size=12, weight="normal", fill="#1f2d3d", mono=False
    ):
        family = "DejaVu Sans Mono" if mono else "DejaVu Sans"
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}"'
            f' font-weight="{weight}" fill="{fill}">{escape(s)}</text>'
        )

    def rect(self, x, y, w, h, fill, stroke="none", rx=6):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"'
            f' fill="{fill}" stroke="{stroke}"/>'
        )

    def arrow(self, x, y, color):
        self.parts.append(
            f'<path d="M{x} {y} L{x + ARROW - 8} {y}" stroke="{color}"'
            f' stroke-width="2" fill="none"/>'
        )
        self.parts.append(
            f'<path d="M{x + ARROW - 8} {y - 4} L{x + ARROW} {y}'
            f' L{x + ARROW - 8} {y + 4} Z" fill="{color}"/>'
        )


def color(path):
    return PALETTE.get(path, OTHER)


def draw_class(svg, x, y, cls, rows, index):
    h = HEAD + len(rows) * ROW + 10
    svg.rect(x, y, COL_W, h, "#f7f9fb", "#d5dde5")
    svg.text(x + 12, y + 20, cls, size=14, weight="bold", mono=True)
    svg.text(
        x + 22 + len(cls) * 8.6,
        y + 20,
        f"— {title_of(cls, index)}",
        size=13,
        fill="#5d6d7e",
    )
    wired = ", ".join(sorted({r["wired_in"] for r in rows}))
    svg.text(
        x + 12,
        y + 37,
        f"{index.classes[cls]}   ·   branché dans " f"{wired}",
        size=11,
        fill="#7f8c8d",
        mono=True,
    )
    ry = y + HEAD
    for r in rows:
        cy = ry + ROW / 2
        svg.rect(x + 12, ry + 2, SIG_W, ROW - 4, "#ffffff", "#aab7c4", rx=4)
        svg.text(x + 20, cy + 4, r["signal"], size=11.5, mono=True)
        c = color(r["target_file"])
        svg.arrow(x + 12 + SIG_W, cy, c)
        fx = x + 12 + SIG_W + ARROW
        svg.rect(fx, ry + 2, FN_W, ROW - 4, c, rx=4)
        svg.text(
            fx + 8, cy + 4, r["target"], size=11.5, fill="#ffffff", mono=True
        )
        svg.text(
            fx + FN_W + 10,
            cy + 4,
            r["target_file"],
            size=11,
            fill=c if c != OTHER else "#7f8c8d",
            mono=True,
        )
        ry += ROW
    return h


def draw(rows, index):
    classes = list(dict.fromkeys(r["cls"] for r in rows))
    placed, body = set(), Svg()
    x0 = {"left": 30, "right": 30 + COL_W + 40}
    y = {"left": TOP, "right": TOP}
    for side, title, prefix in SECTIONS:
        members = [
            c
            for c in classes
            if c not in placed and index.classes[c].startswith(prefix)
        ]
        if not members:
            continue
        body.text(
            x0[side],
            y[side] + 20,
            title.upper(),
            size=14,
            weight="bold",
            fill="#5d6d7e",
        )
        y[side] += SECTION
        for cls in members:
            placed.add(cls)
            mine = [r for r in rows if r["cls"] == cls]
            y[side] += (
                draw_class(body, x0[side], y[side], cls, mine, index) + GAP
            )
        y[side] += 6
    width = x0["right"] + COL_W + 30
    height = max(y.values()) + 20
    head = Svg()
    head.text(
        30,
        40,
        "Laser Studio Pro — qui émet quoi, qui branche, " "qui exécute",
        size=24,
        weight="bold",
    )
    head.text(
        30,
        66,
        "Chaque page / onglet / panneau émet des signaux (à "
        "gauche). La fenêtre FullLaserStudio les branche (main_window"
        ".py, ui/app/window_controller.py) sur une fonction (à droite"
        "), colorée selon le fichier où elle est écrite.",
        size=13,
        fill="#5d6d7e",
    )
    used = {r["target_file"] for r in rows}
    legend = [(f, c) for f, c in PALETTE.items() if f in used]
    legend.append(("ui/ (widgets, boîtes), Qt, Stencil Studio", OTHER))
    lx, ly = 30, 96
    for name, c in legend:
        w = len(name) * 7.2 + 34
        if lx + w > width - 30:
            lx, ly = 30, ly + 24
        head.rect(lx, ly - 12, 16, 16, c, rx=3)
        head.text(lx + 22, ly + 1, name, size=12, mono=True)
        lx += w
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]
        + head.parts
        + body.parts
        + ["</svg>"]
    )


def save_png(svg_path, png_path, scale=1.5):
    """Rendu PNG du SVG avec Qt (sans écran)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QRectF
    from PyQt6.QtGui import QColor, QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    renderer = QSvgRenderer(svg_path)
    size = renderer.defaultSize()
    image = QImage(
        int(size.width() * scale),
        int(size.height() * scale),
        QImage.Format.Format_ARGB32,
    )
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, image.width(), image.height()))
    painter.end()
    image.save(png_path)
    del app  # gardée en vie jusqu'à la fin du rendu


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--list",
        action="store_true",
        help="affiche les connexions au lieu de dessiner",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT,
        help="chemin sans extension (défaut : %(default)s)",
    )
    args = parser.parse_args()
    index = Index()
    rows = connections(index)
    if args.list:
        for r in rows:
            print(
                f'{r["cls"]:20} {r["signal"]:36} -> {r["target"]:32} '
                f'{r["target_file"]}'
            )
        print(f"{len(rows)} connexions")
        return 0
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output + ".svg", "w", encoding="utf-8") as f:
        f.write(draw(rows, index))
    save_png(args.output + ".svg", args.output + ".png")
    print(f"{len(rows)} connexions -> {args.output}.svg / .png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
