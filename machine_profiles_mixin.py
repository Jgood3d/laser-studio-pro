"""Gestion des profils machine et des profils matériaux (sauvegarde/chargement via QSettings)."""
from PyQt6.QtWidgets import (QMessageBox, QInputDialog, QFileDialog)
from PyQt6.QtCore import QSettings
import json

from i18n import tr

# Base de matériaux utilisée (1) au tout premier lancement de l'application,
# avant tout profil machine, et (2) comme repli pour un ancien profil machine
# enregistré avant l'ajout de la liaison materials_db <-> profil (voir
# _apply_machine_profile_fields). Une nouvelle machine créée après cet ajout
# démarre avec une COPIE de cette base, qu'elle peut ensuite personnaliser
# sans affecter les autres profils (voir _capture_machine_profile_fields).
DEFAULT_MATERIALS_DB = {
    "Personnalisé": {"sp_e": 2000, "pw_e": 30, "sp_c": 300, "pw_c": 90, "pass_c": 1},
    "Contreplaqué 3mm": {"sp_e": 2500, "pw_e": 35, "sp_c": 250, "pw_c": 95, "pass_c": 2},
    "MDF 4mm": {"sp_e": 2200, "pw_e": 40, "sp_c": 180, "pw_c": 100, "pass_c": 3},
    "Acrylique 3mm": {"sp_e": 3000, "pw_e": 25, "sp_c": 200, "pw_c": 90, "pass_c": 2},
    "Ardoise / Carrelage": {"sp_e": 1500, "pw_e": 45, "sp_c": 500, "pw_c": 0, "pass_c": 0},
    "Cuir 2mm": {"sp_e": 2800, "pw_e": 20, "sp_c": 350, "pw_c": 80, "pass_c": 1},
}


class MachineProfilesMixin:
    def save_machine_settings(self):
        """Mémorise les infos machine (profils + dimensions courantes) via
        QSettings, pour qu'elles soient retrouvées automatiquement au
        prochain lancement, sans avoir besoin de recharger un projet."""
        settings = QSettings("LaserStudioPro", "MachineConfig")
        settings.setValue("machine_bed_w_mm", self.spin_machine_w.value())
        settings.setValue("machine_bed_h_mm", self.spin_machine_h.value())
        if hasattr(self, "spin_machine_focal"):
            settings.setValue("machine_focal_mm", self.spin_machine_focal.value())
        settings.setValue("machine_profiles_json", json.dumps(getattr(self, "machine_profiles", [])))
        if hasattr(self, "combo_machine_profile") and self.combo_machine_profile.currentIndex() >= 0:
            settings.setValue("last_machine_profile", self.combo_machine_profile.currentText())
        if hasattr(self, "combo_lmm_mode"):
            settings.setValue("lmm_mode_index", self.combo_lmm_mode.currentIndex())
        if hasattr(self, "spin_dpi"):
            settings.setValue("lmm_dpi_value", self.spin_dpi.value())
        if hasattr(self, "spin_lmm"):
            settings.setValue("lmm_value", self.spin_lmm.value())

    def load_machine_settings(self):
        settings = QSettings("LaserStudioPro", "MachineConfig")
        w = settings.value("machine_bed_w_mm", None)
        h = settings.value("machine_bed_h_mm", None)
        if w is not None:
            try:
                self.spin_machine_w.setValue(float(w))
            except (TypeError, ValueError):
                pass
        if h is not None:
            try:
                self.spin_machine_h.setValue(float(h))
            except (TypeError, ValueError):
                pass
        focal = settings.value("machine_focal_mm", None)
        if focal is not None and hasattr(self, "spin_machine_focal"):
            try:
                self.spin_machine_focal.setValue(float(focal))
            except (TypeError, ValueError):
                pass
        # Même logique qu'à chaque validation de profil machine : les
        # calques suivent automatiquement la focale dès le démarrage, sans
        # action manuelle.
        if hasattr(self, "layer_widget"):
            self.layer_widget.link_all_to_focal()

        raw_profiles = settings.value("machine_profiles_json", "")
        try:
            self.machine_profiles = json.loads(raw_profiles) if raw_profiles else []
        except (TypeError, ValueError):
            self.machine_profiles = []
        if not self.machine_profiles:
            self.machine_profiles = [{"name": "Machine par défaut",
                                       "w": self.spin_machine_w.value(),
                                       "h": self.spin_machine_h.value()}]
        last_name = settings.value("last_machine_profile", None)
        self._refresh_machine_profile_combo(select_name=last_name)
        # _refresh_machine_profile_combo sélectionne l'index avec les signaux
        # bloqués (pour ne pas déclencher une confirmation ou un effet de
        # bord pendant le simple remplissage de la liste) : il faut donc
        # appliquer nous-mêmes les réglages du profil sélectionné, sinon rien
        # ne les charge réellement au démarrage.
        idx = self.combo_machine_profile.currentIndex() if hasattr(self, "combo_machine_profile") else -1
        if 0 <= idx < len(self.machine_profiles):
            self._apply_machine_profile_fields(self.machine_profiles[idx])

        mode_index = settings.value("lmm_mode_index", None)
        dpi_value = settings.value("lmm_dpi_value", None)
        lmm_value = settings.value("lmm_value", None)
        if hasattr(self, "spin_lmm") and lmm_value is not None:
            try:
                self.spin_lmm.blockSignals(True)
                self.spin_lmm.setValue(float(lmm_value))
                self.spin_lmm.blockSignals(False)
            except (TypeError, ValueError):
                pass
        if hasattr(self, "spin_dpi") and dpi_value is not None:
            try:
                self.spin_dpi.blockSignals(True)
                self.spin_dpi.setValue(float(dpi_value))
                self.spin_dpi.blockSignals(False)
            except (TypeError, ValueError):
                pass
        if hasattr(self, "combo_lmm_mode") and mode_index is not None:
            try:
                self.combo_lmm_mode.setCurrentIndex(int(mode_index))
            except (TypeError, ValueError):
                pass
        # Force dans tous les cas un recalcul de l'écart lignes/mm affiché
        # (et de la pastille de qualité) à partir de l'état actuellement
        # chargé — que le mode restauré soit 'Lignes/mm' (valeur ci-dessus),
        # 'DPI' ou 'Focale laser', sans attendre une interaction manuelle.
        if hasattr(self, "combo_lmm_mode"):
            self.on_lmm_mode_changed(self.combo_lmm_mode.currentIndex())
        elif hasattr(self, "spin_lmm"):
            self._sync_dpi_and_quality_from_lmm(self.spin_lmm.value())

    def _refresh_machine_profile_combo(self, select_name=None):
        if not hasattr(self, "combo_machine_profile"):
            return
        self.combo_machine_profile.blockSignals(True)
        self.combo_machine_profile.clear()
        for p in self.machine_profiles:
            self.combo_machine_profile.addItem(p["name"])
        if select_name:
            idx = self.combo_machine_profile.findText(select_name)
            if idx >= 0:
                self.combo_machine_profile.setCurrentIndex(idx)
        self.combo_machine_profile.blockSignals(False)

    def _capture_machine_profile_fields(self):
        """Rassemble tous les réglages 'machine' actuellement affichés, pour
        les enregistrer dans un profil (nouveau ou mise à jour)."""
        return {
            "w": self.spin_machine_w.value(),
            "h": self.spin_machine_h.value(),
            "focal": self.spin_machine_focal.value() if hasattr(self, "spin_machine_focal") else 0.1,
            "origin": self.combo_origin.currentText() if hasattr(self, "combo_origin") else "Bas-Gauche (0,0)",
            "max_speed": self.spin_machine_max_speed.value(),
            "accel": self.spin_machine_accel.value(),
            "start_gcode": self.txt_start_gcode.toPlainText() if hasattr(self, "txt_start_gcode") else "",
            "end_gcode": self.txt_end_gcode.toPlainText() if hasattr(self, "txt_end_gcode") else "",
            # Réglages GRBL complets ($$, lus depuis la machine ou importés
            # d'un fichier — voir read_grbl_settings/import_grbl_settings) :
            # capturés automatiquement s'ils sont affichés, pour que "Nouvelle
            # Machine" et "Mettre à jour" sauvegardent TOUTE la config
            # machine, pas seulement les dimensions/focale.
            "grbl_settings": self.txt_grbl_settings.toPlainText() if hasattr(self, "txt_grbl_settings") else "",
            # Base de matériaux propre à CETTE machine (voir
            # _apply_machine_profile_fields) : une copie, pour que modifier
            # les matériaux d'un profil n'affecte jamais les autres.
            "materials_db": dict(self.materials_db) if hasattr(self, "materials_db") else dict(DEFAULT_MATERIALS_DB),
        }

    def _apply_machine_profile_fields(self, p):
        """Applique tous les réglages d'un profil machine aux widgets
        correspondants (dimensions, origine, limites, G-code début/fin)."""
        self.spin_machine_w.setValue(p.get("w", self.spin_machine_w.value()))
        self.spin_machine_h.setValue(p.get("h", self.spin_machine_h.value()))
        if hasattr(self, "spin_machine_focal"):
            self.spin_machine_focal.setValue(p.get("focal", self.spin_machine_focal.value()))
        self.spin_machine_max_speed.setValue(p.get("max_speed", 6000.0))
        self.spin_machine_accel.setValue(p.get("accel", 500.0))
        if hasattr(self, "combo_origin") and "origin" in p:
            idx = self.combo_origin.findText(p["origin"])
            if idx >= 0:
                self.combo_origin.setCurrentIndex(idx)
        if hasattr(self, "txt_start_gcode") and "start_gcode" in p:
            self.txt_start_gcode.setPlainText(p["start_gcode"])
        if hasattr(self, "txt_end_gcode") and "end_gcode" in p:
            self.txt_end_gcode.setPlainText(p["end_gcode"])
        # Affiche les réglages GRBL complets ($$) liés à ce profil, s'il y en
        # a — jamais envoyés automatiquement à la machine (voir
        # send_grbl_settings) : la lecture/écriture EEPROM reste toujours une
        # action volontaire.
        if hasattr(self, "txt_grbl_settings") and "grbl_settings" in p:
            self.txt_grbl_settings.setPlainText(p["grbl_settings"])
        # Bascule vers la base de matériaux propre à ce profil — ne propose
        # ainsi que les matériaux pertinents pour la machine sélectionnée
        # (repli sur la base par défaut pour un profil enregistré avant
        # cette liaison materials_db <-> profil).
        if hasattr(self, "combo_mat"):
            self.materials_db = dict(p.get("materials_db", DEFAULT_MATERIALS_DB))
            self.combo_mat.blockSignals(True)
            self.combo_mat.clear()
            self.combo_mat.addItems(list(self.materials_db.keys()))
            self.combo_mat.blockSignals(False)
            if hasattr(self, "apply_material_profile"):
                self.apply_material_profile()

    def _on_machine_profile_selected(self, idx):
        if idx < 0 or idx >= len(self.machine_profiles):
            return
        self._apply_machine_profile_fields(self.machine_profiles[idx])
        # Force le rafraîchissement de l'onglet Image & Filtres (DPI,
        # Lignes/mm, pastille de qualité) — sans ça, si la nouvelle focale
        # est identique à l'ancienne (Qt n'émet alors pas valueChanged) ou
        # absente du profil (anciens profils sans focale enregistrée), rien
        # ne se met à jour tant qu'on ne va pas soi-même rouvrir les options
        # de résolution. Même appel que _on_machine_focal_changed, pour un
        # comportement cohérent partout : Lignes/mm et DPI suivent toujours
        # la focale, peu importe le mode actif.
        if hasattr(self, "_apply_focal_to_lmm"):
            self._apply_focal_to_lmm()
        if hasattr(self, "layer_widget"):
            self.layer_widget.refresh_focal_quality()

    def _add_machine_profile(self):
        name, ok = QInputDialog.getText(
    self,
    tr("machine.new_title"),
    tr("machine.new_prompt")
)
        if not ok or not name.strip():
            return
        profile = {"name": name.strip()}
        profile.update(self._capture_machine_profile_fields())
        self.machine_profiles.append(profile)
        self._refresh_machine_profile_combo(select_name=profile["name"])

    def save_grbl_settings_to_profile(self):
        """Raccourci pratique depuis l'onglet Configuration GRBL : les
        réglages GRBL sont déjà capturés automatiquement par
        _capture_machine_profile_fields, ce bouton se contente donc
        d'appeler la mise à jour du profil actif (comme le bouton "Mettre à
        jour" des Paramètres Machine), sans avoir à changer d'onglet."""
        self._update_machine_profile()

    def _update_machine_profile(self):
        idx = self.combo_machine_profile.currentIndex()
        if idx < 0 or idx >= len(self.machine_profiles):
            return
        name = self.machine_profiles[idx]["name"]
        updated = self._capture_machine_profile_fields()
        updated["name"] = name
        self.machine_profiles[idx] = updated
        # Reboucle automatiquement le pas de remplissage de tous les calques
        # sur la focale qui vient d'être validée : plus besoin de cocher le
        # 🔗 manuellement calque par calque (source d'oubli sinon).
        if hasattr(self, "layer_widget"):
            self.layer_widget.link_all_to_focal()
        QMessageBox.information(
    self,
    tr("machine.updated_title"),
    tr("machine.updated_body").format(name=name)
)

    def _delete_machine_profile(self):
        idx = self.combo_machine_profile.currentIndex()
        if idx < 0 or idx >= len(self.machine_profiles):
            return
        if len(self.machine_profiles) <= 1:
            QMessageBox.warning(
    self,
    tr("machine.cannot_delete_title"),
    tr("machine.cannot_delete_body")
)
            return
        name = self.machine_profiles[idx]["name"]
        reply = QMessageBox.question(
    self,
    tr("machine.delete_title"),
    tr("machine.delete_body").format(name=name),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
)
        if reply == QMessageBox.StandardButton.Yes:
            self.machine_profiles.pop(idx)
            self._refresh_machine_profile_combo()

    def export_material_profiles(self):
        """Exporte tous les profils matériaux courants dans un fichier .json
        séparé, partageable avec d'autres utilisateurs (ex: même machine)."""
        path, _ = QFileDialog.getSaveFileName(
    self,
    tr("material.export_title"),
    "materiaux_laser.json",
    "JSON (*.json)"
)
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.materials_db, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
    self,
    tr("material.export_success_title"),
    tr("material.export_success_body").format(
        count=len(self.materials_db),
        path=path
    )
)
        except Exception as e:
            QMessageBox.critical(
    self,
    tr("laser.error"),
    tr("material.error_export").format(error=e)
)

    def import_material_profiles(self):
        """Importe des profils matériaux depuis un fichier .json exporté par
        cette application (ou par un·e autre utilisateur·rice) : les profils
        du même nom sont mis à jour, les nouveaux sont ajoutés."""
        path, _ = QFileDialog.getOpenFileName(
    self,
    tr("material.import_title"),
    "",
    "JSON (*.json)"
)
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            if not isinstance(imported, dict):
                raise ValueError(tr("material.invalid_file"))
            added, updated = 0, 0
            for name, profile in imported.items():
                if not isinstance(profile, dict):
                    continue
                if name in self.materials_db:
                    updated += 1
                else:
                    added += 1
                self.materials_db[name] = profile
            self.combo_mat.blockSignals(True)
            self.combo_mat.clear()
            self.combo_mat.addItems(list(self.materials_db.keys()))
            self.combo_mat.blockSignals(False)
            QMessageBox.information(
    self,
    tr("material.import_success_title"),
    tr("material.import_success_body").format(
        added=added,
        updated=updated
    )
)
        except Exception as e:
            QMessageBox.critical(
    self,
    tr("laser.error"),
    tr("material.error_import").format(error=e)
)

    def apply_material_profile(self):
        mat_name = self.combo_mat.currentText()
        if mat_name in self.materials_db:
            p = self.materials_db[mat_name]
            self.spin_speed_engrave.setValue(p['sp_e'])
            self.spin_power_engrave.setValue(p['pw_e'])
            self.spin_speed_cut.setValue(p['sp_c'])
            self.spin_power_cut.setValue(p['pw_c'])
            self.spin_passes_cut.setValue(p['pass_c'])

    def save_material_profile(self):
        mat_name = self.combo_mat.currentText()
        self.materials_db[mat_name] = {
            "sp_e": self.spin_speed_engrave.value(),
            "pw_e": self.spin_power_engrave.value(),
            "sp_c": self.spin_speed_cut.value(),
            "pw_c": self.spin_power_cut.value(),
            "pass_c": self.spin_passes_cut.value()
        }
        QMessageBox.information(
    self,
    tr("material.saved_title"),
    tr("material.saved_body").format(name=mat_name)
)

    def add_material_profile(self):
        name, ok = QInputDialog.getText(
    self,
    tr("material.new_profile_title"),
    tr("material.new_profile_prompt")
)
        if ok and name.strip():
            name = name.strip()
            self.materials_db[name] = {
                "sp_e": self.spin_speed_engrave.value(),
                "pw_e": self.spin_power_engrave.value(),
                "sp_c": self.spin_speed_cut.value(),
                "pw_c": self.spin_power_cut.value(),
                "pass_c": self.spin_passes_cut.value()
            }
            self.combo_mat.addItem(name)
            self.combo_mat.setCurrentText(name)

    def delete_material_profile(self):
        mat_name = self.combo_mat.currentText()
        if mat_name == "Personnalisé":
            QMessageBox.warning(
    self,
    tr("material.delete_forbidden_title"),
    tr("material.delete_forbidden_body")
)
            return
        reply = QMessageBox.question(
    self,
    tr("material.delete_title"),
    tr("material.delete_body").format(name=mat_name),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
)
        if reply == QMessageBox.StandardButton.Yes:
            del self.materials_db[mat_name]
            self.combo_mat.removeItem(self.combo_mat.currentIndex())

    def on_mat_mode_changed(self, index):
        is_gravure = (index == 0)
        self.lbl_mat_p1.setText(tr("ui.mat_min_power") if is_gravure else tr("ui.mat_unique_power"))
        self.spin_mat_max_p.setVisible(is_gravure)
        self.form_matrix.labelForField(self.spin_mat_max_p).setVisible(is_gravure)
        self.spin_mat_steps_p.setVisible(is_gravure)
        self.form_matrix.labelForField(self.spin_mat_steps_p).setVisible(is_gravure)

        self.spin_mat_min_passes.setVisible(not is_gravure)
        self.form_matrix.labelForField(self.spin_mat_min_passes).setVisible(not is_gravure)
        self.spin_mat_max_passes.setVisible(not is_gravure)
        self.form_matrix.labelForField(self.spin_mat_max_passes).setVisible(not is_gravure)
        self.spin_mat_steps_passes.setVisible(not is_gravure)
        self.form_matrix.labelForField(self.spin_mat_steps_passes).setVisible(not is_gravure)

        self.spin_mat_lmm.setVisible(is_gravure)
        self.spin_mat_lmm.dpi_label.setVisible(is_gravure)
        self.form_matrix.labelForField(self.spin_mat_lmm.dpi_row_layout).setVisible(is_gravure)

    def on_overscan_mode_changed(self, index):
        self.overscan_stacked.setCurrentIndex(index)
