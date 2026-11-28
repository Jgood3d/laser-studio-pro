"""Projet complet (.json) : enregistrement, ouverture, projets récents et
sauvegarde automatique périodique."""

import base64
import json
import os
from io import BytesIO

from PIL import Image

from laser_common.files import atomic_write_json, get_background_writer
from laser_studio.core.paths import get_autosave_dir
from laser_studio.i18n import tr
from laser_studio.core.preferences import ui_preferences
from laser_studio.core.debug_log import get_logger

log = get_logger()

AUTOSAVE_FILENAME = "laser_studio_pro_autosave.json"
# Projets récents gardés dans le menu Fichier.
# Image d'un projet : 89 Mpx (Image.MAX_IMAGE_PIXELS de PIL), soit 400 x 400 mm à 23 lignes/mm.
MAX_PROJECT_IMAGE_PIXELS = 89_478_485
MAX_RECENT_PROJECTS = 10


class ProjectController:
    """Fichier du projet : format, boîtes Enregistrer / Ouvrir, projets
    récents, sauvegarde automatique et sa récupération.

    Il ne connaît pas les champs de la fenêtre : un projet est un
    dictionnaire, que la fenêtre fournit et réapplique.

        project = ProjectController(
            self, capture=state.capture_project, restore=state.restore_project,
            show_recent_projects=..., log_to_console=...,
        )
        actions.save_project_requested.connect(project.save)

    `capture()` : (état du projet en dictionnaire, image source PIL ou
    None). `restore(data, image)` : réapplique un projet ouvert (image PIL
    ou None). `show_recent_projects(paths)` : met à jour le menu Fichier.
    `log_to_console(text)` : message pour l'utilisateur (barre d'état).
    `dialogs` : UserDialogs (par défaut, celles de `parent`).
    """

    def __init__(
        self, parent, capture, restore, show_recent_projects, log_to_console, dialogs=None
    ):
        # Boîtes de dialogue (UserDialogs) : celles de la fenêtre, ou un objet
        # qui répond à la place de l'utilisateur dans les tests.
        if dialogs is None:
            from laser_studio.ui.user_dialogs import UserDialogs
            dialogs = UserDialogs(parent)
        self._dialogs = dialogs
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
        """Image en niveaux de gris, depuis son PNG en base64. Sa taille est lue dans l'en-tête avant tout
        décodage : un projet reçu d'un tiers ne peut pas saturer la mémoire avec une image géante (PIL ne
        refuse qu'au-delà du double de Image.MAX_IMAGE_PIXELS)."""
        image = Image.open(BytesIO(base64.b64decode(text)))
        if image.width * image.height > MAX_PROJECT_IMAGE_PIXELS:
            raise ValueError(tr("project.image_too_large").format(width=image.width, height=image.height))
        return image.convert("L")

    # -- enregistrer, ouvrir

    def save(self):
        """Enregistre le projet. True s'il l'a été (False : annulé ou
        erreur)."""
        path = self._dialogs.save_file(tr("project.save_title"), "", tr("project.file_filter"))
        if not path:
            return False
        try:
            atomic_write_json(path, self.data(), indent=4)
            self._add_to_recent_projects(path)
            self.discard_autosave()
            self._dialogs.notify(tr("project.save_success"))
            return True
        except Exception as e:
            self._dialogs.error(tr("laser.error"), tr("project.save_error").format(error=e))
            return False

    def open(self):
        """Ouvre un projet choisi dans une boîte de dialogue."""
        path = self._dialogs.open_file(tr("project.open_title"), tr("project.file_filter"))
        if path:
            self.open_path(path)

    def open_path(self, path):
        """Ouvre le projet `path` (menu « Projets récents », récupération
        de la sauvegarde automatique...). Renvoie True s'il est ouvert."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            encoded = data.get("raw_image_b64")
            image = self.decode_image(encoded) if encoded else None
            self._restore(data, image)
            self._add_to_recent_projects(path)
            self._dialogs.notify(tr("project.load_success"))
        except Exception as e:
            self._dialogs.error(tr("laser.error"), tr("project.load_error").format(error=e))
            return False
        return True

    # -- projets récents

    @staticmethod
    def _recent_projects():
        return ui_preferences().get_list("recent_projects")

    def _add_to_recent_projects(self, path):
        recents = self._recent_projects()
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        ui_preferences().set("recent_projects", recents[:MAX_RECENT_PROJECTS])
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
            log.exception("Sauvegarde automatique du projet impossible")

    def discard_autosave(self):
        """Oublie la sauvegarde automatique (projet enregistré, ou fermeture
        voulue sans enregistrer)."""
        try:
            path = os.path.join(get_autosave_dir(), AUTOSAVE_FILENAME)
            # Annule aussi une écriture en cours, pour qu'elle ne recrée pas
            # le fichier juste après un enregistrement.
            get_background_writer().discard(path)
        except Exception:
            log.warning("Sauvegarde automatique non oubliée", exc_info=True)

    def offer_autosave_recovery(self):
        """Au démarrage : propose de récupérer la dernière sauvegarde
        automatique, si l'application a été fermée anormalement (plantage,
        coupure de courant) avant un enregistrement."""
        path = os.path.join(get_autosave_dir(), AUTOSAVE_FILENAME)
        if not os.path.exists(path):
            return
        if self._dialogs.confirm_default_no(tr("project.autosave_recovery_title"),
                                            tr("project.autosave_recovery_body")) and not self.open_path(path):
            return                     # récupération ratée : la sauvegarde reste pour un nouvel essai
        self.discard_autosave()
