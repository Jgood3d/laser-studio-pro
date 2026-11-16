"""Journal des changements des modèles (LASER_STUDIO_DEBUG=1).

Les réglages saisis au clavier dans un champ texte (G-Code de début et de
fin, réglages $$, nom d'un calque) changent à chaque frappe : le modèle est
bien mis à jour à chaque fois (la génération lit toujours la bonne valeur),
mais le journal n'écrit qu'UNE ligne, une fois la saisie terminée
(DELAY_MS sans frappe), avec la valeur d'avant la saisie et la valeur
finale.
"""
import logging

from PyQt6.QtCore import QCoreApplication, QObject, QTimer

from laser_studio.core.debug_log import LOGGER_NAME

log = logging.getLogger(f"{LOGGER_NAME}.modeles")


def short(value, limit=60):
    """Valeur lisible dans le journal (les longs textes sont coupés, les
    retours à la ligne restent visibles sous la forme \\n)."""
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


class ChangeLog(QObject):
    """Écrit les changements d'un modèle : tout de suite (now) ou regroupés
    jusqu'à la fin de la saisie (later)."""

    DELAY_MS = 1500

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = {}
        self._timer = None

    @staticmethod
    def now(prefix, changes, before):
        """Écrit « préfixe réglage ancien -> nouveau, … » sur une ligne."""
        if changes:
            log.info("%s %s", prefix,
                     ", ".join(f"{k} {short(before[k])} -> {short(v)}" for k, v in changes.items()))

    def later(self, key, prefix, field, old, new):
        """Retient un changement de `field`, écrit à la fin de la saisie.
        `key` regroupe les frappes successives d'un même champ ; `prefix` est
        une fonction appelée au moment d'écrire (le nom a pu changer)."""
        entry = self._pending.get(key)
        if entry is None:
            self._pending[key] = [prefix, field, old, new]
        else:
            entry[0], entry[3] = prefix, new
        if QCoreApplication.instance() is None:
            # Pas de boucle d'événements (script, test sans application) : tout de suite.
            self.flush()
            return
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(self.DELAY_MS)
            self._timer.timeout.connect(self.flush)
        self._timer.start()

    def flush(self):
        """Écrit tout de suite les changements retenus (fin de saisie)."""
        pending, self._pending = self._pending, {}
        for prefix, field, old, new in pending.values():
            if old != new:
                log.info("%s %s %s -> %s", prefix(), field, short(old), short(new))
