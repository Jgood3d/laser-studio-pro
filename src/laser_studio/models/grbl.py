"""Configuration GRBL : commande laser, puissance maximale, homing,
surbalayage, décalage aller/retour, G-Code de début et de fin, réglages $$
(page « Configuration GRBL »)."""
from laser_studio.models.settings import SettingsModel

LASER_COMMANDS = ("M4", "M3")          # dans l'ordre de la liste de la page
OVERSCAN_FIXED, OVERSCAN_PERCENT = 0, 1
ROTARY_AXES = ("Y", "A")               # axe du rotatif : Y (à la place de Y) ou A (axe dédié, en degrés)
ROTARY_DRIVES = ("chuck", "roller")    # mandrin ou rouleaux

DEFAULT_START_GCODE = "G21 ; Unités mm\nG90 ; Absolu"
DEFAULT_END_GCODE = "M5 ; Extinction Laser\nG0 X0 Y0 ; Retour origine"


class GrblConfig(SettingsModel):
    """Réglages de la commande du graveur, mémorisés dans chaque profil
    machine (les réglages mécaniques : homing, surbalayage, décalage, en
    continu ; le reste quand le profil est mis à jour).

    - laser_cmd : "M4" (puissance dynamique) ou "M3" (constante) ;
    - smax : valeur S de la puissance maximale ($30) ;
    - homing_enabled : « Inclure $H » au début du job ;
    - overscan_enabled, overscan_mode (OVERSCAN_FIXED / OVERSCAN_PERCENT),
      overscan_dist_mm, overscan_pct : surbalayage ;
    - scan_offset_mm : décalage des lignes retour ;
    - safe_cut_order : découpe des formes intérieures d'abord ;
    - rotary_enabled, rotary_axis, rotary_drive, rotary_object_mm, rotary_roller_mm, rotary_mm_per_turn :
      axe rotatif (voir gcode/rotary.py) ; `rotary_enabled` n'est PAS enregistré dans les profils : il
      reste décoché à chaque démarrage, pour ne jamais lancer un job à plat avec le rotatif par erreur ;
    - start_gcode, end_gcode : G-Code ajouté au début et à la fin du job ;
    - grbl_settings : texte des réglages GRBL complets ($$).
    """

    LABEL = "GRBL"
    FIELDS = {
        "laser_cmd": (str, "M4"),
        "smax": (int, 1000),
        "homing_enabled": (bool, True),
        "overscan_enabled": (bool, True),
        "overscan_mode": (int, OVERSCAN_FIXED),
        "overscan_dist_mm": (float, 2.5),
        "overscan_pct": (float, 5.0),
        "scan_offset_mm": (float, 0.0),
        # Puissance du laser pendant le cadrage, en % du S-Max : assez pour voir le point sans marquer. Certaines
        # diodes ne s'allument qu'à partir de 1 ou 2 % ; 0 : cadrage laser éteint.
        "frame_power_pct": (float, 0.5),
        "safe_cut_order": (bool, True),
        "start_gcode": (str, DEFAULT_START_GCODE),
        "end_gcode": (str, DEFAULT_END_GCODE),
        "grbl_settings": (str, ""),
        "rotary_enabled": (bool, False),
        "rotary_axis": (str, "Y"),
        "rotary_drive": (str, "chuck"),
        "rotary_object_mm": (float, 60.0),
        "rotary_roller_mm": (float, 20.0),
        "rotary_mm_per_turn": (float, 360.0),
    }
    TYPED_FIELDS = ("start_gcode", "end_gcode", "grbl_settings")
    CHOICES = {
        "laser_cmd": LASER_COMMANDS,
        "overscan_mode": (OVERSCAN_FIXED, OVERSCAN_PERCENT),
        "rotary_axis": ROTARY_AXES,
        "rotary_drive": ROTARY_DRIVES,
    }

    # Réglages propres à la mécanique de la machine, mémorisés EN CONTINU
    # dans son profil (voir MachineProfilesController.store_memory). Le mode
    # du surbalayage est enregistré par son code (0 = distance fixe,
    # 1 = pourcentage).
    MECHANICAL_FIELDS = ("homing_enabled", "scan_offset_mm", "overscan_enabled",
                         "overscan_mode", "overscan_dist_mm", "overscan_pct", "frame_power_pct",
                         "rotary_axis", "rotary_drive", "rotary_object_mm", "rotary_roller_mm",
                         "rotary_mm_per_turn")
    # Enregistrés quand le profil est mis à jour (« Mettre à jour »).
    PROFILE_FIELDS = ("start_gcode", "end_gcode", "grbl_settings") + MECHANICAL_FIELDS

    def to_project(self):
        """Réglages enregistrés dans un projet : l'ordre de découpe sûr (le reste suit le profil machine)."""
        return {"safe_cut_order": self.safe_cut_order}

    def load_project(self, data):
        """Réapplique les réglages d'un projet ; absent (ancien projet) : ordre sûr, la valeur par défaut."""
        return self.update(safe_cut_order=data.get("safe_cut_order", True))

    def mechanical_values(self):
        """Réglages mécaniques, au format d'un profil machine."""
        return {name: self._values[name] for name in self.MECHANICAL_FIELDS}

    def to_profile(self):
        """Réglages enregistrés dans un profil machine : G-Code de début et de
        fin, réglages GRBL complets ($$) et réglages mécaniques."""
        return {name: self._values[name] for name in self.PROFILE_FIELDS}

    def apply_profile(self, profile):
        """Réapplique un profil machine enregistré. Un réglage absent (profil
        enregistré avant son ajout) garde sa valeur, sauf le décalage
        aller/retour qui revient à 0 ; une valeur illisible est ignorée (un
        décalage illisible revient à 0). Les réglages GRBL ne sont jamais
        envoyés à la machine ici. Renvoie ce qui a changé."""
        fields = {name: profile[name] for name in self.PROFILE_FIELDS
                  if name in profile and name not in ("overscan_mode", "scan_offset_mm")}
        if profile.get("overscan_mode") in self.CHOICES["overscan_mode"]:
            fields["overscan_mode"] = profile["overscan_mode"]
        try:
            fields["scan_offset_mm"] = float(profile.get("scan_offset_mm", 0.0))
        except (TypeError, ValueError):
            fields["scan_offset_mm"] = 0.0
        return self.update(**fields)
