"""Prise en main au premier lancement : quatre étapes pour graver au bon endroit dès le premier travail (choisir
sa machine, se connecter, faire un homing, essayer un cadrage), sans lire l'aide d'abord. La fenêtre
(ui/dialogs/first_steps/) s'ouvre au premier démarrage, puis depuis Aide › Premiers pas.

    steps = FirstStepsController(connection, {"machine": ..., "connect": ..., "home": ..., "frame": ...},
                                 ui_preferences())
    if steps.should_show_at_launch():
        open_first_steps(window, steps)
    steps.run("home")              # bouton de l'étape
    steps.done()                   # {"machine": True, "connect": True, "home": False, "frame": False}
"""
from PyQt6.QtCore import QObject, pyqtSignal

STEPS = ("machine", "connect", "home", "frame")
SHOW_KEY = "first_steps/show_at_launch"


class FirstStepsController(QObject):
    """`connection` : MachineConnection (connecté, homing fait) ; `actions` : étape -> fonction qui la lance
    (fenêtre du catalogue, connexion, homing, cadrage) ; `settings` : Preferences (core/preferences.py).

    Une étape est faite quand l'état du graveur le montre (connecté, homing réussi) ; le choix de la machine
    et le cadrage, sans état à relire, le sont une fois lancés (le cadrage, graveur connecté).
    Signal changed() : une étape vient peut-être de changer d'état."""

    changed = pyqtSignal()

    def __init__(self, connection, actions, settings, parent=None):
        super().__init__(parent)
        self.connection = connection
        self.actions = actions
        self.settings = settings
        self._launched = set()
        connection.connection_changed.connect(lambda _connected: self.changed.emit())
        connection.state_changed.connect(lambda _state: self.changed.emit())

    def should_show_at_launch(self):
        """Au premier démarrage, et ensuite tant que la case « Afficher au démarrage » reste cochée."""
        return self.settings.get_bool(SHOW_KEY, True)

    def set_show_at_launch(self, show):
        self.settings.set(SHOW_KEY, bool(show))

    def run(self, step):
        """Lance l'étape `step` (une clé de STEPS)."""
        self._launched.add(step)
        self.actions[step]()
        self.changed.emit()

    def done(self):
        """État de chaque étape : {clé: fait}."""
        connected = self.connection.is_connected()
        return {
            "machine": "machine" in self._launched,
            "connect": connected,
            "home": connected and self.connection.homed,
            "frame": connected and "frame" in self._launched,
        }
