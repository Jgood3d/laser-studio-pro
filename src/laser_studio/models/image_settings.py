"""Réglages de tramage de l'onglet « Graver une image » : luminosité,
contraste, gamma, netteté, effet bande dessinée, négatif, matière, miroirs, algorithme ; et leur
historique d'annulation propre à l'onglet (Ctrl+Z / Ctrl+Y).

    settings = ImageSettings(window)
    history = ImageSettingsHistory(settings)
    settings.update(brightness=20)      # signal changed({"brightness": 20})
    history.undo()                      # luminosité revenue à 0

Les champs de l'onglet y sont liés par ui/binding.py ; la logique (tramage,
génération, projets, séparation) lit le modèle, plus les widgets.
"""
import time

from laser_studio.models.settings import SettingsModel

DEFAULT_ALGORITHM = "Floyd-Steinberg"

# Réglage du modèle -> clé dans un projet enregistré et dans les paramètres
# du traitement (ImageProcessingWorker).
PROJECT_KEYS = {
    "brightness": "bright",
    "contrast": "contrast",
    "gamma": "gamma",
    "sharpness": "sharp",
    "cartoon_radius": "cartoon_r",
    "cartoon_black": "cartoon_k",
    "invert": "invert",
    "material_bg": "material_bg",
    "mirror_h": "mirror_h",
    "mirror_v": "mirror_v",
    "algorithm": "algo",
}


class ImageSettings(SettingsModel):
    """Réglages du tramage.

    - brightness, contrast : -100 à 100 ; gamma : × 100 (100 = 1,0) ;
      sharpness : 0 à 100 ;
    - cartoon_radius : rayon du masque de l'effet bande dessinée, en dixièmes
      de mm (0 = pas d'effet, 50 = 5 mm) ; cartoon_black : pourcentage de noir
      (0 à 100) ;
    - invert : négatif ; material_bg : "dark" (fond noir) ou "light" (fond
      clair) ; choisir une matière coche ou décoche le négatif (voir
      choose_material), qui reste modifiable à part ;
    - mirror_h, mirror_v : miroirs ;
    - algorithm : nom de l'algorithme de tramage (liste de l'onglet).
    """

    LABEL = "Image"
    FIELDS = {
        "brightness": (int, 0),
        "contrast": (int, 0),
        "gamma": (int, 100),
        "sharpness": (int, 0),
        "cartoon_radius": (int, 0),
        "cartoon_black": (int, 20),
        "invert": (bool, False),
        "material_bg": (str, "light"),
        "mirror_h": (bool, False),
        "mirror_v": (bool, False),
        "algorithm": (str, DEFAULT_ALGORITHM),
    }
    CHOICES = {"material_bg": ("dark", "light")}

    def choose_material(self, material_bg):
        """Matière choisie par l'utilisateur : fond noir -> négatif activé
        (le laser éclaircit ce qu'il brûle), fond clair -> négatif
        désactivé. Le miroir n'est pas touché."""
        return self.update(material_bg=material_bg, invert=(material_bg == "dark"))

    def reset(self, keep_algorithm=True):
        """Réglages par défaut (bouton « Réinitialiser ») ; l'algorithme est
        gardé, sauf si `keep_algorithm` est faux."""
        defaults = {name: default for name, (_cast, default) in self.FIELDS.items()}
        if keep_algorithm:
            defaults.pop("algorithm")
        return self.update(**defaults)

    def processing_params(self):
        """Réglages au format des paramètres de ImageProcessingWorker
        (bright, contrast, gamma, sharp, cartoon_r, cartoon_k, invert, mirror_h, mirror_v, algo)."""
        return {key: self._values[name] for name, key in PROJECT_KEYS.items()
                if name != "material_bg"}

    def to_project(self):
        """Réglages au format d'un projet enregistré."""
        return {key: self._values[name] for name, key in PROJECT_KEYS.items()}

    def load_project(self, data):
        """Réapplique les réglages d'un projet ; une clé absente (ancien
        projet) prend sa valeur par défaut. Sans « material_bg », la matière
        est déduite du négatif enregistré."""
        fields = {name: data.get(key, self.FIELDS[name][1]) for name, key in PROJECT_KEYS.items()}
        if "material_bg" not in data:
            fields["material_bg"] = "dark" if data.get("invert", False) else "light"
        return self.update(**fields)


class ImageSettingsHistory:
    """Annuler / refaire les réglages de tramage.

    Chaque changement du modèle empile l'état d'avant. Les changements
    rapprochés (moins de GROUP_DELAY_S : glissement continu d'un curseur)
    forment une seule étape, sinon défaire un glissement demanderait des
    dizaines de Ctrl+Z. MAX_STEPS étapes au plus de chaque côté.
    """

    GROUP_DELAY_S = 0.6
    MAX_STEPS = 30

    def __init__(self, settings, clock=time.monotonic):
        self._settings = settings
        self._clock = clock
        self._undo = []
        self._redo = []
        self._last = settings.to_dict()
        self._last_push = None
        self._applying = False
        settings.changed.connect(self._on_changed)

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def _on_changed(self, _changes):
        current = self._settings.to_dict()
        if not self._applying and current != self._last:
            now = self._clock()
            if self._last_push is None or now - self._last_push > self.GROUP_DELAY_S or not self._undo:
                self._push(self._undo, self._last)
                self._redo.clear()
            self._last_push = now
        self._last = current

    def _push(self, stack, state):
        stack.append(state)
        if len(stack) > self.MAX_STEPS:
            stack.pop(0)

    def _apply(self, state):
        self._applying = True
        try:
            self._settings.update(**state)
        finally:
            self._applying = False
        self._last = self._settings.to_dict()
        self._last_push = None

    def undo(self):
        """Revient à l'état d'avant le dernier changement. Faux si rien à annuler."""
        if not self._undo:
            return False
        self._push(self._redo, self._settings.to_dict())
        self._apply(self._undo.pop())
        return True

    def redo(self):
        """Refait le dernier changement annulé. Faux si rien à refaire."""
        if not self._redo:
            return False
        self._push(self._undo, self._settings.to_dict())
        self._apply(self._redo.pop())
        return True
