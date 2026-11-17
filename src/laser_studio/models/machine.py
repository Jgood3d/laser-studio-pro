"""Réglages de la machine : plateau, spot du laser, limites (page
« Paramètres du graveur »)."""
from laser_studio.models.settings import SettingsModel


class MachineConfig(SettingsModel):
    """Réglages physiques du graveur, mémorisés dans chaque profil machine.

    - bed_w, bed_h : largeur et profondeur du plateau (mm) ;
    - focal : taille du spot du laser (mm) ;
    - max_speed : vitesse maximale (mm/min) ; accel : accélération (mm/s²).

    Les noms des clés d'un profil machine enregistré (w, h, focal, max_speed,
    accel) sont repris par to_profile / PROFILE_KEYS.
    """

    LABEL = "Machine"
    FIELDS = {
        "bed_w": (float, 300.0),
        "bed_h": (float, 200.0),
        "focal": (float, 0.10),
        "max_speed": (float, 6000.0),
        "accel": (float, 500.0),
    }
    # Réglage -> clé dans un profil machine enregistré.
    PROFILE_KEYS = {"bed_w": "w", "bed_h": "h", "focal": "focal",
                    "max_speed": "max_speed", "accel": "accel"}

    def to_profile(self):
        """Réglages au format d'un profil machine enregistré."""
        return {key: self._values[name] for name, key in self.PROFILE_KEYS.items()}

    def apply_profile(self, profile):
        """Réapplique un profil machine enregistré. Plateau et spot absents :
        valeurs actuelles gardées ; vitesse et accélération absentes : valeurs
        par défaut (profil enregistré avant leur ajout)."""
        fields = {name: profile[key] for name, key in self.PROFILE_KEYS.items() if key in profile}
        for name in ("max_speed", "accel"):
            fields.setdefault(name, self.FIELDS[name][1])
        return self.update(**fields)
