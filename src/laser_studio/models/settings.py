"""Base des modèles de réglages « à plat » (un nom -> une valeur) : réglages
machine (MachineConfig), configuration GRBL (GrblConfig)…

Chaque sous-classe déclare ses champs dans FIELDS. Les valeurs se lisent
comme des attributs (`machine.bed_w`) et ne se modifient que par
`update(...)`, qui convertit les types, n'émet `changed` que pour ce qui a
vraiment changé, et écrit l'ancienne et la nouvelle valeur dans le journal
de débogage (LASER_STUDIO_DEBUG=1).
"""
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import LOGGER_NAME

log = logging.getLogger(f"{LOGGER_NAME}.modeles")


def _short(value, limit=60):
    """Valeur lisible dans le journal (les longs textes sont coupés)."""
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


class SettingsModel(QObject):
    """Réglages nommés, avec leur type et leur valeur par défaut.

    FIELDS : {nom: (type, valeur par défaut)}.
    CHOICES : {nom: valeurs permises} (facultatif).
    LABEL : préfixe des lignes du journal.

    Signal changed({nom: nouvelle valeur}) : seulement ce qui a changé.
    """

    FIELDS = {}
    CHOICES = {}
    LABEL = "Réglages"

    changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {name: default for name, (_cast, default) in self.FIELDS.items()}

    def __getattr__(self, name):
        # Appelé seulement si l'attribut n'existe pas normalement.
        values = self.__dict__.get("_values")
        if values is not None and name in values:
            return values[name]
        raise AttributeError(f"{type(self).__name__} n'a pas de réglage « {name} »")

    def get(self, name):
        return self._values[name]

    def to_dict(self):
        return dict(self._values)

    def _validated(self, fields):
        values = {}
        for name, value in fields.items():
            cast = self.FIELDS[name][0]
            try:
                value = cast(value)
            except (TypeError, ValueError):
                log.warning("%s : valeur ignorée pour %s : %s", self.LABEL, name, _short(value))
                continue
            choices = self.CHOICES.get(name)
            if choices is not None and value not in choices:
                log.warning("%s : valeur ignorée pour %s : %s", self.LABEL, name, _short(value))
                continue
            values[name] = value
        return values

    def update(self, **fields):
        """Modifie des réglages. Renvoie ce qui a changé ({nom: valeur}), vide
        si rien n'a changé (aucun signal n'est alors émis). Un nom inconnu est
        une erreur de programmation (KeyError) ; une valeur inutilisable est
        ignorée."""
        unknown = set(fields) - set(self.FIELDS)
        if unknown:
            raise KeyError(f"{self.LABEL} : réglages inconnus : {sorted(unknown)}")
        changes, before = {}, {}
        for name, value in self._validated(fields).items():
            if self._values[name] != value:
                before[name] = self._values[name]
                self._values[name] = value
                changes[name] = value
        if changes:
            log.info("%s : %s", self.LABEL,
                     ", ".join(f"{k} {_short(before[k])} -> {_short(v)}" for k, v in changes.items()))
            self.changed.emit(changes)
        return changes

    def load(self, data):
        """Reprend les réglages connus de `data` (dictionnaire d'un profil, d'un
        fichier) ; les autres clés sont ignorées. Renvoie ce qui a changé."""
        if not isinstance(data, dict):
            return {}
        return self.update(**{k: v for k, v in data.items() if k in self.FIELDS})
