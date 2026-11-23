"""Outils de test du JobController : boîtes de dialogue simulées et contrôleur
prêt à l'emploi, sans fenêtre."""
from laser_studio.controllers.job import JobController
from laser_studio.models.grbl import GrblConfig
from laser_studio.models.image_settings import ImageSettings
from laser_studio.models.layers import LayersModel
from laser_studio.models.machine import MachineConfig


class FakeDialogs:
    """Même interface que UserDialogs : enregistre les messages et répond à
    la place de l'utilisateur (`answer` pour confirm / ask_yes_no, `path`
    pour les choix de fichier)."""

    def __init__(self, answer=True, path="", text=None):
        self.answer, self.path, self.text = answer, path, text
        self.calls = []

    def _record(self, kind, title, text):
        self.calls.append((kind, title, text))

    def info(self, title, text):
        self._record("info", title, text)

    def warning(self, title, text):
        self._record("warning", title, text)

    def error(self, title, text):
        self._record("error", title, text)

    def confirm(self, title, text):
        self._record("confirm", title, text)
        return self.answer

    def confirm_default_no(self, title, text):
        self._record("confirm_default_no", title, text)
        return self.answer

    def confirm_yes_no(self, title, text):
        self._record("confirm_yes_no", title, text)
        return self.answer

    def ask_text(self, title, label):
        self._record("ask_text", title, label)
        return self.text

    def ask_yes_no(self, title, text):
        self._record("ask_yes_no", title, text)
        return self.answer

    def choose(self, title, text, choices):
        """Renvoie `self.choice` (clé), sinon la première proposée."""
        self._record("choose", title, text)
        return getattr(self, "choice", choices[0][0])

    def save_file(self, title, default_name, file_filter):
        self._record("save_file", title, default_name)
        return self.path

    def open_file(self, title, file_filter):
        self._record("open_file", title, "")
        return self.path

    def open_folder(self, title):
        self._record("open_folder", title, "")
        return self.path

    def kinds(self):
        return [c[0] for c in self.calls]

    def last_text(self, kind):
        return [c[2] for c in self.calls if c[0] == kind][-1]


def geometry(**kw):
    g = {'width_mm': 40.0, 'height_mm': 30.0, 'origin_pos': "bottom_left", 'offset_x': 0.0, 'offset_y': 0.0}
    g.update(kw)
    return g


def make_job(image=None, objects=(), dialogs=None, geometry_kw=None, svg_path=None):
    """(JobController, FakeDialogs) avec des modèles neufs."""
    dialogs = dialogs or FakeDialogs()
    holder = {"image": image, "objects": list(objects)}
    job = JobController(
        LayersModel(), GrblConfig(), MachineConfig(), ImageSettings(), dialogs,
        geometry=lambda: geometry(**(geometry_kw or {})),
        image=lambda: holder["image"],
        svg_path=lambda: svg_path,
        vector_objects=lambda: holder["objects"],
        lines_mm=lambda: 10.0,
        material_summary=lambda: "Matière : fond clair",
    )
    job.holder = holder
    return job, dialogs


def memory_preferences(test, **initial):
    """Préférences en mémoire pendant le test `test` (rien d'écrit chez l'utilisateur) ; renvoie les
    magasins par fichier : stores["UIConfig"].values, stores["MachineConfig"].values…"""
    from laser_studio.core import preferences
    context = preferences.in_memory(**initial)
    stores = context.__enter__()
    test.addCleanup(context.__exit__, None, None, None)
    return stores


def start_memory_preferences(cls):
    """Préférences en mémoire pour toute une classe de tests : à appeler dans setUpClass, AVANT de
    construire la fenêtre. Changer XDG_CONFIG_HOME ne suffit pas : QSettings garde le dossier choisi à
    sa première utilisation dans le processus, et la fenêtre écrirait chez l'utilisateur."""
    from laser_studio.core import preferences
    context = preferences.in_memory()
    stores = context.__enter__()
    cls.addClassCleanup(context.__exit__, None, None, None)
    return stores
