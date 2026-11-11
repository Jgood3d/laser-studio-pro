#!/usr/bin/env python3
"""Autotest : vérifie que les bibliothèques de ce PC (OpenCV, numpy, scipy...) donnent les mêmes
résultats que ceux attendus. Usage :  py selftest.py
Envoyer la sortie complète si une ligne affiche DIFF."""
import sys
import numpy as np
import cv2
import scipy
from scipy import ndimage as ndi
import core

# Valeurs mesurées avec Python 3.12 / OpenCV 4.13 / numpy 2.4 / scipy 1.17 (tolérance en %)
EXPECTED = {
    'gris : moyenne': 219.555,
    'CLAHE : moyenne': 220.776,
    'flou gaussien : moyenne': 219.556,
    'filtre bilateral : moyenne': 219.64,
    'seuil adaptatif : pixels noirs': 19807.0,
    'ouverture : pixels': 2868.0,
    'fermeture : pixels': 18827.0,
    'dilatation : pixels': 41749.0,
    'composantes connexes': 6.0,
    'distance (scipy) : somme': 18677338.268,
    'reduction INTER_AREA : moyenne': 223.761,
    'grabcut : pixels sujet': 127630.0,
 'grabcut N&B + rectangle : pixels sujet': 129455.0,
    'local (defaut) : contours': 9.0,
    'local (defaut) : longueur mm': 1553.65,
    'local (defaut) : ponts': 5.0,
    'local (defaut) : supprimes': 0.0,
    'local (defaut) : pixels de matiere': 64855.0,
    'dessin au trait : contours': 10.0,
    'dessin au trait : longueur mm': 1506.467,
    'dessin au trait : ponts': 4.0,
    'dessin au trait : supprimes': 0.0,
    'dessin au trait : pixels de matiere': 66734.0,
    'oeillet cercle : largeur mm': 100.0,
    'oeillet cercle : hauteur mm': 106.83,
    'oeillet cercle : contours': 3.0,
    'oeillet cercle : pixels de matiere': 44665.0,
    'texte ovale + 2 trous : largeur mm': 113.83,
    'texte ovale + 2 trous : hauteur mm': 100.0,
    'texte ovale + 2 trous : contours': 12.0,
    'texte ovale + 2 trous : pixels de matiere': 89792.0,
    'coeur : largeur mm': 100.0,
    'coeur : hauteur mm': 100.0,
    'coeur : contours': 3.0,
    'coeur : pixels de matiere': 45665.0,
    'tramage stucki : pixels noirs': 32722.0,
    'tramage floyd : pixels noirs': 32737.0,
    'tramage atkinson : pixels noirs': 32669.0,
    'tramage bayer : pixels noirs': 32768.0,
    'tramage stucki 4 niveaux : somme': 8360175.0,
    'gravure : largeur px': 630.0,
    'gravure : hauteur px': 683.0,
    'gravure : contours': 2.0,
    'caisson : cadres': 8.0,
    'caisson : vis': 4.0,
    'caisson : pieces': 11.0,
    'caisson a encoches rectangle : parois': 4.0,
    'caisson a encoches rectangle : fentes': 0.0,
    'caisson a encoches rectangle : fentes de plaque': 22.0,
    'caisson a encoches rectangle arrondi : parois': 1.0,
    'caisson a encoches rectangle arrondi : fentes': 66.0,
    'caisson a encoches rectangle arrondi : fentes de plaque': 23.0,
    'caisson a encoches cercle : parois': 1.0,
    'caisson a encoches cercle : fentes': 168.0,
    'caisson a encoches cercle : fentes de plaque': 20.0,
    'sapin : largeur mm': 100.0,
    'sapin : hauteur mm': 106.67,
    'sapin : contours': 2.0,
    'sapin : pixels de matiere': 49683.0,
    'caisson a encoches etoile : parois': 10.0,
    'caisson a encoches etoile : avertissements': 0.0,
    'caisson a encoches sapin : parois': 8.0,
    'caisson a encoches sapin : avertissements': 0.0,
    'support empile : pieces du pied': 4.0,
    'support empile : contours du fond': 8.0,
    'support empile : avertissements': 0.0,
    'support encoches : pieces du pied': 4.0,
    'support encoches : contours du fond': 22.0,
    'support encoches : avertissements': 0.0,
    'lignes : fentes': 45.0,
    'lignes : pixels de matiere': 60920.0,
    'low poly : maillage plausible': 1.0,
    'qr : gravé relu': 1.0,
    'qr : ajouré relu': 1.0,
    'qr : calque ENGRAVE exporté': 1.0,
    'multicouche : 4 plaques + repères': 1.0,
    'multicouche couleur : palette': 1.0,
    'couleur auto : logo 2 plaques': 1.0,
    'couleur : pipette 3 couleurs': 1.0,
    'couleur : îlots gardés (pièces libres)': 1.0,
    'couleur : logo plein cadre (fond = couleur dominante)': 1.0,
    'multicouche : fond à part + gravure': 1.0,
}
TOL = {"default": 3.0, "grabcut": 12.0}


def synthetic():
    """Dessin 'cartoon' : fond blanc, corps rose, traits noirs fins, yeux, zone violette."""
    img = np.full((600, 600, 3), 255, np.uint8)
    cv2.ellipse(img, (300, 330), (170, 210), 0, 0, 360, (195, 160, 215), -1, cv2.LINE_AA)   # RGB rose
    cv2.ellipse(img, (300, 330), (170, 210), 0, 0, 360, (30, 20, 40), 3, cv2.LINE_AA)
    cv2.ellipse(img, (210, 150), (40, 130), -15, 0, 360, (195, 160, 215), -1, cv2.LINE_AA)
    cv2.ellipse(img, (210, 150), (40, 130), -15, 0, 360, (30, 20, 40), 3, cv2.LINE_AA)
    cv2.ellipse(img, (390, 150), (40, 130), 15, 0, 360, (195, 160, 215), -1, cv2.LINE_AA)
    cv2.ellipse(img, (390, 150), (40, 130), 15, 0, 360, (30, 20, 40), 3, cv2.LINE_AA)
    for cx in (240, 360):
        cv2.circle(img, (cx, 300), 38, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, 300), 38, (30, 20, 40), 3, cv2.LINE_AA)
        cv2.circle(img, (cx, 305), 22, (10, 10, 10), -1, cv2.LINE_AA)
        cv2.circle(img, (cx - 7, 296), 6, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.ellipse(img, (300, 400), (60, 30), 0, 20, 160, (30, 20, 40), 2, cv2.LINE_AA)   # sourire (trait fin)
    cv2.line(img, (300, 440), (300, 520), (30, 20, 40), 2, cv2.LINE_AA)                # trait fin
    cv2.ellipse(img, (300, 360), (30, 20), 0, 0, 360, (160, 140, 190), -1, cv2.LINE_AA)  # nez violet
    return img


def measure():
    cv2.setRNGSeed(0)
    rgb = synthetic()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    m = {}
    m["gris : moyenne"] = float(gray.mean())
    m["CLAHE : moyenne"] = float(cv2.createCLAHE(2.0, (8, 8)).apply(gray).mean())
    m["flou gaussien : moyenne"] = float(cv2.GaussianBlur(gray, (0, 0), 2.0).mean())
    m["filtre bilateral : moyenne"] = float(cv2.bilateralFilter(gray, 0, 40, 6.0).mean())
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 75, 10) > 0
    m["seuil adaptatif : pixels noirs"] = float(thr.sum())
    mat = (gray < 140).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    m["ouverture : pixels"] = float(cv2.morphologyEx(mat, cv2.MORPH_OPEN, k).sum())
    m["fermeture : pixels"] = float(cv2.morphologyEx(mat, cv2.MORPH_CLOSE, k).sum())
    m["dilatation : pixels"] = float(cv2.dilate(mat, k).sum())
    m["composantes connexes"] = float(cv2.connectedComponentsWithStats(mat, connectivity=4)[0])
    m["distance (scipy) : somme"] = float(ndi.distance_transform_edt(1 - mat).sum())
    sm = cv2.resize(rgb, (300, 300), interpolation=cv2.INTER_AREA)
    m["reduction INTER_AREA : moyenne"] = float(sm.mean())
    sub = core.remove_background(rgb, (0.05, 0.05, 0.9, 0.9), None, size=300)
    m["grabcut : pixels sujet"] = float(sub.sum())
    gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)  # image strictement grise (R=G=B), comme une photo N&B
    cv2.setRNGSeed(0)
    sub_g = core.remove_background(gray3, (0.2, 0.1, 0.6, 0.8), None, size=300)
    m["grabcut N&B + rectangle : pixels sujet"] = float(sub_g.sum())
    for name, kw in (("local (defaut)", {}), ("dessin au trait", dict(mode="global", texture=0, blur=1.0, grow_mm=0.3))):
        r = core.process(rgb, core.Params(size_mm=100, **kw), sub)
        m[f"{name} : contours"] = float(r.stats["contours"])
        m[f"{name} : longueur mm"] = float(r.stats["length_mm"])
        m[f"{name} : ponts"] = float(r.stats["linked"])
        m[f"{name} : supprimes"] = float(r.stats["dropped"])
        m[f"{name} : pixels de matiere"] = float(r.mat.sum())
    blank = np.full((600, 600, 3), 255, np.uint8)   # formes, accroche et texte : indépendants de la photo
    for name, kw in (("oeillet cercle", dict(shape="circle", hang="top")),
                     ("texte ovale + 2 trous", dict(shape="oval", text_top="NOEL", text_bottom="Emma", hang="both")),
                     ("coeur", dict(shape="heart", hang="top")),
                     ("sapin", dict(shape="tree", hang="top"))):
        r = core.process(blank, core.Params(size_mm=100, **kw))
        m[f"{name} : largeur mm"] = round(r.w_mm, 2)
        m[f"{name} : hauteur mm"] = round(r.h_mm, 2)
        m[f"{name} : contours"] = float(r.stats["contours"])
        m[f"{name} : pixels de matiere"] = float(r.mat.sum())
    import engrave, lightbox
    grad = np.tile(np.linspace(0, 255, 256, dtype=np.float32), (256, 1))
    for meth in ("stucki", "floyd", "atkinson", "bayer"):
        m[f"tramage {meth} : pixels noirs"] = float((engrave.dither(grad, meth, 2) == 0).sum())
    m["tramage stucki 4 niveaux : somme"] = float(engrave.dither(grad, "stucki", 4).astype(np.int64).sum())
    pe = core.Params(size_mm=80, output="engrave", shape="circle", hang="top", eng_dpi=200)
    re_ = core.process(blank, pe)
    m["gravure : largeur px"] = float(re_.engrave.shape[1])
    m["gravure : hauteur px"] = float(re_.engrave.shape[0])
    m["gravure : contours"] = float(re_.stats["contours"])
    pb = core.Params(size_mm=80, output="halftone", shape="circle", hang="top", box_depth_mm=24)
    bx = lightbox.make_box(core.process(blank, pb), pb)
    m["caisson : cadres"] = float(bx["frames"])
    m["caisson : vis"] = float(bx["screws"])
    m["caisson : pieces"] = float(len(bx["layout"]))
    for nm, shp in (("rectangle", "rect"), ("rectangle arrondi", "rrect"), ("cercle", "circle")):
        pf = core.Params(size_mm=100, output="halftone", shape=shp, box_style="fingers", box_depth_mm=24)
        bf = lightbox.make_box(core.process(blank, pf), pf)
        walls = [pt for pt in bf["parts"] if pt["name"] == "wall"]
        m[f"caisson a encoches {nm} : parois"] = float(len(walls))
        m[f"caisson a encoches {nm} : fentes"] = float(sum(1 for pt in walls for q in pt["polys"] if len(q) == 2))
        m[f"caisson a encoches {nm} : fentes de plaque"] = float(sum(len(pt["polys"]) for pt in bf["parts"] if pt["name"] == "back"))
    for nm, shp in (("etoile", "star"), ("sapin", "tree")):
        pf = core.Params(size_mm=100, output="halftone", shape=shp, box_style="fingers", box_depth_mm=24, ring_mm=6, hang="top")
        bf = lightbox.make_box(core.process(blank, pf), pf)
        m[f"caisson a encoches {nm} : parois"] = float(sum(1 for pt in bf["parts"] if pt["name"] == "wall"))
        m[f"caisson a encoches {nm} : avertissements"] = float(len(bf["notes"]))
    for nm, sty in (("empile", "stack"), ("encoches", "fingers")):
        ps = core.Params(size_mm=100, output="halftone", shape="circle", box_style=sty, box_depth_mm=24, box_support="both", ring_mm=5)
        bs = lightbox.make_box(core.process(blank, ps), ps)
        m[f"support {nm} : pieces du pied"] = float(sum(pt["qty"] for pt in bs["parts"] if pt["name"].startswith("foot")))
        m[f"support {nm} : contours du fond"] = float(sum(len(pt["polys"]) for pt in bs["parts"] if pt["name"] == "back"))
        m[f"support {nm} : avertissements"] = float(len(bs["notes"]))
    pl = core.Params(size_mm=100, output="lines", shape="circle", line_pitch_mm=2.0, line_angle=0, line_break_mm=0)
    gradient = np.tile(np.linspace(0, 255, 400, dtype=np.uint8), (400, 1))
    rl = core.process(np.stack([gradient] * 3, -1), pl)
    m["lignes : fentes"] = float(rl.stats["holes"])
    m["lignes : pixels de matiere"] = float(rl.mat.sum())
    pq = core.Params(size_mm=100, output="lowpoly", shape="circle", lp_points=100, lp_style="wire", lp_beam_mm=1.5)
    rq = core.process(gradient3 := np.stack([gradient] * 3, -1), pq)
    m["low poly : maillage plausible"] = float(100 <= rq.stats.get("lp_triangles", 0) <= 400 and rq.stats["contours"] > 20)
    blank = np.full((800, 800, 3), 255, np.uint8)
    pe = core.Params(size_mm=100, output="qr", shape="rrect", qr_mode="engrave", qr_side_mm=50, qr_text="https://exemple.fr/menu")
    re_ = core.process(blank, pe)
    m["qr : gravé relu"] = float(re_.stats.get("qr_scan") == "ok")
    m["qr : ajouré relu"] = float(core.process(blank, core.Params(size_mm=100, output="qr", shape="rrect", qr_mode="cut",
                                  qr_side_mm=50, qr_text="https://exemple.fr/menu")).stats.get("qr_scan") == "ok")
    m["qr : calque ENGRAVE exporté"] = float("ENGRAVE" in core.dxf_string(re_.polys_mm, re_.h_mm, marks=re_.marks_polys)
                                            and 'id="ENGRAVE"' in core.svg_string(re_.polys_mm, re_.w_mm, re_.h_mm, None, re_.marks_polys))
    ml = core.process(np.dstack([np.tile(np.linspace(0, 255, 600, dtype=np.uint8), (600, 1))] * 3),
                      core.Params(size_mm=100, output="layers", shape="circle", ring_mm=6, ml_layers=4))
    m["multicouche : 4 plaques + repères"] = float(len(ml.layers) == 4 and ml.stats.get("ml_pins") == 3
                                                  and len(ml.layer_polys) == 4 and ml.stats["contours"] > 8)
    mc = core.process(np.dstack([np.tile(np.linspace(0, 255, 600, dtype=np.uint8), (600, 1))] * 3),
                      core.Params(size_mm=100, output="layers", shape="circle", ring_mm=6, ml_layers=3, ml_sep="color"))
    m["multicouche couleur : palette"] = float(len(mc.stats.get("ml_palette", [])) == 3 and len(mc.layer_colors) == 3
                                              and sorted(mc.stats.get("ml_order_ids", [])) == [0, 1, 2])
    mg = core.process(np.dstack([np.tile(np.linspace(0, 255, 600, dtype=np.uint8), (600, 1))] * 3),
                      core.Params(size_mm=100, output="layers", shape="circle", ring_mm=6, ml_layers=3, ml_sep="color",
                                  ml_bg="own", ml_engrave=True))
    _lg = np.zeros((120, 200, 3), np.uint8); _lg[:] = 255; _lg[30:90, 40:160] = (178, 58, 50)
    _lg = cv2.GaussianBlur(_lg, (0, 0), 1.2)
    _lr = core.layers_result(_lg, core.replace(core.Params(), output="layers", ml_sep="color", ml_layers=4))
    m["couleur auto : logo 2 plaques"] = float(len(_lr.layers) == 2)
    _lb = np.zeros((160, 160, 3), np.uint8); _lb[:] = (64, 108, 176); _lb[60:100, 30:130] = 255
    _lb = cv2.GaussianBlur(_lb, (0, 0), 1.0)
    _lq = core.layers_result(_lb, core.replace(core.Params(), output="layers", ml_sep="color", ml_layers=4))
    m["couleur : logo plein cadre (fond = couleur dominante)"] = float(
        len(_lq.layers) == 2 and _lq.stats.get("ml_palette", [""])[0].startswith("#3"))
    _li = np.zeros((200, 300, 3), np.uint8); _li[:] = (64, 108, 176); _li[90:110, 20:60] = 255; _li[90:110, 240:280] = 255
    _li = cv2.GaussianBlur(_li, (0, 0), 1.0)
    _lj = core.layers_result(_li, core.replace(core.Params(), output="layers", ml_sep="color", ml_layers=4, shape="none", size_mm=300, max_bridge_mm=2))
    m["couleur : îlots gardés (pièces libres)"] = float(len(_lj.layers) >= 2 and _lj.stats.get("ml_loose", 0) >= 1)
    _lp = core.layers_result(_lb, core.replace(core.Params(), output="layers", ml_sep="color", ml_layers=8,
                                               ml_picks="#4070b0,#ffffff,#ff0000"))
    m["couleur : pipette 3 couleurs"] = float(len(_lp.layers) == 3 and len(_lp.stats.get("ml_palette", [])) == 3)
    m["multicouche : fond à part + gravure"] = float(len(mg.layers) == 4 and len(mg.layer_colors) == 4
                                                    and mg.layer_colors[0] == (232, 220, 200))
    return m


def main():
    print(f"Python {sys.version.split()[0]} | OpenCV {cv2.__version__} | numpy {np.__version__} | scipy {scipy.__version__}")
    print(f"core.py version {getattr(core, 'VERSION', '?')}")
    import re as _re, os as _os
    _h = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "studio.html"), encoding="utf-8").read()
    _m = _re.search(r'UI_VERSION = "([0-9.]+)"', _h)
    if not _m or _m.group(1) != core.VERSION:
        print(f"ERREUR : studio.html est en version {_m.group(1) if _m else '?'} mais core.py en {core.VERSION}")
        sys.exit(1)
    m = measure()
    if "--record" in sys.argv:
        print("EXPECTED = {")
        for k, v in m.items():
            print(f"    {k!r}: {v:.3f},")
        print("}")
        return 0
    bad = 0
    print(f"{'test':42s} {'ce PC':>12s} {'attendu':>12s}  resultat")
    for k, v in m.items():
        e = EXPECTED.get(k)
        if e is None:
            print(f"{k:42s} {v:12.2f} {'?':>12s}  ?")
            continue
        tol = TOL["grabcut"] if "grabcut" in k else TOL["default"]
        diff = abs(v - e) / (abs(e) + 1e-9) * 100 if abs(e) > 1e-9 else abs(v - e)
        ok = (v == e) if e in (0.0, 1.0) else (diff <= tol or abs(v - e) <= 2)
        bad += 0 if ok else 1
        print(f"{k:42s} {v:12.2f} {e:12.2f}  {'OK' if ok else 'DIFF  <<<<'}")
    print("\n" + ("Tout est conforme." if bad == 0 else f"{bad} difference(s) : envoyer cette sortie complete."))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
