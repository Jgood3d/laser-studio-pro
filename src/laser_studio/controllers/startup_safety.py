"""Quand afficher l'avertissement de sécurité du démarrage.

Comme les « astuces du jour » de certaines applications, l'avertissement a
une case « Ne plus afficher à chaque démarrage ». Cochée, il ne revient
plus qu'en rappel, tous les REMINDER_EVERY démarrages. La variable
d'environnement NOWARNING (toute valeur sauf vide ou « 0 ») le désactive
complètement, pour les tests.

    policy = StartupSafetyPolicy(QSettings("LaserStudioPro", "UIConfig"))
    if policy.should_show_at_launch():
        accepted, hide = confirm_startup_safety(None, policy.hidden())
        if accepted:
            policy.record(hide)

`settings` : tout objet qui offre value(clé, défaut) et setValue(clé,
valeur), comme QSettings (un dictionnaire adapté suffit dans les tests).
"""

import os

# Rappel quand la case « Ne plus afficher » est cochée : un démarrage sur 30.
REMINDER_EVERY = 30
# Variable d'environnement qui désactive l'avertissement (tests).
DISABLE_ENV = "NOWARNING"

HIDDEN_KEY = "startup_safety/hidden"
COUNT_KEY = "startup_safety/launches_since_shown"


def _as_bool(value):
    """QSettings rend parfois les booléens sous forme de texte."""
    return value in (True, "true", "True", "1", 1)


class StartupSafetyPolicy:
    """Règle d'affichage de l'avertissement de sécurité au démarrage."""

    def __init__(self, settings, environ=None):
        self._settings = settings
        self._environ = os.environ if environ is None else environ

    def disabled(self):
        """Vrai si NOWARNING désactive l'avertissement."""
        return self._environ.get(DISABLE_ENV, "") not in ("", "0")

    def hidden(self):
        """Vrai si l'utilisateur a coché « Ne plus afficher »."""
        return _as_bool(self._settings.value(HIDDEN_KEY, False))

    def should_show_at_launch(self):
        """À appeler une fois par démarrage : faut-il afficher l'avertissement ?

        Toujours, sauf si la case est cochée : alors un démarrage sur
        REMINDER_EVERY seulement (ce démarrage compte). Jamais avec NOWARNING.
        """
        if self.disabled():
            return False
        if not self.hidden():
            return True
        try:
            count = int(self._settings.value(COUNT_KEY, 0)) + 1
        except (TypeError, ValueError):
            count = 1
        if count >= REMINDER_EVERY:
            self._settings.setValue(COUNT_KEY, 0)
            return True
        self._settings.setValue(COUNT_KEY, count)
        return False

    def record(self, hide):
        """L'utilisateur a validé l'avertissement, case « Ne plus afficher »
        cochée (`hide`) ou non. Le compte des démarrages repart de zéro."""
        self._settings.setValue(HIDDEN_KEY, bool(hide))
        self._settings.setValue(COUNT_KEY, 0)
