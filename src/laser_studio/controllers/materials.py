"""Profils matériaux : vitesses, puissances et passes de gravure et de
découpe enregistrées par matière."""

import json


from laser_studio.controllers.layer_memory import settings_from
from laser_studio.models.materials import MaterialsModel
from laser_studio.i18n import tr

# Réglages d'un calque qui dépendent du matériau (et non de la structure du
# job : le mode, le nom et l'activation des calques ne changent pas avec la
# matière).
MATERIAL_LAYER_KEYS = ("power", "speed", "passes", "line_interval", "line_interval_linked")

# Base de matériaux utilisée (1) au tout premier lancement de l'application,
# avant tout profil machine, et (2) comme repli pour un ancien profil machine
# enregistré avant l'ajout de la liaison materials_db <-> profil (voir
# WindowState.apply_machine_profile). Une nouvelle machine créée après cet ajout
# démarre avec une COPIE de cette base, qu'elle peut ensuite personnaliser
# sans affecter les autres profils (voir WindowState.capture_machine_profile).
DEFAULT_MATERIALS_DB = {
    "Personnalisé": {
        "sp_e": 2000,
        "pw_e": 30,
        "sp_c": 300,
        "pw_c": 90,
        "pass_c": 1,
    },
    "Contreplaqué 3mm": {
        "sp_e": 2500,
        "pw_e": 35,
        "sp_c": 250,
        "pw_c": 95,
        "pass_c": 2,
    },
    "MDF 4mm": {
        "sp_e": 2200,
        "pw_e": 40,
        "sp_c": 180,
        "pw_c": 100,
        "pass_c": 3,
    },
    "Acrylique 3mm": {
        "sp_e": 3000,
        "pw_e": 25,
        "sp_c": 200,
        "pw_c": 90,
        "pass_c": 2,
    },
    "Ardoise / Carrelage": {
        "sp_e": 1500,
        "pw_e": 45,
        "sp_c": 500,
        "pw_c": 0,
        "pass_c": 0,
    },
    "Cuir 2mm": {
        "sp_e": 2800,
        "pw_e": 20,
        "sp_c": 350,
        "pw_c": 80,
        "pass_c": 1,
    },
}

# Matériau qu'on ne peut pas supprimer.
DEFAULT_MATERIAL = "Personnalisé"


def capture_material_layers(layer_manager):
    """Réglages de chaque calque à mémoriser dans un matériau (clé "layers"),
    avec le rôle (calques de base), l'identifiant et le nom du calque pour
    le retrouver."""
    return [
        {"role": getattr(layer, "role", None), "id": layer.id, "name": layer.name,
         **{key: getattr(layer, key) for key in MATERIAL_LAYER_KEYS}}
        for layer in layer_manager.layers
    ]


def _base_entry(role, power=None, speed=None, passes=None):
    """Entrée de matériau pour le calque de base `role` : valeurs données, ou
    celles par défaut du calque de base."""
    from laser_studio.models.layers import BASE_LAYER_DEFAULTS
    _key, _color, _mode, d_power, d_speed, d_passes, d_interval = BASE_LAYER_DEFAULTS[role]
    p = int(d_passes if passes is None else passes)
    return {"role": role,
            "power": float(d_power if power is None else power),
            "speed": int(d_speed if speed is None else speed),
            "passes": max(1, p),  # 0 passe = aucune géométrie générée
            "line_interval": d_interval}


def _material_has_meaningful_cut(material):
    """True si le matériau fournit des réglages de découpe utilisables.

    On regarde d'abord les clés plates (format ancien ou _job_settings) :
    pass_c > 0. Sinon on regarde l'entrée cut dans "layers".

    Les matériaux type Ardoise (pass_c=0) sont considérés sans découpe :
    on ne doit pas écraser les calques cut existants ni enregistrer des
    zéros. Même après complete_material (qui met des défauts 90/2 dans
    layers), le pass_c=0 plat reste prioritaire.
    """
    if not material:
        return False
    # Clés plates prioritaires (même si "layers" est déjà présent).
    if "pass_c" in material or "sp_c" in material or "pw_c" in material:
        return int(material.get("pass_c", 0) or 0) > 0
    if "layers" in material:
        for d in material.get("layers") or []:
            if isinstance(d, dict) and d.get("role") == "cut":
                return int(d.get("passes") or 0) > 0
        return False
    return False


def complete_material(material):
    """Matériau avec, au minimum, une entrée pour chacun des trois calques de
    base (gravure, découpe, marquage). Renvoie un nouveau dictionnaire.

    Ancien matériau (sp_e / pw_e / sp_c / pw_c / pass_c) : la gravure reprend
    sp_e / pw_e, la découpe sp_c / pw_c / pass_c (valeurs par défaut si 0
    passe : matière qu'on ne découpe pas), le marquage ses valeurs par défaut.
    Entrée de base manquante : valeurs par défaut. Les autres entrées (calques
    ajoutés) sont gardées."""
    from laser_studio.models.layers import BASE_LAYER_ROLES
    if not material:
        material = {}
    material = dict(material)
    entries = [dict(d) for d in material.get("layers") or [] if isinstance(d, dict)]
    roles = {d.get("role") for d in entries}
    
    for role in BASE_LAYER_ROLES:
        if role in roles:
            continue
        if role == "engrave" and "sp_e" in material and "pw_e" in material:
            entry = _base_entry(role, material["pw_e"], material["sp_e"])
        elif role == "cut":
            # pass_c == 0 (Ardoise, etc.) ou absence de clés cut → défauts
            # sensés plutôt que des zéros inutilisables.
            if _material_has_meaningful_cut(material):
                passes = max(1, int(material.get("pass_c", 0) or 0))
                entry = _base_entry(
                    role, material.get("pw_c"), material.get("sp_c"), passes
                )
            else:
                # Pas de découpe configurée : réglage de découpe par défaut (BASE_LAYER_DEFAULTS).
                entry = _base_entry(role)
        else:
            entry = _base_entry(role)
        entries.append(entry)
        
    material["layers"] = entries
    return material


def apply_material_to_layers(layer_manager, material):
    """Applique un matériau au tableau des calques. Renvoie True si un calque
    a changé.

    Les matériaux sans découpe utile (pass_c=0, ex. Ardoise / Carrelage) ne
    touchent pas aux calques de découpe déjà présents.

    Si le matériau a encore les clés plates (sp_e/pw_e/sp_c/...), elles
    priment pour les calques de base engrave/cut (fiable pour les profils
    DEFAULT et _job_settings).
    """
    material = material or {}
    has_cut = _material_has_meaningful_cut(material)
    entries = complete_material(material)["layers"]
    by_role = {d["role"]: d for d in entries if d.get("role")}
    by_id = {d.get("id"): d for d in entries if d.get("id")}

    # Clés plates prioritaires pour les calques de base (évite d'appliquer
    # par erreur les défauts mark 75/2000 à l'engrave).
    if "pw_e" in material and "sp_e" in material:
        by_role["engrave"] = {
            **(by_role.get("engrave") or {"role": "engrave"}),
            "power": float(material["pw_e"]),
            "speed": int(material["sp_e"]),
        }
    if has_cut and ("pw_c" in material or "sp_c" in material or "pass_c" in material):
        by_role["cut"] = {
            **(by_role.get("cut") or {"role": "cut"}),
            "power": float(material.get("pw_c") or 0),
            "speed": int(material.get("sp_c") or 250),
            "passes": max(1, int(material.get("pass_c") or 1)),
        }

    changed = False
    for layer in layer_manager.layers:
        role = getattr(layer, "role", None)
        d = by_role.get(role) if role else by_id.get(layer.id)
        if d is None:
            continue
        # Matériau sans découpe utile (Ardoise : 0 passe) : le calque de découpe garde ses réglages,
        # au lieu d'être remis aux valeurs par défaut que complete_material a ajoutées à ce matériau.
        if role == "cut" and not has_cut:
            continue
        layer_manager.update(layer.id, **settings_from({k: d[k] for k in MATERIAL_LAYER_KEYS if k in d}))
        changed = True
    return changed


class MaterialsController:
    """Profils matériaux : le modèle (MaterialsModel, `model`) et les actions de
    la barre d'outils : appliquer, créer, supprimer, exporter, importer.

    Un matériau garde les réglages de chaque calque (clé "layers", voir
    capture_material_layers), et sous les clés sp_e / pw_e (gravure image :
    vitesse, puissance), sp_c / pw_c / pass_c (ancienne découpe SVG : vitesse,
    puissance, passes).

    Plus de bouton « Enregistrer » : la fenêtre appelle
    store_current_settings() à chaque changement de calque, et le matériau
    choisi suit aussitôt.

        materials = MaterialsController(
            self, page.material_combo, dict(DEFAULT_MATERIALS_DB),
            current_settings=..., apply_settings=...,
        )
        layers_tab.material_selected.connect(materials.apply_selected)

    `combo` : la liste déroulante des matériaux (barre d'outils de l'onglet
    Calques), tenue à jour à partir des signaux du modèle.
    `current_settings()` : réglages en cours, au format d'un matériau.
    `apply_settings(material)` : les applique.
    """

    def __init__(
        self, parent, combo, materials, current_settings, apply_settings, dialogs=None
    ):
        # Boîtes de dialogue (UserDialogs) : celles de la fenêtre, ou un objet
        # qui répond à la place de l'utilisateur dans les tests.
        if dialogs is None:
            from laser_studio.ui.user_dialogs import UserDialogs
            dialogs = UserDialogs(parent)
        self._dialogs = dialogs
        self._combo = combo
        self._current_settings = current_settings
        self._apply_settings = apply_settings
        self.model = MaterialsModel(complete=complete_material)
        self.model.materials_reset.connect(lambda: self._fill_combo(block_signals=True))
        self.model.material_added.connect(self._on_added)
        self.model.material_removed.connect(self._on_removed)
        self.model.current_changed.connect(self._show_current)
        self.model.set_materials(materials, current=combo.currentText() or None)

    @property
    def materials(self):
        """Matériaux (nom -> réglages) du modèle."""
        return self.model.materials

    def set_materials(self, materials, block_signals=True):
        """Remplace toute la liste (projet ouvert, profil machine choisi), sans
        appliquer de matériau : les calques du projet ou du profil font foi.
        Chaque matériau est complété avec les trois calques de base
        (complete_material). `block_signals` : gardé pour compatibilité, la
        liste déroulante est toujours remplie sans émettre de signal."""
        self.model.set_materials(materials)

    # -- modèle -> liste déroulante

    def _fill_combo(self, block_signals=True):
        if block_signals:
            self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(self.model.names())
        if self.model.current is not None:
            self._combo.setCurrentText(self.model.current)
        if block_signals:
            self._combo.blockSignals(False)

    def _on_added(self, name):
        self._combo.blockSignals(True)
        self._combo.addItem(name)
        self._combo.blockSignals(False)

    def _on_removed(self, name):
        index = self._combo.findText(name)
        if index >= 0:
            self._combo.blockSignals(True)
            self._combo.removeItem(index)
            self._combo.blockSignals(False)
        self._show_current(self.model.current)

    def _show_current(self, name):
        if name is not None and self._combo.currentText() != name:
            self._combo.blockSignals(True)
            self._combo.setCurrentText(name)
            self._combo.blockSignals(False)

    # -- actions de la page

    def apply_selected(self, *_args):
        """Applique les réglages du matériau choisi dans la liste."""
        name = self._combo.currentText()
        if name in self.model.materials:
            self.model.select(name)
            self._apply_settings(self.model.get(name))

    def store_current_settings(self):
        """Enregistre les réglages en cours dans le matériau choisi (appelé à
        chaque changement de calque). Renvoie True s'il a changé."""
        name = self.model.current
        if name is None:
            return False
        return self.model.store(name, self._current_settings())

    def new_material(self):
        name = self._dialogs.ask_text(tr("material.new_profile_title"), tr("material.new_profile_prompt"))
        if name is not None and name.strip():
            name = name.strip()
            self.model.store(name, self._current_settings())
            self.model.select(name)

    def delete_selected(self):
        name = self._combo.currentText()
        if name == DEFAULT_MATERIAL:
            self._dialogs.warning(tr("material.delete_forbidden_title"), tr("material.delete_forbidden_body"))
            return
        if self._dialogs.confirm_yes_no(tr("material.delete_title"), tr("material.delete_body").format(name=name)):
            self.model.remove(name)

    def export_materials(self):
        path = self._dialogs.save_file(tr("material.export_title"), "materiaux_laser.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.materials, f, indent=2, ensure_ascii=False)
            self._dialogs.notify(tr("material.export_success_body").format(count=len(self.materials), path=path))
        except Exception as e:
            self._dialogs.error(tr("laser.error"), tr("material.error_export").format(error=e))

    def import_materials(self):
        path = self._dialogs.open_file(tr("material.import_title"), "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if not isinstance(imported, dict):
                raise ValueError(tr("material.invalid_file"))
            added, updated = 0, 0
            for name, material in imported.items():
                if not isinstance(material, dict):
                    continue
                if name in self.materials:
                    updated += 1
                else:
                    added += 1
                self.model.store(name, material)
            self._dialogs.notify(tr("material.import_success_body").format(added=added, updated=updated))
        except Exception as e:
            self._dialogs.error(tr("laser.error"), tr("material.error_import").format(error=e))
