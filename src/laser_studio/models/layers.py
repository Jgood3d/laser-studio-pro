"""Modèle des calques : la liste ordonnée des LaserLayer et leurs réglages.

Toute modification passe par LayersModel (update, add_layer, remove_layer,
move_layer, load_list), qui émet le signal correspondant puis `changed`.
Les vues (tableau des calques, canevas) et la génération lisent le modèle :
il n'existe plus de copie des réglages ailleurs (ex. l'ancienne puissance de
gravure image, recopiée dans la fenêtre et qui pouvait diverger du calque).

Chaque changement est écrit dans le journal de débogage
(LASER_STUDIO_DEBUG=1, voir core/debug_log.py) : ancienne et nouvelle valeur.
"""
import logging
import uuid

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import LOGGER_NAME
from laser_studio.i18n import tr
from laser_studio.models.change_log import ChangeLog

log = logging.getLogger(f"{LOGGER_NAME}.modeles")

# Modes des calques : codes indépendants de la langue (voir layer_modes.py).
# ENGRAVE_MODE / CUT_MODE / MARK_MODE : noms historiques des codes.
from laser_studio.models.layer_modes import (  # noqa: E402
    LAYER_LASER_CMDS, LAYER_MODE_TR_KEYS, LAYER_MODES, MODE_CUT,
    MODE_FILL, MODE_MARK, MODE_PERF, normalize_mode,
)

ENGRAVE_MODE, CUT_MODE, MARK_MODE, PERF_MODE = MODE_FILL, MODE_CUT, MODE_MARK, MODE_PERF

DEFAULT_LAYER_COLORS = [
    "#ff3b30", "#34c759", "#0a84ff", "#ff9f0a",
    "#bf5af2", "#64d2ff", "#ffd60a", "#ff375f",
]

# Calques de base, toujours présents (voir LayersModel.ensure_base_layers) :
# rôle -> (clé du nom, couleur, mode, puissance, vitesse, passes, pas de
# remplissage). Leur nom est fixe (traduit) et ils ne peuvent pas être
# supprimés ; chaque profil matériau a une entrée pour chacun.
BASE_LAYER_ROLES = ("engrave", "cut", "mark")
BASE_LAYER_DEFAULTS = {
    "engrave": ("layers.default_name_engrave", DEFAULT_LAYER_COLORS[2], MODE_FILL, 35.0, 2000, 1, 0.10),
    "cut": ("layers.default_name_cut", DEFAULT_LAYER_COLORS[0], MODE_CUT, 90.0, 250, 1, 0.10),
    "mark": ("layers.default_name_mark", DEFAULT_LAYER_COLORS[1], MODE_MARK, 75.0, 2000, 1, 0.06),
}


# Réglages modifiables d'un calque, avec leur type. L'identifiant et le rôle
# ne se modifient pas (les objets du canevas sont rattachés par identifiant).
LAYER_FIELD_CASTS = {
    "name": str,
    "color": str,
    "mode": str,
    "power": float,
    "speed": int,
    "passes": int,
    "line_interval": float,
    "line_interval_linked": bool,
    "enabled": bool,
    "overscan": bool,
    "laser_cmd": str,
    "tabs": bool,
    "tab_count": int,
    "tab_width": float,
    "kerf": bool,
    "kerf_width": float,
    "lead": bool,
    "lead_radius": float,
    "perf_dash": float,
    "perf_gap": float,
    "ramp": bool,
    "ramp_power": float,
    "air": bool,
}

# Ponts de maintien d'un calque de découpe (voir vector/tabs.py) : bornes des réglages.
TAB_COUNT_MAX = 20
TAB_WIDTH_MIN_MM, TAB_WIDTH_MAX_MM = 0.1, 10.0
# Compensation du kerf d'un calque de découpe (voir vector/kerf.py) : largeur de la saignée, en mm.
KERF_WIDTH_MIN_MM, KERF_WIDTH_MAX_MM = 0.01, 2.0
DEFAULT_KERF_WIDTH_MM = 0.15

# Arcs d'entrée et de sortie d'un calque de découpe (voir vector/lead.py) : rayon, en mm.
LEAD_RADIUS_MIN_MM, LEAD_RADIUS_MAX_MM = 0.2, 10.0
DEFAULT_LEAD_RADIUS_MM = 1.0

# Perforation (mode Perforation, voir vector/perforate.py) : longueur d'un trait et d'un vide, en mm.
PERF_LENGTH_MIN_MM, PERF_LENGTH_MAX_MM = 0.1, 50.0
DEFAULT_PERF_DASH_MM = 2.0
DEFAULT_PERF_GAP_MM = 1.0

# Rampe de puissance d'un calque de contour (voir gcode/vector._pass_power) : puissance finale, en %.
RAMP_POWER_MIN_PCT, RAMP_POWER_MAX_PCT = 1.0, 100.0
DEFAULT_RAMP_POWER_PCT = 100.0

DEFAULT_TAB_COUNT = 4
DEFAULT_TAB_WIDTH_MM = 0.5


def base_layer_name(role):
    """Nom fixe (traduit) du calque de base `role`."""
    return tr(BASE_LAYER_DEFAULTS[role][0])


def mode_label(mode):
    """Libellé traduit du mode `mode` (code), à afficher."""
    key = LAYER_MODE_TR_KEYS.get(normalize_mode(mode))
    return tr(key) if key else str(mode)


def layer_label(layer):
    """« Nom  [mode traduit] » d'un calque, pour les listes et les messages."""
    return f"{layer.name}  [{mode_label(layer.mode)}]"


def validated_settings(source, defaults=None):
    """Réglages de `source` (dictionnaire) convertis dans leur type.

    Les clés qui ne sont pas des réglages (id, role...) sont ignorées. Une
    valeur inutilisable (type, mode inconnu) est ignorée, ou remplacée par
    celle de `defaults` (un LaserLayer) s'il est donné."""
    values = {}
    for key, cast in LAYER_FIELD_CASTS.items():
        if key not in source:
            continue
        try:
            value = cast(source[key])
            if key == "mode":
                value = normalize_mode(value)       # ancien libellé français -> code
                if value not in LAYER_MODES:
                    raise ValueError(value)
            elif key == "laser_cmd":
                value = value.strip().upper()
                if value not in LAYER_LASER_CMDS:
                    raise ValueError(value)
            elif key == "tab_count":
                value = min(max(0, int(value)), TAB_COUNT_MAX)
            elif key == "tab_width":
                value = float(value)
                if not value == value:                  # NaN
                    raise ValueError(value)
                value = min(max(value, TAB_WIDTH_MIN_MM), TAB_WIDTH_MAX_MM)
            elif key == "kerf_width":
                value = float(value)
                if not value == value:                  # NaN
                    raise ValueError(value)
                value = min(max(value, KERF_WIDTH_MIN_MM), KERF_WIDTH_MAX_MM)
            elif key == "lead_radius":
                value = float(value)
                if not value == value:                  # NaN
                    raise ValueError(value)
                value = min(max(value, LEAD_RADIUS_MIN_MM), LEAD_RADIUS_MAX_MM)
            elif key in ("perf_dash", "perf_gap"):
                value = float(value)
                if not value == value:                  # NaN
                    raise ValueError(value)
                value = min(max(value, PERF_LENGTH_MIN_MM), PERF_LENGTH_MAX_MM)
            elif key == "ramp_power":
                value = float(value)
                if not value == value:                  # NaN
                    raise ValueError(value)
                value = min(max(value, RAMP_POWER_MIN_PCT), RAMP_POWER_MAX_PCT)
            elif key == "passes":
                # 0 passe = aucune découpe/marquage généré. On refuse 0 et les
                # négatifs (souvent issus d'un ancien matériau pass_c=0 ou d'un
                # profil mal migré). Le spin UI est déjà borné à [1, 50].
                value = max(1, int(value))
        except (TypeError, ValueError):
            if defaults is not None:
                values[key] = getattr(defaults, key)
            continue
        values[key] = value
    return values


class LaserLayer:
    """Un calque = une couleur + un jeu de réglages laser, comme dans LightBurn.

    `role` : "engrave", "cut" ou "mark" pour les trois calques de base (nom
    fixe, non supprimables), None pour un calque ajouté.

    Un LaserLayer se lit librement ; il ne se modifie qu'à travers
    LayersModel.update, pour que chaque changement soit signalé."""

    def __init__(self, name="Calque", color="#ff3b30", mode=MODE_CUT,
                 power=80.0, speed=300, passes=1, line_interval=0.10,
                 enabled=True, layer_id=None, line_interval_linked=False, role=None,
                 overscan=True, laser_cmd="", tabs=False, tab_count=DEFAULT_TAB_COUNT,
                 tab_width=DEFAULT_TAB_WIDTH_MM, kerf=False, kerf_width=DEFAULT_KERF_WIDTH_MM,
                 lead=False, lead_radius=DEFAULT_LEAD_RADIUS_MM,
                 perf_dash=DEFAULT_PERF_DASH_MM, perf_gap=DEFAULT_PERF_GAP_MM,
                 ramp=False, ramp_power=DEFAULT_RAMP_POWER_PCT, air=False):
        self.id = layer_id or uuid.uuid4().hex[:8]
        self.role = role
        self.name = name
        self.color = color
        self.mode = normalize_mode(mode)    # cf. LAYER_MODES (codes)
        self.power = float(power)           # %
        self.speed = int(speed)             # mm/min
        self.passes = max(1, int(passes))   # 0 passe = aucune découpe générée
        self.line_interval = float(line_interval)  # mm (pas du remplissage)
        # Si True, line_interval suit automatiquement la taille du spot
        # (MachineConfig.focal) à chaque changement — voir LayersTab.link_all_to_focal.
        self.line_interval_linked = bool(line_interval_linked)
        self.enabled = bool(enabled)
        # Surbalayage : appliqué à ce calque seulement si l'option est aussi activée dans Configuration
        # GRBL (réglage global : elle en donne le mode et la distance). Sans effet hors gravure remplie.
        self.overscan = bool(overscan)
        # Commande laser propre au calque ("" : celle de Configuration GRBL, voir LAYER_LASER_CMDS).
        self.laser_cmd = laser_cmd if laser_cmd in LAYER_LASER_CMDS else ""
        # Ponts de maintien (calque de découpe) : `tabs` les active (le nombre et la largeur sont conservés
        # quand on le désactive) ; nombre par contour extérieur fermé et largeur en mm le long du tracé.
        # Sans effet hors découpe.
        self.tabs = bool(tabs)
        self.tab_count = min(max(0, int(tab_count)), TAB_COUNT_MAX)
        self.tab_width = min(max(float(tab_width), TAB_WIDTH_MIN_MM), TAB_WIDTH_MAX_MM)
        # Compensation du kerf (calque de découpe) : `kerf` l'active, `kerf_width` (mm) est la largeur de la
        # saignée du laser ; les contours sont décalés de la moitié. Sans effet hors découpe.
        self.kerf = bool(kerf)
        self.kerf_width = min(max(float(kerf_width), KERF_WIDTH_MIN_MM), KERF_WIDTH_MAX_MM)
        # Arcs d'entrée et de sortie (calque de découpe) : `lead` les active, `lead_radius` (mm) est le rayon
        # du quart de cercle tangent au contour, posé sur la chute. Sans effet hors découpe.
        self.lead = bool(lead)
        self.lead_radius = min(max(float(lead_radius), LEAD_RADIUS_MIN_MM), LEAD_RADIUS_MAX_MM)
        # Perforation (mode Perforation) : longueur d'un trait coupé et d'un vide, en mm. Sans effet
        # dans les autres modes.
        self.perf_dash = min(max(float(perf_dash), PERF_LENGTH_MIN_MM), PERF_LENGTH_MAX_MM)
        self.perf_gap = min(max(float(perf_gap), PERF_LENGTH_MIN_MM), PERF_LENGTH_MAX_MM)
        # Rampe de puissance (découpe, perforation, marquage) : `ramp` l'active, `ramp_power` (%) est la
        # puissance de la dernière passe ; celle du calque est la première. Sans effet à une seule passe.
        self.ramp = bool(ramp)
        self.ramp_power = min(max(float(ramp_power), RAMP_POWER_MIN_PCT), RAMP_POWER_MAX_PCT)
        # Air assist : soufflage allumé (M8) pendant ce calque, éteint (M9) après. Tous les modes.
        self.air = bool(air)

    def to_dict(self):
        return dict(self.__dict__)

    @staticmethod
    def from_dict(d):
        layer = LaserLayer()
        layer.__dict__.update(d)
        # Anciens projets / profils pouvaient avoir passes=0 (matériau sans
        # découpe). On force au minimum 1 pour que la génération produise
        # bien les contours si le calque est actif.
        try:
            layer.passes = max(1, int(layer.passes))
        except (TypeError, ValueError):
            layer.passes = 1
        layer.mode = normalize_mode(getattr(layer, "mode", MODE_CUT))
        return layer


def _describe(layer):
    return f"« {layer.name} » ({layer.id})"


class LayersModel(QObject):
    """Liste ordonnée des calques. L'ordre de la liste est aussi l'ordre
    d'exécution des calques dans le G-Code.

    Signaux, émis après la modification :
    - layer_changed(id, {réglage: nouvelle valeur}) : seulement les réglages
      qui ont vraiment changé (aucune émission si rien ne change) ;
    - layer_added(id), layer_removed(id), layers_reordered() ;
    - layers_reset() : liste entièrement rechargée (projet, profil machine) ;
    - changed() : après chacun des signaux précédents, pour qui veut
      seulement savoir que « les calques ont changé » ;
    - engrave_layer_selected(id) : calque de la gravure des images choisi
      (liste « Calque de gravure » de l'onglet image).
    """

    layer_changed = pyqtSignal(str, dict)
    layer_added = pyqtSignal(str)
    layer_removed = pyqtSignal(str)
    layers_reordered = pyqtSignal()
    layers_reset = pyqtSignal()
    changed = pyqtSignal()
    engrave_layer_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Calque de la gravure des images choisi par l'utilisateur (None :
        # le premier calque de gravure, voir engrave_layer).
        self._engrave_layer_id = None
        # Les trois calques de base : la gravure (mode remplissage) en première
        # position, calque proposé par défaut pour la gravure des images
        # (tramage / séparation couleur), puis la découpe et le marquage.
        self.layers = [self.new_base_layer(role) for role in BASE_LAYER_ROLES]
        self._log = ChangeLog(self)

    # Réglages saisis au clavier : une ligne de journal à la fin de la saisie.
    TYPED_FIELDS = ("name",)

    def flush_log(self):
        """Écrit tout de suite les saisies en cours dans le journal."""
        self._log.flush()

    # -- lecture -----------------------------------------------------------

    @staticmethod
    def new_base_layer(role):
        """Calque de base `role` avec ses réglages par défaut."""
        key, color, mode, power, speed, passes, interval = BASE_LAYER_DEFAULTS[role]
        return LaserLayer(name=tr(key), color=color, mode=mode, power=power, speed=speed,
                          passes=passes, line_interval=interval, role=role)

    def is_base_layer(self, layer):
        return getattr(layer, "role", None) in BASE_LAYER_ROLES

    def get(self, layer_id):
        for l in self.layers:
            if l.id == layer_id:
                return l
        return None

    def engrave_layer(self):
        """Calque de la gravure des images (tramage, séparation couleur) : le
        calque choisi (select_engrave_layer) s'il existe encore et grave
        toujours (mode Gravure Remplie) ; sinon le premier calque en mode
        Gravure Remplie, à défaut le premier calque, ou None s'il n'y a
        aucun calque."""
        chosen = self.get(self._engrave_layer_id)
        if chosen is not None and chosen.mode == ENGRAVE_MODE:
            return chosen
        for l in self.layers:
            if l.mode == ENGRAVE_MODE:
                return l
        return self.layers[0] if self.layers else None

    def select_engrave_layer(self, layer_id):
        """Choisit le calque de la gravure des images (un calque en mode
        Gravure Remplie). Renvoie True si le choix a changé."""
        layer = self.get(layer_id)
        if layer is None or layer.mode != ENGRAVE_MODE:
            log.warning("Calques : calque de gravure ignoré : %r", layer_id)
            return False
        if self.engrave_layer() is layer and self._engrave_layer_id == layer_id:
            return False
        self._engrave_layer_id = layer_id
        log.info("Calques : calque de gravure des images -> %s", _describe(layer))
        self.engrave_layer_selected.emit(layer_id)
        return True

    def layer_for_role(self, role):
        """Calque de base de rôle `role` (« engrave », « cut », « mark »), sinon le calque SVG par défaut."""
        for layer in self.layers:
            if getattr(layer, "role", None) == role:
                return layer
        return self.default_svg_layer()

    def default_svg_layer(self):
        """Calque par défaut des imports SVG (import classique et PNG -> SVG) :
        le premier calque en mode Découpe. À défaut, le premier calque."""
        for l in self.layers:
            if l.mode == MODE_CUT:
                return l
        return self.layers[0] if self.layers else None

    def to_list(self):
        return [l.to_dict() for l in self.layers]

    def colors_by_name(self):
        """Couleur de chaque calque, par nom (le premier calque d'un nom donné) : couleurs de l'aperçu 2D."""
        colors = {}
        for layer in self.layers:
            colors.setdefault(layer.name, layer.color)
        return colors

    # -- modification ------------------------------------------------------

    def update(self, layer_id, **fields):
        """Modifie les réglages d'un calque. Les valeurs sont converties dans
        leur type ; une valeur inutilisable est ignorée. Renvoie les réglages
        qui ont changé ({réglage: nouvelle valeur}), vide si rien n'a changé
        (aucun signal n'est alors émis)."""
        unknown = set(fields) - set(LAYER_FIELD_CASTS)
        if unknown:
            raise KeyError(f"Réglages de calque inconnus : {sorted(unknown)}")
        layer = self.get(layer_id)
        if layer is None:
            log.warning("Calques : calque %s introuvable, modification ignorée : %s", layer_id, fields)
            return {}
        changes, before = {}, {}
        for key, value in validated_settings(fields).items():
            old = getattr(layer, key, None)
            if old != value:
                before[key] = old
                setattr(layer, key, value)
                changes[key] = value
        if changes:
            self._log.now(f"Calques : {_describe(layer)}",
                          {k: v for k, v in changes.items() if k not in self.TYPED_FIELDS}, before)
            for key in self.TYPED_FIELDS:
                if key in changes:
                    self._log.later((layer.id, key), lambda l=layer: f"Calques : {_describe(l)}",
                                    key, before[key], changes[key])
            self.layer_changed.emit(layer.id, changes)
            self.changed.emit()
        return changes

    def add_layer(self, line_interval=None, line_interval_linked=False):
        idx = len(self.layers)
        color = DEFAULT_LAYER_COLORS[idx % len(DEFAULT_LAYER_COLORS)]
        kwargs = {"line_interval_linked": line_interval_linked}
        if line_interval is not None:
            kwargs["line_interval"] = line_interval
        layer = LaserLayer(name=f"Calque {idx + 1}", color=color, **kwargs)
        self.layers.append(layer)
        log.info("Calques : ajout de %s : %s", _describe(layer), layer.to_dict())
        self.layer_added.emit(layer.id)
        self.changed.emit()
        return layer

    def append_layer(self, layer):
        """Ajoute un calque déjà réglé (`LaserLayer`, ex. plaque importée de Stencil Studio) et le renvoie."""
        self.layers.append(layer)
        log.info("Calques : ajout de %s : %s", _describe(layer), layer.to_dict())
        self.layer_added.emit(layer.id)
        self.changed.emit()
        return layer

    def remove_layer(self, layer_id):
        layer = self.get(layer_id)
        if layer is None:
            return
        self.layers = [l for l in self.layers if l.id != layer_id]
        log.info("Calques : suppression de %s", _describe(layer))
        self.layer_removed.emit(layer_id)
        self.changed.emit()

    def move_layer(self, layer_id, delta):
        """Décale un calque de `delta` positions dans la liste (-1 = monter,
        +1 = descendre). Renvoie le nouvel index, ou None si le calque est
        introuvable / déjà en butée."""
        idx = next((i for i, l in enumerate(self.layers) if l.id == layer_id), None)
        if idx is None:
            return None
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.layers):
            return None
        layer = self.layers.pop(idx)
        self.layers.insert(new_idx, layer)
        log.info("Calques : %s déplacé de la position %d à %d", _describe(layer), idx + 1, new_idx + 1)
        self.layers_reordered.emit()
        self.changed.emit()
        return new_idx

    def load_list(self, data):
        """Remplace toute la liste (projet ouvert, profil machine au démarrage).

        Une valeur corrompue est remplacée par celle d'un calque neuf, plutôt
        que de planter à l'ouverture. Les trois calques de base sont ensuite
        garantis (ensure_base_layers)."""
        layers = []
        for d in data or []:
            if not isinstance(d, dict):
                continue
            layer = LaserLayer.from_dict(d)
            for key, value in validated_settings(d, defaults=LaserLayer()).items():
                setattr(layer, key, value)
            layers.append(layer)
        self.layers = layers
        self.ensure_base_layers()
        log.info("Calques : liste rechargée (%d calques)", len(self.layers))
        for layer in self.layers:
            log.info("Calques :   %s %s", _describe(layer),
                     {k: getattr(layer, k) for k in LAYER_FIELD_CASTS if k != "name"})
        self.layers_reset.emit()
        self.changed.emit()

    def ensure_base_layers(self):
        """Garantit les trois calques de base (gravure, découpe, marquage),
        avec leur nom fixe. Appelé par load_list, avant son signal.

        Calques enregistrés avant les rôles (projet, profil machine) : le
        premier calque sans rôle du bon mode devient le calque de base, et
        prend son nom fixe (son identifiant ne change pas : les objets du
        canevas qui y sont rattachés le gardent). S'il n'y en a pas, le
        calque de base est ajouté avec ses réglages par défaut."""
        for role in BASE_LAYER_ROLES:
            layer = next((l for l in self.layers if getattr(l, "role", None) == role), None)
            if layer is None:
                mode = BASE_LAYER_DEFAULTS[role][2]
                layer = next((l for l in self.layers
                              if getattr(l, "role", None) is None and l.mode == mode), None)
                if layer is None:
                    layer = self.new_base_layer(role)
                    self.layers.append(layer)
                layer.role = role
            layer.name = base_layer_name(role)
