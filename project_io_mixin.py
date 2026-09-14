"""Sauvegarde et chargement d'un projet complet (.json)."""
from PyQt6.QtWidgets import (QFileDialog, QMessageBox)
from PIL import Image
from io import BytesIO
import base64
import json


class ProjectIOMixin:
    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder Projet Laser", "", "Projet Laser (*.json)")
        if not path:
            return

        proj_data = {
            "w_mm": self.spin_w.value(),
            "h_mm": self.spin_h.value(),
            "machine_bed_w_mm": self.spin_machine_w.value(),
            "machine_bed_h_mm": self.spin_machine_h.value(),
            "origin_pos": self.combo_origin.currentText(),
            "offset_x": self.spin_off_x.value(),
            "offset_y": self.spin_off_y.value(),
            "bright": self.slider_bright.value(),
            "contrast": self.slider_contrast.value(),
            "gamma": self.slider_gamma.value(),
            "invert": self.chk_invert.isChecked(),
            "mirror_h": self.chk_mirror_h.isChecked(),
            "mirror_v": self.chk_mirror_v.isChecked(),
            "algo": self.combo_algo.currentText(),
            "lmm": self.spin_lmm.value(),
            "speed_engrave": self.spin_speed_engrave.value(),
            "power_engrave": self.spin_power_engrave.value(),
            "enable_cut": self.chk_enable_cut.isChecked(),
            "speed_cut": self.spin_speed_cut.value(),
            "power_cut": self.spin_power_cut.value(),
            "passes_cut": self.spin_passes_cut.value(),
            "materials_db": self.materials_db,
            "raw_image_b64": None,
            "svg_path": self.loaded_svg_path,
            "layers": self.layer_manager.to_list(),
            "vector_objects": self.vector_canvas.serialize_objects() if hasattr(self, "vector_canvas") else []
        }

        if self.raw_image:
            buffer = BytesIO()
            self.raw_image.save(buffer, format="PNG")
            proj_data["raw_image_b64"] = base64.b64encode(buffer.getvalue()).decode('utf-8')

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(proj_data, f, indent=4)
            QMessageBox.information(self, "Sauvegarde", "Projet sauvegardé avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le projet :\n{e}")

    def load_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ouvrir Projet Laser", "", "Projet Laser (*.json)")
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                proj_data = json.load(f)

            self.spin_w.setValue(proj_data.get("w_mm", 100.0))
            self.spin_h.setValue(proj_data.get("h_mm", 100.0))
            self.spin_machine_w.setValue(proj_data.get("machine_bed_w_mm", self.spin_machine_w.value()))
            self.spin_machine_h.setValue(proj_data.get("machine_bed_h_mm", self.spin_machine_h.value()))
            self.combo_origin.setCurrentText(proj_data.get("origin_pos", "Bas-Gauche (0,0)"))
            self.spin_off_x.setValue(proj_data.get("offset_x", 0.0))
            self.spin_off_y.setValue(proj_data.get("offset_y", 0.0))

            self.slider_bright.setValue(proj_data.get("bright", 0))
            self.slider_contrast.setValue(proj_data.get("contrast", 0))
            self.slider_gamma.setValue(proj_data.get("gamma", 100))
            self.chk_invert.setChecked(proj_data.get("invert", False))
            self.chk_mirror_h.setChecked(proj_data.get("mirror_h", False))
            self.chk_mirror_v.setChecked(proj_data.get("mirror_v", False))
            self.combo_algo.setCurrentText(proj_data.get("algo", "Floyd-Steinberg"))
            self.spin_lmm.setValue(proj_data.get("lmm", 10.0))

            self.spin_speed_engrave.setValue(proj_data.get("speed_engrave", 2000))
            self.spin_power_engrave.setValue(proj_data.get("power_engrave", 30))
            
            self.chk_enable_cut.setChecked(proj_data.get("enable_cut", False))
            
            self.spin_speed_cut.setValue(proj_data.get("speed_cut", 300))
            self.spin_power_cut.setValue(proj_data.get("power_cut", 90))
            self.spin_passes_cut.setValue(proj_data.get("passes_cut", 2))

            if "materials_db" in proj_data:
                self.materials_db = proj_data["materials_db"]
                self.combo_mat.clear()
                self.combo_mat.addItems(list(self.materials_db.keys()))

            img_b64 = proj_data.get("raw_image_b64")
            if img_b64:
                img_data = base64.b64decode(img_b64)
                self.raw_image = Image.open(BytesIO(img_data)).convert("L")
                self.display_source_image()

            self.loaded_svg_path = proj_data.get("svg_path")

            if "layers" in proj_data:
                self.layer_manager.load_list(proj_data["layers"])
                self.layer_widget.refresh()
            if hasattr(self, "vector_canvas"):
                self.vector_canvas.load_objects(proj_data.get("vector_objects"))
                self.update_vector_work_area()

            self.update_image_processing()
            QMessageBox.information(self, "Succès", "Projet chargé avec succès.")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec du chargement du projet :\n{e}")
