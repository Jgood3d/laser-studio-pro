#!/usr/bin/env python3
"""Ligne de commande : photo -> silhouette de découpe laser (SVG + DXF).
Utilise le même traitement que l'interface (core.py). Interface : `py studio.py`."""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from . import core
except ImportError:
    import core
try:
    from .i18n import available_languages, detect_language, set_language, tr
except ImportError:
    from i18n import available_languages, detect_language, set_language, tr


def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_preview(path, res):
    h, w = res.gray.shape
    panels = [
        (core.render_view(res, "original"), tr("Original")),
        (core.render_view(res, "material"), tr("Material (black)")),
        (core.render_view(res, "result"), tr("Result + bridges (red)")),
    ]
    bar = 44
    canvas = Image.new("RGB", (w * 3, h + bar), "white")
    draw = ImageDraw.Draw(canvas)
    f = _font(24)
    for i, (img, title) in enumerate(panels):
        canvas.paste(Image.fromarray(img), (i * w, bar))
        draw.text((i * w + 12, 8), title, fill="black", font=f)
    canvas.save(path)


def build_parser():
    ap = argparse.ArgumentParser(description=tr("Photo to laser-cut stencil silhouette (prototype)."))
    ap.add_argument("image", help=tr("Input image (jpg/png)"))
    ap.add_argument("-o", "--output", help=tr("Output base name (default: image name)"))
    ap.add_argument("--lang", choices=available_languages() or None, help=tr("Interface language"))
    ap.add_argument("--size", type=float, default=100.0, help=tr("Final size in mm (largest side)"))
    ap.add_argument("--shape", choices=["circle", "oval", "rect", "rrect", "heart", "star", "tree", "none"], default="circle", help=tr("Outer shape"))
    ap.add_argument("--hang", choices=["none", "top", "top_left", "top_right", "both"], default="none", help="Hanging loop")
    ap.add_argument("--hang-style", choices=["round", "drop"], default="round", help="Loop shape")
    ap.add_argument("--hang-hole", type=float, default=3.0, help="Hanging hole diameter in mm")
    ap.add_argument("--text-top", default="", help="Text on the top of the ring")
    ap.add_argument("--text-bottom", default="", help="Text on the bottom of the ring")
    ap.add_argument("--text-size", type=float, default=6.0, help="Letter height in mm")
    ap.add_argument("--lp-points", type=int, default=400, help="Low poly style: number of mesh vertices")
    ap.add_argument("--lp-beam", type=float, default=1.0, help="Low poly style: edge width in mm")
    ap.add_argument("--lp-render", choices=["wire", "shade", "solid"], default="solid", help="Low poly style: facet rendering")
    ap.add_argument("--line-pitch", type=float, default=1.5, help="Lines style: spacing between lines in mm")
    ap.add_argument("--line-angle", type=float, default=30.0, help="Lines style: angle in degrees")
    ap.add_argument("--line-break", type=float, default=30.0, help="Lines style: longest slot before a bridge in mm (0 = continuous)")
    ap.add_argument("--ring", type=float, default=4.0, help=tr("Outer ring width in mm"))
    ap.add_argument("--bridge", type=float, default=1.5, help=tr("Bridge width in mm"))
    ap.add_argument("--min-feature", type=float, default=0.8, help=tr("Smallest cuttable detail in mm"))
    ap.add_argument("--threshold", type=float, help=tr("Threshold 0-255 (default: automatic)"))
    ap.add_argument("--bias", type=float, default=0.0, help=tr("Offset added to the threshold"))
    ap.add_argument("--mode", choices=["local", "global"], default="local",
                    help=tr("Tone mode: local (keeps facial details) or global (single threshold)"))
    ap.add_argument("--local-contrast", type=float, default=10.0,
                    help=tr("Local mode: how much darker than surroundings (higher = fewer details)"))
    ap.add_argument("--dark-offset", type=float, default=90.0,
                    help=tr("Local mode: very dark areas below threshold minus this value are solid"))
    ap.add_argument("--grow", type=float, default=0.0,
                    help=tr("Line weight in mm: positive thickens all lines, negative thins them"))
    ap.add_argument("--drop-thin", action="store_true",
                    help=tr("Remove lines thinner than the minimum detail instead of thickening them"))
    ap.add_argument("--style", choices=["stencil", "halftone", "lines", "engrave", "lowpoly"], default="stencil",
                    help=tr("Output: stencil (shapes with bridges) or halftone (dot pattern for photos)"))
    ap.add_argument("--dot-pitch", type=float, default=1.6, help=tr("Halftone: dot pitch in mm"))
    ap.add_argument("--tone", choices=["luminance", "darkest", "mix"], default="luminance",
                    help=tr("Tone source: luminance, darkest channel (saturated colours become solid) or a mix"))
    ap.add_argument("--outline", type=float, default=1.0, help=tr("Solid outline along the subject edge, millimetres"))
    ap.add_argument("--texture", type=float, default=1.0, help=tr("Texture smoothing passes (0 = off)"))
    ap.add_argument("--blur", type=float, default=1.5, help=tr("Blur before thresholding (px)"))
    ap.add_argument("--no-contrast", action="store_true", help=tr("Disable contrast equalization"))
    ap.add_argument("--invert", action="store_true", help=tr("Keep light areas instead of dark"))
    ap.add_argument("--smooth", type=float, default=2.0, help=tr("Contour smoothing (px)"))
    ap.add_argument("--simplify", type=float, default=0.8, help=tr("Contour simplification (px)"))
    ap.add_argument("--remove-bg", action="store_true",
                    help=tr("Isolate the subject (GrabCut), background is cut away"))
    ap.add_argument("--subject", type=float, nargs=4, metavar=("X", "Y", "W", "H"),
                    default=(0.03, 0.03, 0.94, 0.94), help=tr("Subject box as fractions 0-1 (with --remove-bg)"))
    ap.add_argument("--hints", help=tr("Hint image: green strokes = subject, red strokes = background"))
    ap.add_argument("--min-island", type=float, default=10.0,
                    help=tr("Drop isolated pieces smaller than this area (mm2)"))
    ap.add_argument("--max-bridge", type=float, default=8.0,
                    help=tr("Drop isolated pieces farther than this from the body (mm)"))
    ap.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "W", "H"), help=tr("Crop region in source pixels"))
    ap.add_argument("--work-size", type=int, default=1200, help=tr("Working resolution in pixels"))
    return ap


def main(argv=None):
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang")
    known, _ = pre.parse_known_args(argv)
    set_language(known.lang or detect_language())
    args = build_parser().parse_args(argv)
    if args.lang:
        set_language(args.lang)

    if not os.path.isfile(args.image):
        print(tr("Error: file not found: {path}", path=args.image), file=sys.stderr)
        return 1
    base = args.output or os.path.splitext(args.image)[0]

    print(tr("Loading image: {path}", path=args.image))
    img = core.to_rgb(Image.open(args.image))
    if args.crop:
        x, y, w, h = args.crop
        img = img.crop((x, y, x + w, y + h))
    W, H = img.size
    frame = {"cx": 0.5, "cy": 0.5, "w": 1.0, "aspect": 1.0 if args.shape in ("circle", "heart", "star", "tree") else W / H}
    box = core.frame_box(W, H, frame)
    rgb = core.crop_resize(img, box, args.work_size)

    p = core.Params(size_mm=args.size, shape=args.shape, ring_mm=args.ring, bridge_mm=args.bridge,
                    max_bridge_mm=args.max_bridge, min_island_mm2=args.min_island,
                    output=args.style, lp_points=args.lp_points, lp_beam_mm=args.lp_beam, lp_style=args.lp_render, dot_pitch_mm=args.dot_pitch, min_feature_mm=args.min_feature, keep_thin=not args.drop_thin, grow_mm=args.grow, mode=args.mode, tone_source=args.tone,
                    auto_threshold=args.threshold is None, threshold=args.threshold or 128.0,
                    bias=args.bias, blur=args.blur, texture=args.texture, outline_mm=args.outline, contrast=not args.no_contrast, invert=args.invert,
                    local_contrast=args.local_contrast, dark_offset=args.dark_offset,
                    smooth=args.smooth, simplify=args.simplify,
                    hang=args.hang, hang_style=args.hang_style, hang_hole_mm=args.hang_hole,
                    line_pitch_mm=args.line_pitch, line_angle=args.line_angle, line_break_mm=args.line_break,
                    text_top=args.text_top, text_bottom=args.text_bottom, text_size_mm=args.text_size)

    subject = None
    if args.remove_bg:
        print(tr("Isolating the subject..."))
        codes = None
        if args.hints:
            hints = Image.open(args.hints).convert("RGB").resize((rgb.shape[1], rgb.shape[0]), Image.NEAREST)
            codes = core.codes_from_rgb(np.array(hints))
        subject = core.remove_background(rgb, args.subject, codes)

    print(tr("Building the mask..."))
    res = core.process(rgb, p, subject)
    s = res.stats
    print(tr("Threshold used: {t:.0f}", t=s["threshold"]))
    print(tr("Islands connected: {n}", n=s["linked"]))
    print(tr("Islands removed (too small or too far): {n}", n=s["dropped"]))
    print(tr("Contours: {n}", n=s["contours"]))
    print(tr("Total cut length: {mm:.0f} mm", mm=s["length_mm"]))
    print(tr("Final size: {w:.1f} x {h:.1f} mm", w=res.w_mm, h=res.h_mm))

    with open(base + "_cut.svg", "w", encoding="utf-8") as f:
        f.write(core.svg_string(res.polys_mm, res.w_mm, res.h_mm))
    with open(base + "_cut.dxf", "w", encoding="ascii") as f:
        f.write(core.dxf_string(res.polys_mm, res.h_mm))
    write_preview(base + "_preview.png", res)
    Image.fromarray(rgb).save(base + "_work.png")
    for ext in ("_cut.svg", "_cut.dxf", "_preview.png", "_work.png"):
        print(tr("File written: {path}", path=base + ext))
    print(tr("Done."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
