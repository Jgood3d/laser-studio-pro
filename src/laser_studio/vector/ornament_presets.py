"""Modèles prédéfinis de boules de Noël (galerie du générateur), sans Qt.

Un modèle n'est qu'un jeu de réglages du générateur : motif, disposition, bande du prénom, remplissage, bois de
renne… Il ne touche ni au diamètre, ni à la largeur de l'anneau, ni au prénom, à la police ou aux calques : ce sont
ceux de l'utilisateur. Appliquer un modèle, c'est donc recopier ces réglages dans le formulaire, qui reste
entièrement modifiable ensuite.

`key` sert aussi de clé de traduction : `ornament.preset.<key>`.
"""
from __future__ import annotations

from typing import Dict, List, NamedTuple


class Preset(NamedTuple):
    key: str
    settings: Dict[str, object]


# Réglages communs : on repart toujours d'une base neutre pour qu'un modèle n'hérite rien du précédent.
BASE: Dict[str, object] = {
    "motif": "Aucun", "flake_layout": "Haut et bas", "flake_style": None, "flake_count": 3, "flake_size": 16.0,
    "motif_drop": 0.0, "name_mode": "Gravé", "support": "Barre", "band_height": 0.0, "band_frame": True,
    "crown": "Aucune", "fill": "Aucun", "fill_zone": "Haut et bas", "fill_pitch": 6.0, "hanger": "Anneau",
    "name_offset": None, "name_size": 0.0,
}


def _p(key, **kw) -> Preset:
    settings = dict(BASE)
    settings.update(kw)
    return Preset(key, settings)


PRESETS: List[Preset] = [
    # Prénom gravé sur une bande, motifs autour
    _p("flakes_opposed", motif="Flocons", flake_layout="Haut et bas", flake_count=2, flake_size=17.0),
    _p("flake_below", motif="Flocons", flake_layout="Bas", flake_count=1, flake_size=34.0),
    _p("flake_below_lace", motif="Flocons", flake_layout="Bas", flake_style="Dentelle", flake_count=1, flake_size=32.0),
    _p("flake_above", motif="Flocons", flake_layout="Haut", flake_count=1, flake_size=32.0),
    _p("flakes_hanging", motif="Flocons", flake_layout="Suspendus", flake_count=3, flake_size=14.0),
    _p("stars_band", motif="Étoiles", flake_layout="Haut et bas", flake_count=2, flake_size=13.0),
    _p("tree_band", motif="Sapins", flake_layout="Haut", flake_count=1, flake_size=26.0),
    _p("santa_band", motif="Père Noël", flake_layout="Haut", flake_count=1, flake_size=30.0),
    _p("snowman_band", motif="Bonhomme de neige", flake_layout="Bas", flake_count=1, flake_size=26.0),
    _p("holly_band", motif="Houx", flake_layout="Haut", flake_count=2, flake_size=18.0),
    _p("bells_band", motif="Cloche", flake_layout="Haut", flake_count=2, flake_size=18.0),
    _p("gifts_band", motif="Cadeaux", flake_layout="Bas", flake_count=3, flake_size=17.0),
    _p("candles_band", motif="Bougie", flake_layout="Bas", flake_count=3, flake_size=22.0),
    _p("moon_band", motif="Lune", flake_layout="Haut", flake_count=1, flake_size=20.0),
    _p("garland_band", motif="Guirlande", flake_layout="Haut", flake_count=5, flake_size=10.0),
    # Remplissages à motif
    _p("stripes_band", fill="Rayures", fill_pitch=7.0),
    _p("lattice_band", fill="Treillis", fill_pitch=8.0, hanger="Capuchon"),
    _p("knit_band", fill="Tricot", fill_pitch=6.0, hanger="Capuchon"),
    _p("waves_band", fill="Vagues", fill_pitch=7.0),
    _p("leaves_band", fill="Feuilles", fill_pitch=6.0),
    _p("leaves_top", fill="Feuilles", fill_zone="Haut", fill_pitch=6.0),
    # Reno
    _p("reindeer_band", crown="Bois de renne", band_height=0.0),
    # Prénom découpé et lié à l'anneau (comme avant)
    _p("cut_flakes", motif="Flocons", flake_layout="Suspendus", flake_count=3, flake_size=16.0, name_mode="Découpé",
       band_frame=False),
    _p("cut_name_bar", motif="Aucun", name_mode="Découpé", support="Barre", band_frame=False),
    _p("cut_tree_bandeau", motif="Sapins", flake_layout="Haut", flake_count=1, flake_size=22.0, name_mode="Découpé",
       support="Bandeau", band_frame=False),
]

BY_KEY = {p.key: p for p in PRESETS}

# Réglages qu'un modèle peut poser : tout le reste du formulaire reste à l'utilisateur.
SETTING_KEYS = tuple(BASE)
