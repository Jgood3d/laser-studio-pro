"""Placement du job sur le plateau : taille de l'image, décalage, origine du repère, résolution de la gravure et
réordonnancement des tracés. Les champs de l'interface y sont liés (ui/binding.py) ; la génération, le cadrage,
les projets et les profils machine le lisent ici, jamais dans les widgets.

    placement = JobPlacement()
    placement.update(offset_x=5.0)
    params = JobParams(**placement.geometry(), ...)
"""
from laser_studio.core.constants import ORIGIN_BOTTOM_LEFT, ORIGIN_CENTER
from laser_studio.i18n import TRANSLATIONS
from laser_studio.models.settings import SettingsModel

# Libellé enregistré par une ancienne version (texte affiché, dans n'importe quelle langue) -> code de l'origine.
_ORIGIN_LABEL_KEYS = {ORIGIN_BOTTOM_LEFT: "ui.origin_bottom_left", ORIGIN_CENTER: "ui.origin_center"}


def normalize_origin(value):
    """Code de l'origine (ORIGIN_BOTTOM_LEFT ou ORIGIN_CENTER) pour un code ou un ancien libellé traduit ;
    None si la valeur n'est pas reconnue."""
    for code, key in _ORIGIN_LABEL_KEYS.items():
        if value == code or value in TRANSLATIONS[key].values():
            return code
    return None


class JobPlacement(SettingsModel):
    """Où et comment le job se place sur le plateau.

    - width_mm, height_mm : taille de l'image à graver (mm) ;
    - origin : origine du repère, ORIGIN_BOTTOM_LEFT ou ORIGIN_CENTER ;
    - offset_x, offset_y : décalage du job par rapport à l'origine (mm) ;
    - lines_mm : résolution de la gravure (lignes/mm) ;
    - optimize_path : réordonner les tracés vectoriels pour réduire les déplacements à vide.
    """

    LABEL = "Placement du job"
    FIELDS = {
        "width_mm": (float, 100.0),
        "height_mm": (float, 100.0),
        "origin": (str, ORIGIN_BOTTOM_LEFT),
        "offset_x": (float, 0.0),
        "offset_y": (float, 0.0),
        "lines_mm": (float, 10.0),
        "optimize_path": (bool, True),
    }
    CHOICES = {"origin": (ORIGIN_BOTTOM_LEFT, ORIGIN_CENTER)}
    # Réglage -> clé dans un projet enregistré.
    PROJECT_KEYS = {"width_mm": "w_mm", "height_mm": "h_mm", "origin": "origin_pos",
                    "offset_x": "offset_x", "offset_y": "offset_y", "lines_mm": "lmm"}

    def geometry(self):
        """Taille et position du job, au format de JobParams."""
        v = self._values
        return {"width_mm": v["width_mm"], "height_mm": v["height_mm"], "origin_pos": v["origin"],
                "offset_x": v["offset_x"], "offset_y": v["offset_y"]}

    def to_project(self):
        """Réglages au format d'un projet enregistré."""
        return {key: self._values[name] for name, key in self.PROJECT_KEYS.items()}

    def load_project(self, data):
        """Réapplique un projet ; une clé absente (ancien projet) prend sa valeur par défaut, une origine
        illisible garde la valeur actuelle."""
        fields = {name: data.get(key, self.FIELDS[name][1]) for name, key in self.PROJECT_KEYS.items()}
        fields["origin"] = normalize_origin(fields["origin"]) or self.origin
        return self.update(**fields)

    def to_profile(self):
        """Origine du repère, enregistrée dans un profil machine."""
        return {"origin": self.origin}

    def apply_profile(self, profile):
        """Réapplique l'origine d'un profil, si elle est reconnue."""
        origin = normalize_origin(profile.get("origin"))
        return self.update(origin=origin) if origin else {}
