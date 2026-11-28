"""Traitement photo -> silhouette de découpe laser (partagé par la CLI et l'interface web).

Aucune dépendance à une interface : tout est en fonctions pures sur des tableaux numpy. Le calcul est
rangé par métier ; ce paquet expose les noms utilisés par l'API, la CLI et les tests :

    params (réglages, résultat) · framing (cadrage) · subject (sujet, visage) · tones (tons -> matière)
    plate (formes, anneau, œillet, ponts, contours) · halftone (trame de points) · engraving (gravure)
    lowpoly · qr · colors (palette) · layers (multicouche) · pipeline (process) · render (aperçus)
    export (SVG, DXF)
"""
from dataclasses import replace  # noqa: F401  (core.replace(params, …) : utilisé par l'API et les tests)

from .params import VERSION, Params, Result  # noqa: F401
from .framing import to_rgb, frame_box, rot_maps, crop_resize, valid_mask, codes_from_rgb  # noqa: F401
from .subject import remove_background, detect_face, ai_mask  # noqa: F401
from .plate import effective_ring, _load_font, _ring_path, extract_contours  # noqa: F401
from .engraving import engrave_png_bytes, svg_engrave_string  # noqa: F401
from .colors import color_classes  # noqa: F401
from .pipeline import layers_result, process  # noqa: F401
from .render import render_view  # noqa: F401
from .export import polys_bbox, svg_string, frame_svg, frame_dxf_lines, dxf_string  # noqa: F401
