"""Exports texte : SVG et DXF des contours, du cadrage et des marques gravées.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

import numpy as np

from .layers import LAYER_COLORS


def polys_bbox(polys):
    """Rectangle englobant (x0, y0, x1, y1) d'une liste de polylignes, ou None."""
    pts = [np.asarray(q, float).reshape(-1, 2) for q in polys if len(q)]
    if not pts:
        return None
    a = np.vstack(pts)
    return (float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max()))


def svg_string(polys_mm, w_mm, h_mm, frame=None, marks=None, layers=None, colors=None):
    if layers:       # multicouche : une couleur par couche (LSP crée un calque par couleur)
        return _layers_svg(layers, w_mm, h_mm, frame, colors, marks)
    parts = []
    for q in polys_mm:
        d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + " Z"
        parts.append(f'<path d="{d}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_mm:.3f}mm" height="{h_mm:.3f}mm" '
            f'viewBox="0 0 {w_mm:.3f} {h_mm:.3f}">\n'
            f'<g id="CUT" fill="none" stroke="#ff0000" stroke-width="0.1">\n'
            + "\n".join(parts) + "\n</g>\n"
            + _marks_svg(marks)
            + (frame_svg(frame) if frame else "") + "</svg>\n")


def _layers_svg(layers, w_mm, h_mm, frame=None, colors=None, marks=None):
    gs = []
    for i, (name, polys) in enumerate(layers):
        d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + " Z" for q in polys)
        gs.append(f'<g id="{name}" fill="none" stroke="{("#%02x%02x%02x" % tuple(colors[i])) if colors else LAYER_COLORS[i % len(LAYER_COLORS)]}" stroke-width="0.1"><path d="{d}"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_mm:.3f}mm" height="{h_mm:.3f}mm" '
            f'viewBox="0 0 {w_mm:.3f} {h_mm:.3f}">\n' + "\n".join(gs) + "\n" + _marks_svg(marks) + (frame_svg(frame) if frame else "") + "</svg>\n")


def _marks_svg(marks):
    """Calque ENGRAVE (zones gravées pleines) : QR code gravé."""
    if not marks:
        return ""
    d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in q) + " Z" for q in marks)
    return f'<g id="ENGRAVE" fill="#000000" stroke="none" fill-rule="evenodd"><path d="{d}"/></g>\n'


def frame_svg(frame):
    x0, y0, x1, y1 = frame
    return (f'<g id="FRAME" fill="none" stroke="#00aa00" stroke-width="0.1">'
            f'<path d="M{x0:.3f},{y0:.3f} L{x1:.3f},{y0:.3f} L{x1:.3f},{y1:.3f} L{x0:.3f},{y1:.3f} Z"/></g>\n')


def frame_dxf_lines(frame, h_mm):
    """Entités DXF du rectangle de cadrage (calque FRAME), axe Y vers le haut."""
    x0, y0, x1, y1 = frame
    L = ["0", "POLYLINE", "8", "FRAME", "66", "1", "70", "1"]
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        L += ["0", "VERTEX", "8", "FRAME", "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
    return L + ["0", "SEQEND", "8", "FRAME"]


def dxf_string(polys_mm, h_mm, layer="CUT", frame=None, marks=None, layers=None):
    """DXF R12 minimal (POLYLINE fermées), axe Y vers le haut, en mm. layers : [(nom, contours)] pour le multicouche."""
    L = ["0", "SECTION", "2", "ENTITIES"]
    if layers:
        for name, polys in layers:
            for q in polys:
                L += ["0", "POLYLINE", "8", name, "66", "1", "70", "1"]
                for x, y in q:
                    L += ["0", "VERTEX", "8", name, "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
                L += ["0", "SEQEND", "8", name]
        polys_mm = []
    for q in polys_mm:
        L += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
        for x, y in q:
            L += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
        L += ["0", "SEQEND", "8", layer]
    for q in (marks or []):
        L += ["0", "POLYLINE", "8", "ENGRAVE", "66", "1", "70", "1"]
        for x, y in q:
            L += ["0", "VERTEX", "8", "ENGRAVE", "10", f"{x:.4f}", "20", f"{h_mm - y:.4f}"]
        L += ["0", "SEQEND", "8", "ENGRAVE"]
    if frame:
        L += frame_dxf_lines(frame, h_mm)
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"
