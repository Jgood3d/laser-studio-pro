"""Projet complet (.json) : enregistrement, ouverture, projets récents et
sauvegarde automatique périodique."""

import base64
import json
import os
from io import BytesIO

from PIL import Image
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from app_utils import (
    atomic_write_json,
    get_autosave_dir,
    get_background_writer,
)
from i18n import tr

AUTOSAVE_FILENAME = "laser_studio_pro_autosave.json"
# Projets récents gardés dans le menu Fichier.
MAX_RECENT_PROJECTS = 10


class ProjectController:
    """Fichier du projet : format, boîtes Enregistrer / Ouvrir, projets
    récents, sauvegarde automatique et sa récupération.

    Il ne connaît pas les champs de la fenêtre : un projet est un
    dictionnaire, que la fenêtre fournit et réapplique.

        project = ProjectController(
            self, capture=self._capture_project, restore=self._restore_project,
            show_recent_projects=..., log_to_console=...,
        )
        actions.save_project_requested.connect(project.save)

    `capture()` : (état du projet en dictionnaire, image source PIL ou
    None). `restore(data, image)` : réapplique un projet ouvert (image PIL
    ou None). `show_recent_projects(paths)` : met à jour le menu Fichier.
    `log_to_console(text)` : écrit dans la console.
    """

    def __init__(
        self, parent, capture, restore, show_recent_projects, log_to_console
    ):
        self._parent = parent
        self._capture = capture
        self._restore = restore
        self._show_recent_projects = show_recent_projects
        self._log_to_console = log_to_console

    # -- format

    def data(self, encode_image=True):
        """Projet en dictionnaire, prêt pour le JSON. encode_image=False
        laisse « raw_image_b64 » à None : l'encodage PNG + base64, de loin
        le plus lent, est alors fait par l'appelant (voir autosave)."""
        data, image = self._capture()
        data["raw_image_b64"] = None
        if image and encode_image:
            data["raw_image_b64"] = self.encode_image(image)
        return data

    @staticmethod
    def encode_image(image):
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def decode_image(text):
        """Image en niveaux de gris, depuis son PNG en base64."""
        return Image.open(BytesIO(base64.b64decode(text))).convert("L")

    # -- enregistrer, ouvrir

    def save(self):
        """Enregistre le projet. True s'il l'a été (False : annulé ou
        erreur)."""
        path, _ = QFileDialog.getSaveFileName(
            self._parent,
            tr("project.save_title"),
            "",
            tr("project.file_filter"),
        )
        if not path:
            return False
        try:
            atomic_write_json(path, self.data(), indent=4)
            self._add_to_recent_projects(path)
            self.discard_autosave()
            QMessageBox.information(
                self._parent,
                tr("project.save_success_title"),
                tr("project.save_success"),
            )
            return True
        except Exception as e:
            QMessageBox.critical(
                self._parent,
                tr("laser.error"),
                tr("project.save_error").format(error=e),
            )
            return False

    def open(self):
        """Ouvre un projet choisi dans une boîte de dialogue."""
        path, _ = QFileDialog.getOpenFileName(
            self._parent,
            tr("project.open_title"),
            "",
            tr("project.file_filter"),
        )
        if path:
            self.open_path(path)

    def open_path(self, path):
        """Ouvre le projet `path` (menu « Projets récents », récupération
        de la sauvegarde automatique...)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            encoded = data.get("raw_image_b64")
            image = self.decode_image(encoded) if encoded else None
            self._restore(data, image)
            self._add_to_recent_projects(path)
            QMessageBox.information(
                self._parent,
                tr("project.load_success_title"),
                tr("project.load_success"),
            )
        except Exception as e:
            QMessageBox.critical(
                self._parent,
                tr("laser.error"),
                tr("project.load_error").format(error=e),
            )

    # -- projets récents

    @staticmethod
    def _recent_projects():
        recents = QSettings("LaserStudioPro", "UIConfig").value(
            "recent_projects", []
        )
        if isinstance(recents, str):
            recents = [recents]
        return list(recents or [])

    def _add_to_recent_projects(self, path):
        recents = self._recent_projects()
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        QSettings("LaserStudioPro", "UIConfig").setValue(
            "recent_projects", recents[:MAX_RECENT_PROJECTS]
        )
        self.refresh_recent_projects()

    def refresh_recent_projects(self):
        """Projets récents encore présents sur le disque, dans le menu."""
        self._show_recent_projects(
            [path for path in self._recent_projects() if os.path.exists(path)]
        )

    # -- sauvegarde automatique

    def autosave(self):
        """Sauvegarde silencieuse de l'état courant, appelée
        périodiquement. Ne doit jamais interrompre l'utilisateur : une
        erreur ici est simplement ignorée."""
        try:
            path = os.path.join(get_autosave_dir(), AUTOSAVE_FILENAME)
            writer = get_background_writer()
            # Une erreur de la sauvegarde précédente (disque plein...) est
            # signalée UNE fois dans la console, au lieu d'être ignorée.
            error = writer.pop_error(path)
            if error is not None:
                self._log_to_console(
                    tr("project.autosave_failed").format(error=error)
                )
            # Ici, seulement la collecte de l'état (rapide) et une copie de
            # l'image (quelques ms) ; l'encodage PNG / base64, le JSON et
            # l'écriture se font dans le thread d'écriture.
            data, image = self._capture()
            data["raw_image_b64"] = None
            image = image.copy() if image else None

            def produce():
                if image is not None:
                    data["raw_image_b64"] = self.encode_image(image)
                return json.dumps(data)

            writer.submit(path, produce)
        except Exception:
            pass

    def discard_autosave(self):
        """Oublie la sauvegarde automatique (projet enregistré, ou fermeture
        voulue sans enregistrer)."""
        try:
            path = os.path.join(get_autosave_dir(), AUTOSAVE_FILENAME)
            # Annule aussi une écriture en cours, pour qu'elle ne recrée pas
            # le fichier juste après un enregistrement.
            get_background_writer().discard(path)
        except Exception:
            pass

    def offer_autosave_recovery(self):
        """Au démarrage : propose de récupérer la dernière sauvegarde
        automatique, si l'application a été fermée anormalement (plantage,
        coupure de courant) avant un enregistrement."""
        path = os.path.join(get_autosave_dir(), AUTOSAVE_FILENAME)
        if not os.path.exists(path):
            return
        reply = QMessageBox.question(
            self._parent,
            tr("project.autosave_recovery_title"),
            tr("project.autosave_recovery_body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.open_path(path)
        self.discard_autosave()
