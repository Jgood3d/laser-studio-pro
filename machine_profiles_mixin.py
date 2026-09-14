"""Gestion des profils machine et des profils matériaux (sauvegarde/chargement via QSettings)."""
from PyQt6.QtWidgets import (QMessageBox, QInputDialog)
from PyQt6.QtCore import QSettings
import json


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

    def _on_machine_profile_selected(self, idx):
        if idx < 0 or idx >= len(self.machine_profiles):
            return
        self._apply_machine_profile_fields(self.machine_profiles[idx])

    def _add_machine_profile(self):
        name, ok = QInputDialog.getText(self, "Nouvelle Machine", "Nom de la machine :")
        if not ok or not name.strip():
            return
        profile = {"name": name.strip()}
        profile.update(self._capture_machine_profile_fields())
        self.machine_profiles.append(profile)
        self._refresh_machine_profile_combo(select_name=profile["name"])

    def _update_machine_profile(self):
        idx = self.combo_machine_profile.currentIndex()
        if idx < 0 or idx >= len(self.machine_profiles):
            return
        name = self.machine_profiles[idx]["name"]
        updated = self._capture_machine_profile_fields()
        updated["name"] = name
        self.machine_profiles[idx] = updated
        QMessageBox.information(self, "Profil mis à jour",
                                 f"Le profil « {name} » a été mis à jour avec les réglages actuels "
                                 "(dimensions, origine, limites, G-code début/fin).")

    def _delete_machine_profile(self):
        idx = self.combo_machine_profile.currentIndex()
        if idx < 0 or idx >= len(self.machine_profiles):
            return
        if len(self.machine_profiles) <= 1:
            QMessageBox.warning(self, "Impossible", "Il doit rester au moins un profil de machine.")
            return
        name = self.machine_profiles[idx]["name"]
        reply = QMessageBox.question(
            self, "Supprimer le profil", f"Supprimer le profil « {name} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.machine_profiles.pop(idx)
            self._refresh_machine_profile_combo()

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
        QMessageBox.information(self, "Profil Enregistré", f"Les paramètres pour '{mat_name}' ont été sauvegardés.")

    def add_material_profile(self):
        name, ok = QInputDialog.getText(self, "Nouveau Profil", "Nom du matériau :")
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
            QMessageBox.warning(self, "Action Interdite", "Le profil par défaut ne peut être supprimé.")
            return
        reply = QMessageBox.question(self, "Suppression", f"Supprimer le profil '{mat_name}' ?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.materials_db[mat_name]
            self.combo_mat.removeItem(self.combo_mat.currentIndex())

    def on_mat_mode_changed(self, index):
        is_gravure = (index == 0)
        self.lbl_mat_p1.setText("Puissance Min (%):" if is_gravure else "Puissance Unique (%):")
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
