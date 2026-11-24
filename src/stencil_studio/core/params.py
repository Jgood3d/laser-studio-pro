"""Réglages (Params) et résultat (Result) d'un pochoir, version du calcul.

Partie du calcul de Stencil Studio (voir core/__init__.py)."""

from dataclasses import asdict, dataclass, fields
import numpy as np


VERSION = "2026.11.86"  # doit être identique dans core/params.py et studio.html


REF_SIZE = 1200.0  # taille de référence : les réglages en pixels sont exprimés pour 1200 px


@dataclass
class Params:
    size_mm: float = 100.0        # taille finale (plus grand côté)
    output: str = "stencil"        # stencil (formes + ponts) | halftone (trame de points pour les photos)
    dot_pitch_mm: float = 1.6     # halftone : pas de la trame
    min_web_mm: float = 0.5       # halftone : matière minimale entre deux trous
    min_dot_mm: float = 0.35      # halftone : plus petit trou découpé (en dessous : zone pleine)
    dot_angle: float = 45.0       # halftone : angle de la trame (degrés)
    dot_gamma: float = 1.0        # halftone : courbe des tons (>1 = plus de matière)
    dot_contrast: float = 0.8     # halftone : 0 = niveaux étalés ; 1 = histogramme égalisé (contraste maximal)
    dot_detail: float = 1.5       # halftone : renforcement du détail local (0 = aucun)
    shape: str = "circle"         # circle | rect | none
    ring_mm: float = 4.0          # largeur de l'anneau extérieur
    bridge_mm: float = 1.5        # largeur des ponts
    max_bridge_mm: float = 8.0    # îlot plus loin : supprimé
    min_island_mm2: float = 10.0  # îlot plus petit : supprimé
    min_feature_mm: float = 0.8   # plus petit détail découpable
    keep_thin: bool = True        # épaissir les traits fins au lieu de les supprimer
    grow_mm: float = 0.0          # épaisseur des traits : + épaissit, - amincit (variation de largeur totale)
    mode: str = "local"           # local | global
    tone_source: str = "luminance" # luminance | darkest | mix
    auto_threshold: bool = True
    threshold: float = 128.0
    bias: float = 0.0
    texture: float = 1.0          # passes de lissage des textures (0 = aucun)
    outline_mm: float = 1.0       # trait plein le long du contour du sujet (si sujet isolé)
    blur: float = 1.5             # px à 1200 px
    contrast: bool = True
    invert: bool = False
    local_contrast: float = 10.0
    local_size: float = 0.125     # fraction de l'image
    dark_offset: float = 90.0
    smooth: float = 2.0           # px à 1200 px
    simplify: float = 0.8         # px à 1200 px
    hang: str = "none"            # accroche : none | top | top_left | top_right | both
    hang_style: str = "round"     # round | drop
    hang_hole_mm: float = 3.0     # diamètre du trou d'accroche
    hang_tab_mm: float = 2.5      # matière autour du trou
    text_top: str = ""            # texte courbe dans l'anneau (haut)
    text_bottom: str = ""         # texte courbe dans l'anneau (bas)
    text_size_mm: float = 6.0     # hauteur des majuscules
    text_spacing: float = 12.0    # espace entre lettres (% de la hauteur)
    text_bridge_mm: float = 0.7   # largeur des ponts dans les lettres (centres de A, O, B...)
    font: str = ""                # chemin d'une police .ttf (vide = police fournie)
    eng_dpi: float = 195.0        # gravure : résolution de la machine (points par pouce)
    eng_dither: str = "stucki"    # stucki | floyd | atkinson | jarvis | burkes | sierra | bayer | threshold
    eng_levels: int = 2           # 2 = noir / blanc ; 3 et plus = niveaux de gris (puissances différentes)
    eng_brightness: float = 0.0   # -100..100
    eng_contrast: float = 0.0     # -90..90
    eng_gamma: float = 1.0        # > 1 = plus clair
    eng_sharpen: float = 1.0      # netteté (0 = aucune)
    eng_invert: bool = False      # graver les zones claires (matière sombre qui s'éclaircit)
    eng_border_mm: float = 1.0    # marge sans gravure le long du bord de la pièce
    eng_speed: float = 5500.0     # mm/min, pour l'estimation de durée
    box_depth_mm: float = 25.0    # caisson lumineux : profondeur intérieure
    box_thickness_mm: float = 3.0 # épaisseur du matériau des cadres
    box_wall_mm: float = 10.0     # largeur de paroi
    box_screws: int = 4           # vis du fond (0 = collé)
    box_screw_mm: float = 3.0     # diamètre de vis (M3)
    export_frame: bool = False   # ajoute un rectangle de cadrage (calque FRAME / Marquage) aux exports SVG et DXF
    box_support: str = "none"    # none | foot | wall | both : pied et/ou trous de serrure dans le fond
    box_foot_h: float = 9.0       # profondeur de la rainure du pied (mm)
    box_key_head: float = 8.0     # diamètre de la tête de vis pour la fixation murale (mm)
    box_key_shank: float = 4.0    # diamètre de la tige de vis (mm)
    box_center_mm: float = 0.0    # trou rond au centre du fond (diamètre, 0 = aucun)
    box_cable_mm: float = 8.0     # trou de câble dans le fond (0 = aucun)
    box_diffuser: bool = True     # plaque diffusante entre façade et cadres
    box_sheet_w: float = 400.0    # largeur de la plaque à découper (mise en page)
    box_gap_mm: float = 4.0       # espace entre pièces
    box_style: str = "stack"      # stack (cadres collés) | fingers (parois à encoches, flexibles sur les courbes)
    box_rib_mm: float = 2.54  # fingers : écart entre deux lignes de coupe de la paroi flexible (= largeur d'une nervure)
    box_end_mm: float = 2.7    # fingers : distance des fentes centrales aux bords haut / bas
    box_fit_auto: bool = True     # fingers : jeu des languettes ajusté à la courbure
    box_tab_solid: bool = False   # fingers : languettes pleines (non traversées par les fentes de flexion)
    box_mid_mm: float = 6.0  # fingers : pont de matière au milieu entre cellules
    box_wall_parts: int = 1       # fingers : nombre de morceaux de la paroi courbe (1 à 3)
    box_fit_mm: float = 0.1       # fingers : jeu des fentes (colle)
    box_lip_mm: float = 1.5       # fingers : débord de la façade et du fond autour de la paroi
    line_pitch_mm: float = 1.5    # lignes : écart entre deux lignes
    line_angle: float = 30.0      # lignes : angle (degrés)
    lp_points: int = 200          # low poly : nombre approximatif de sommets du maillage
    lp_beam_mm: float = 1.4       # low poly : largeur des arêtes (poutres) en mm
    lp_style: str = "solid"       # low poly : wire (arêtes seules) | solid (facettes sombres pleines) | shade (trou de chaque facette selon le ton)
    lp_geo: bool = False          # low poly : style géométrique (silhouette en polygone, peu de sommets, taches sombres en facettes)
    lp_simplify: float = 1.2      # low poly géométrique : simplification de la silhouette (% de la taille)
    ml_layers: int = 4            # multicouche : nombre de plaques empilées (la 1re = fond plein)
    ml_invert: bool = False       # multicouche : les zones claires sont les plus profondes (au lieu des sombres)
    ml_sep: str = "tone"          # multicouche : tone (par luminosité) | color (une plaque par couleur dominante)
    ml_order: str = ""            # multicouche couleur : ordre des couleurs de l'arrière vers l'avant (indices séparés par des virgules)
    ml_bg: str = "front"          # multicouche : fond de l'image = couleur de la plaque de devant (front) | plaque de fond à part (own)
    ml_bg_color: str = "#e8dcc8"  # multicouche : couleur de la plaque de fond à part (aperçu et export)
    ml_engrave: bool = False      # multicouche : graver les détails (visages...) sur la plaque de devant (calque ENGRAVE)
    ml_eng_level: float = 50.0    # multicouche : sensibilité de la gravure des détails (0 à 100)
    ml_pins: bool = True          # multicouche : 3 trous de repérage identiques dans la bordure de chaque couche
    ml_pin_mm: float = 3.0        # diamètre des trous de repérage (tourillons / vis)
    ml_picks: str = ""            # multicouche couleur : couleurs choisies à la pipette (#rrggbb séparés par des virgules)
    ml_color_auto: bool = True    # multicouche couleur : nombre de couleurs détecté automatiquement (ml_layers = maximum)
    ml_pieces: bool = False       # multicouche : plaques de dessus = pièces libres à coller (aucun pont)
    ml_mid_loose: bool = True     # multicouche : plaques intermédiaires = pièces libres (collées sur la plaque pleine derrière) : aucun pont visible entre les couleurs
    keep_islands: bool = False    # interne : les îlots non reliés sont gardés comme pièces libres (au lieu d'être supprimés)
    loose: bool = False           # interne : pas de ponts (pièces libres)
    ml_gap_mm: float = 6.0        # espace entre couches sur la planche de découpe
    qr_kind: str = "text"         # qr : text (lien, texte...) | wifi
    qr_text: str = "https://exemple.fr"
    qr_ssid: str = ""
    qr_pass: str = ""
    qr_sec: str = "WPA"           # WPA | WEP | nopass
    qr_ec: str = "Q"              # correction d'erreur : L | M | Q | H
    qr_mode: str = "engrave"      # engrave (modules gravés sur la plaque) | cut (modules ajourés, avec ponts)
    qr_side_mm: float = 40.0      # côté du code (sans la marge)
    qr_invert: bool = False       # polarité inversée (graver les modules clairs / ajourer les modules sombres)
    qr_bridge_mm: float = 0.5     # largeur des ponts du mode ajouré
    ai_subject: bool = True       # détecte le sujet par réseau de neurones si onnxruntime est installé (sinon méthode classique)
    lp_auto: bool = True          # low poly : détecte le sujet tout seul si le fond est uni
    lp_level: float = 0.0         # low poly (solid) : décalage du seuil clair/sombre (+ = plus de facettes pleines)
    lp_focus: float = 0.35         # low poly : 0 = sommets uniformes, 1 = très serrés sur les détails
    lp_seed: int = 1              # low poly : variante du semis de sommets
    line_break_mm: float = 30.0   # lignes : longueur max d'une fente avant un pont (0 = fentes continues)

    @classmethod
    def unknown_keys(cls, d):
        """Réglages reçus que cette version de core.py ne connaît pas."""
        names = {f.name for f in fields(cls)}
        return sorted(k for k in (d or {}) if k not in names)

    @classmethod
    def from_dict(cls, d):
        names = {f.name: f.type for f in fields(cls)}
        out = {}
        for k, v in (d or {}).items():
            if k in names:
                out[k] = v
        return cls(**out)

    def to_dict(self):
        return asdict(self)


@dataclass
class Result:
    rgb: np.ndarray
    gray: np.ndarray
    subject: object
    mat0: np.ndarray       # matière après nettoyage (avant forme + ponts)
    mat: np.ndarray        # matière finale
    bridges: np.ndarray
    polys_mm: list
    w_mm: float
    h_mm: float
    stats: dict
    sheet: object = None   # masque 1 = plaque présente (hors plaque : fond)
    engrave: object = None  # gravure : image tramée (uint8, 0 = brûlé) à la résolution de la machine
    eng_dpi: float = 0.0
    tab: object = None      # zone de l'œillet (masque, repère agrandi)
    hang_holes: object = None  # trous d'accroche [(x_mm, y_mm, r_mm)]
    base_sheet: object = None  # masque de la forme sans la languette d'accroche
    marks: object = None       # qr : masque des zones gravées (modules)
    marks_polys: object = None  # qr : contours (mm) des zones gravées, pour le calque ENGRAVE
    layers: object = None       # multicouche : matière (masque) de chaque couche, taille d'une tuile
    layer_colors: object = None  # multicouche couleur : (r, g, b) de chaque plaque
    layer_boxes: object = None   # multicouche : (x0, y0, w, h) de chaque tuile sur la planche
    layer_polys: object = None  # multicouche : [(nom, contours mm)] sur la planche de découpe
