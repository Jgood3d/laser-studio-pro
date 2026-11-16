"""Configuration GRBL : commande laser, puissance maximale, homing,
surbalayage, décalage aller/retour, G-Code de début et de fin, réglages $$
(page « Configuration GRBL »)."""
from laser_studio.models.settings import SettingsModel

LASER_COMMANDS = ("M4", "M3")          # dans l'ordre de la liste de la page
OVERSCAN_FIXED, OVERSCAN_PERCENT = 0, 1

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
        "safe_cut_order": (bool, True),
        "start_gcode": (str, DEFAULT_START_GCODE),
        "end_gcode": (str, DEFAULT_END_GCODE),
        "grbl_settings": (str, ""),
    }
    CHOICES = {
        "laser_cmd": LASER_COMMANDS,
        "overscan_mode": (OVERSCAN_FIXED, OVERSCAN_PERCENT),
    }
