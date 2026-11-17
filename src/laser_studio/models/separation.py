"""Réglages de l'onglet « Séparation Couleur / Verre » : plaque de verre,
résolution d'impression, calque noir (gain de point), calque couleur et
simulation du rétro-éclairage. Les champs de l'onglet y sont liés
(ui/binding.py) ; le cadrage (recadrage, zoom, décalage) reste lu dans
l'onglet (SeparationTab.frame_args), qui combine plusieurs champs."""
from laser_studio.models.settings import SettingsModel


class SeparationSettings(SettingsModel):
    """- plate_w, plate_h : taille de la plaque de verre (mm) ;
    - print_dpi : résolution du calque couleur imprimé ;
    - gain : gain de point du calque noir (0 à 20, en %) ;
    - saturation, lightness : calque couleur (%, 100 = inchangé ; valeurs
      par défaut : celles du support « film transparent ») ;
    - mirror_print : calque couleur imprimé en miroir ;
    - diffusion, intensity : simulation du rétro-éclairage (diffusion de la
      lumière en centièmes de mm, intensité en %).
    """

    LABEL = "Séparation"
    FIELDS = {
        "plate_w": (float, 150.0),
        "plate_h": (float, 100.0),
        "print_dpi": (int, 300),
        "gain": (int, 0),
        "saturation": (int, 140),
        "lightness": (int, 100),
        "mirror_print": (bool, False),
        "diffusion": (int, 15),
        "intensity": (int, 100),
    }
