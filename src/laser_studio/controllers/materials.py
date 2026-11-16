"""Profils matériaux : vitesses, puissances et passes de gravure et de
découpe enregistrées par matière."""

import json

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from laser_studio.controllers.layer_memory import settings_from
from laser_studio.i18n import tr

# Réglages d'un calque qui dépendent du matériau (et non de la structure du
# job : le mode, le nom et l'activation des calques ne changent pas avec la
# matière).
MATERIAL_LAYER_KEYS = ("power", "speed", "passes", "line_interval", "line_interval_linked")
ENGRAVE_MODE = "Gravure Remplie"
CUT_MODE = "Découpe"

# Base de matériaux utilisée (1) au tout premier lancement de l'application,
# avant tout profil machine, et (2) comme repli pour un ancien profil machine
# enregistré avant l'ajout de la liaison materials_db <-> profil (voir
# main_window._apply_machine_profile). Une nouvelle machine créée après cet ajout
# démarre avec une COPIE de cette base, qu'elle peut ensuite personnaliser
# sans affecter les autres profils (voir main_window._capture_machine_profile).
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
    return {"role": role,
            "power": float(d_power if power is None else power),
            "speed": int(d_speed if speed is None else speed),
            "passes": int(d_passes if passes is None else passes),
            "line_interval": d_interval}


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
            passes = int(material.get("pass_c", 0) or 0)
            if passes > 0:
                entry = _base_entry(role, material.get("pw_c"), material.get("sp_c"), passes)
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

    Les calques de base reprennent l'entrée de leur rôle ; les autres calques,
    l'entrée de même identifiant. Seuls les réglages de MATERIAL_LAYER_KEYS
    sont repris ; aucun calque n'est ajouté ni supprimé. Un ancien matériau
    est d'abord complété (complete_material)."""
    entries = complete_material(material)["layers"]
    by_role = {d["role"]: d for d in entries if d.get("role")}
    by_id = {d.get("id"): d for d in entries if d.get("id")}
    changed = False
    for layer in layer_manager.layers:
        role = getattr(layer, "role", None)
        d = by_role.get(role) if role else by_id.get(layer.id)
        if d:
            layer_manager.update(layer.id, **settings_from({k: d[k] for k in MATERIAL_LAYER_KEYS if k in d}))
            changed = True
    return changed


def complete_materials(materials):
    """Tous les matériaux complétés (complete_material), dans le même ordre."""
    if not materials:
        return {}
    return {name: complete_material(m) for name, m in materials.items()}


class MaterialsController:
    """Liste des matériaux (`materials` : nom -> réglages) et ses actions :
    appliquer, enregistrer, créer, supprimer, exporter, importer.

    Un matériau garde les réglages de chaque calque (clé "layers", voir
    capture_material_layers), et sous les clés sp_e / pw_e (gravure image :
    vitesse, puissance), sp_c / pw_c / pass_c (ancienne découpe SVG : vitesse,
    puissance, passes).

        materials = MaterialsController(
            self, page.material_combo, dict(DEFAULT_MATERIALS_DB),
            current_settings=..., apply_settings=...,
        )
        layers_tab.material_selected.connect(materials.apply_selected)

    `combo` : la liste déroulante des matériaux (barre d'outils de l'onglet
    Calques). `current_settings()` : réglages en cours, au format d'un
    matériau. `apply_settings(material)` : les applique.
    """

    def __init__(
        self, parent, combo, materials, current_settings, apply_settings
    ):
        self._parent = parent
        self._combo = combo
        self.materials = complete_materials(materials)
        self._current_settings = current_settings
        self._apply_settings = apply_settings

    def set_materials(self, materials, block_signals=False):
        """Remplace toute la liste (projet ouvert, profil machine choisi).

        Sans block_signals, le premier matériau de la liste est aussitôt
        appliqué (signal de la liste déroulante). Chaque matériau est complété
        avec les trois calques de base (complete_material)."""
        self.materials = complete_materials(materials)
        self._fill_combo(block_signals)

    def _fill_combo(self, block_signals):
        if block_signals:
            self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(list(self.materials.keys()))
        if block_signals:
            self._combo.blockSignals(False)

    # -- actions de la page

    def apply_selected(self, *_args):
        """Applique les réglages du matériau choisi."""
        material = self.materials.get(self._combo.currentText())
        if material is not None:
            self._apply_settings(material)

    def save_selected(self):
        """Enregistre les réglages en cours dans le matériau choisi."""
        name = self._combo.currentText()
        self.materials[name] = self._current_settings()
        QMessageBox.information(
            self._parent,
            tr("material.saved_title"),
            tr("material.saved_body").format(name=name),
        )

    def new_material(self):
        """Nouveau matériau, avec les réglages en cours."""
        name, ok = QInputDialog.getText(
            self._parent,
            tr("material.new_profile_title"),
            tr("material.new_profile_prompt"),
        )
        if ok and name.strip():
            name = name.strip()
            self.materials[name] = self._current_settings()
            self._combo.addItem(name)
            self._combo.setCurrentText(name)

    def delete_selected(self):
        name = self._combo.currentText()
        if name == DEFAULT_MATERIAL:
            QMessageBox.warning(
                self._parent,
                tr("material.delete_forbidden_title"),
                tr("material.delete_forbidden_body"),
            )
            return
        reply = QMessageBox.question(
            self._parent,
            tr("material.delete_title"),
            tr("material.delete_body").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.materials[name]
            self._combo.removeItem(self._combo.currentIndex())

    def export_materials(self):
        """Exporte tous les matériaux dans un fichier .json, partageable
        avec d'autres utilisateurs (même machine, par exemple)."""
        path, _ = QFileDialog.getSaveFileName(
            self._parent,
            tr("material.export_title"),
            "materiaux_laser.json",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.materials, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self._parent,
                tr("material.export_success_title"),
                tr("material.export_success_body").format(
                    count=len(self.materials), path=path
                ),
            )
        except Exception as e:
            QMessageBox.critical(
                self._parent,
                tr("laser.error"),
                tr("material.error_export").format(error=e),
            )

    def import_materials(self):
        """Importe des matériaux d'un fichier .json exporté : ceux du même
        nom sont mis à jour, les nouveaux sont ajoutés."""
        path, _ = QFileDialog.getOpenFileName(
            self._parent, tr("material.import_title"), "", "JSON (*.json)"
        )
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
                self.materials[name] = complete_material(material)
            self._fill_combo(block_signals=True)
            QMessageBox.information(
                self._parent,
                tr("material.import_success_title"),
                tr("material.import_success_body").format(
                    added=added, updated=updated
                ),
            )
        except Exception as e:
            QMessageBox.critical(
                self._parent,
                tr("laser.error"),
                tr("material.error_import").format(error=e),
            )
