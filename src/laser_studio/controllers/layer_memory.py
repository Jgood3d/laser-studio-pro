"""Mémoire des calques par machine : réglages (vitesse, puissance,
passes...) enregistrés dans chaque profil machine et réappliqués au modèle
des calques (models/layers.py)."""

from laser_studio.models.layers import validated_settings

# Réglages repris d'un profil machine quand on CHANGE de machine en cours de
# session (le nom, la couleur et l'identité des calques ne bougent pas : les
# objets du canevas y sont rattachés par identifiant), avec leur type.
LAYER_SETTING_CASTS = (
    ("mode", str),
    ("power", float),
    ("speed", int),
    ("passes", int),
    ("line_interval", float),
    ("line_interval_linked", bool),
    ("enabled", bool),
)


def coerce_layer_settings(layer, source, reset_invalid=False):
    """Copie les réglages de `source` (dictionnaire) vers `layer` en forçant
    le bon type, SANS passer par le modèle (aucun signal) : réservé à un
    calque isolé. Pour un calque du modèle, utiliser
    `layers.update(layer.id, **settings_from(source))`.

    Une valeur inutilisable est ignorée (le calque garde sa valeur) ; avec
    reset_invalid=True, elle est remplacée par la valeur par défaut d'un
    calque neuf.
    """
    defaults = type(layer)() if reset_invalid else None
    for key, value in settings_from(source, defaults).items():
        setattr(layer, key, value)


def settings_from(source, defaults=None):
    """Réglages de LAYER_SETTING_CASTS présents dans `source`, convertis dans
    leur type (voir models.layers.validated_settings)."""
    keys = {key for key, _cast in LAYER_SETTING_CASTS}
    return validated_settings({k: v for k, v in source.items() if k in keys}, defaults)


def apply_saved_layers(layer_manager, saved_layers, full=False):
    """Applique les calques mémorisés dans un profil machine. Renvoie True
    s'il y en avait (False : rien n'a changé).

    full=True (démarrage) : remplace entièrement la liste des calques
    (LayersModel.load_list, qui remplace les valeurs corrompues).
    full=False (changement de machine en cours de session) : ne reprend que
    les réglages, appliqués aux calques existants, retrouvés par
    identifiant puis, à défaut, par position. Les calques ne sont ni
    ajoutés, ni supprimés, ni renommés : sinon des objets du canevas
    perdraient leur calque et ne seraient plus gravés. Un profil sans
    calques mémorisés (ancien profil) ne change rien.
    """
    if not saved_layers or not isinstance(saved_layers, list):
        return False
    saved_layers = [d for d in saved_layers if isinstance(d, dict)]
    if not saved_layers:
        return False
    if full:
        layer_manager.load_list(saved_layers)
    else:
        by_id = {d.get("id"): d for d in saved_layers}
        for i, layer in enumerate(list(layer_manager.layers)):
            d = by_id.get(layer.id) or (
                saved_layers[i] if i < len(saved_layers) else None
            )
            if d:
                layer_manager.update(layer.id, **settings_from(d))
    return True
