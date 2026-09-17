"""Sauvegarde et chargement d'un projet complet (.json), projets récents,
et sauvegarde automatique périodique."""
from PyQt6.QtWidgets import (QFileDialog, QMessageBox)
from PyQt6.QtCore import QSettings
from PIL import Image
from io import BytesIO
import base64
import json
import os

from app_utils import get_app_dir

AUTOSAVE_FILENAME = "laser_studio_pro_autosave.json"


class ProjectIOMixin:
    def _get_project_data(self):
        """Rassemble l'état courant du projet dans un dictionnaire — utilisé
        à la fois par la sauvegarde manuelle et la sauvegarde automatique."""
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
        return proj_data

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder Projet Laser", "", "Projet Laser (*.json)")
        if not path:
            return
        try:
            proj_data = self._get_project_data()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(proj_data, f, indent=4)
            self._add_to_recent_projects(path)
            self._clear_autosave()
            QMessageBox.information(self, "Sauvegarde", "Projet sauvegardé avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder le projet :\n{e}")

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir Projet Laser", "", "Projet Laser (*.json)")
        if not path:
            return
        self._load_project_from_path(path)

    def _load_project_from_path(self, path):
        """Charge un projet depuis un chemin donné — factorisé pour être
        réutilisé par le menu 'Projets récents' et la récupération de
        sauvegarde automatique, sans repasser par la boîte de dialogue."""
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
            self._add_to_recent_projects(path)
            QMessageBox.information(self, "Succès", "Projet chargé avec succès.")

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec du chargement du projet :\n{e}")

    # ------------------------------------------------------------------
    # Projets récents
    # ------------------------------------------------------------------
    def _add_to_recent_projects(self, path):
        settings = QSettings("LaserStudioPro", "UIConfig")
        recents = settings.value("recent_projects", [])
        if isinstance(recents, str):
            recents = [recents]
        recents = list(recents or [])
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        recents = recents[:10]
        settings.setValue("recent_projects", recents)
        self._refresh_recent_projects_menu()

    def _refresh_recent_projects_menu(self):
        if not hasattr(self, "menu_recent_projects"):
            return
        self.menu_recent_projects.clear()
        settings = QSettings("LaserStudioPro", "UIConfig")
        recents = settings.value("recent_projects", [])
        if isinstance(recents, str):
            recents = [recents]
        recents = [p for p in (recents or []) if os.path.exists(p)]
        if not recents:
            action_none = self.menu_recent_projects.addAction("(aucun)")
            action_none.setEnabled(False)
            return
        for path in recents:
            label = os.path.basename(path)
            action = self.menu_recent_projects.addAction(label)
            action.setToolTip(path)
            action.triggered.connect(lambda checked=False, p=path: self._load_project_from_path(p))

    # ------------------------------------------------------------------
    # Sauvegarde automatique périodique
    # ------------------------------------------------------------------
    def autosave_project(self):
        """Sauvegarde silencieuse de l'état courant, appelée périodiquement
        par un QTimer. Ne doit jamais interrompre l'utilisateur — une
        erreur ici est simplement ignorée."""
        try:
            proj_data = self._get_project_data()
            path = os.path.join(get_app_dir(), AUTOSAVE_FILENAME)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(proj_data, f)
        except Exception:
            pass

    def _clear_autosave(self):
        try:
            path = os.path.join(get_app_dir(), AUTOSAVE_FILENAME)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def check_for_autosave_recovery(self):
        """Appelé une fois au démarrage : propose de récupérer la dernière
        sauvegarde automatique si l'application a été fermée anormalement
        (plantage, coupure de courant) avant un enregistrement manuel."""
        path = os.path.join(get_app_dir(), AUTOSAVE_FILENAME)
        if not os.path.exists(path):
            return
        reply = QMessageBox.question(
            self, "Récupération de session",
            "Une sauvegarde automatique d'une session précédente a été trouvée "
            "(probablement suite à une fermeture inattendue).\n\n"
            "Veux-tu la récupérer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._load_project_from_path(path)
        self._clear_autosave()
