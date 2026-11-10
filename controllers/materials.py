"""Profils matériaux : vitesses, puissances et passes de gravure et de
découpe enregistrées par matière."""

import json

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from i18n import tr

# Base de matériaux utilisée (1) au tout premier lancement de l'application,
# avant tout profil machine, et (2) comme repli pour un ancien profil machine
# enregistré avant l'ajout de la liaison materials_db <-> profil (voir
# MachineProfilesMixin._apply_machine_profile_widgets). Une nouvelle machine créée après cet ajout
# démarre avec une COPIE de cette base, qu'elle peut ensuite personnaliser
# sans affecter les autres profils (voir MachineProfilesMixin._capture_machine_profile_fields).
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


class MaterialsController:
    """Liste des matériaux (`materials` : nom -> réglages) et ses actions :
    appliquer, enregistrer, créer, supprimer, exporter, importer.

    Un matériau garde ses réglages sous les clés sp_e / pw_e (gravure :
    vitesse, puissance), sp_c / pw_c / pass_c (découpe : vitesse,
    puissance, passes).

        materials = MaterialsController(
            self, page.material_combo, dict(DEFAULT_MATERIALS_DB),
            current_settings=..., apply_settings=...,
        )
        page.material_selected.connect(materials.apply_selected)

    `combo` : la liste déroulante des matériaux (page Matériaux et
    connexion). `current_settings()` : réglages en cours, au format d'un
    matériau. `apply_settings(material)` : les applique.
    """

    def __init__(
        self, parent, combo, materials, current_settings, apply_settings
    ):
        self._parent = parent
        self._combo = combo
        self.materials = materials
        self._current_settings = current_settings
        self._apply_settings = apply_settings

    def set_materials(self, materials, block_signals=False):
        """Remplace toute la liste (projet ouvert, profil machine choisi).

        Sans block_signals, le premier matériau de la liste est aussitôt
        appliqué (signal de la liste déroulante)."""
        self.materials = materials
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
                self.materials[name] = material
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
