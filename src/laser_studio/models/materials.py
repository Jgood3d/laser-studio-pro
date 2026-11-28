"""Modèle des profils matériaux : chaque matériau est une liste de réglages
de calques (clé "layers"), plus les anciennes valeurs de gravure image et de
découpe SVG (sp_e, pw_e, sp_c, pw_c, pass_c).

Le matériau choisi (`current`) suit les calques : chaque changement de
calque y est enregistré aussitôt par la fenêtre (store), il n'y a plus de
bouton « Enregistrer ».
"""
import copy
import logging

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.core.debug_log import LOGGER_NAME

log = logging.getLogger(f"{LOGGER_NAME}.modeles")


def _layers_diff(old, new):
    """Résumé lisible des réglages de calques qui diffèrent entre deux
    matériaux (pour le journal)."""
    def key(entry):
        return entry.get("role") or entry.get("id") or entry.get("name")
    before = {key(e): e for e in (old or {}).get("layers") or []}
    parts = []
    for entry in (new or {}).get("layers") or []:
        prev = before.get(key(entry), {})
        diffs = [f"{k} {prev.get(k)!r} -> {v!r}" for k, v in entry.items()
                 if k not in ("role", "id", "name") and prev.get(k) != v]
        if diffs:
            parts.append(f"{entry.get('name') or key(entry)} : {', '.join(diffs)}")
    return " ; ".join(parts)


class MaterialsModel(QObject):
    """Liste des matériaux (nom -> réglages) et matériau choisi.

    Signaux, émis après la modification :
    - materials_reset() : liste entièrement remplacée (profil machine, projet,
      import) ;
    - material_added(nom), material_removed(nom), material_changed(nom) ;
    - current_changed(nom) : autre matériau choisi ;
    - changed() : après chacun des signaux précédents.

    `complete` : fonction qui complète un matériau (les trois calques de base,
    voir controllers.materials.complete_material).
    """

    materials_reset = pyqtSignal()
    material_added = pyqtSignal(str)
    material_removed = pyqtSignal(str)
    material_changed = pyqtSignal(str)
    current_changed = pyqtSignal(str)
    changed = pyqtSignal()

    def __init__(self, materials=None, complete=None, parent=None):
        super().__init__(parent)
        self._complete = complete or (lambda m: dict(m))
        self.materials = {}
        self.current = None
        if materials:
            self.set_materials(materials)

    # -- lecture

    def names(self):
        return list(self.materials.keys())

    def get(self, name):
        return self.materials.get(name)

    def current_material(self):
        return self.materials.get(self.current)

    def to_dict(self):
        """Copie de la liste (pour l'enregistrer dans un profil, un projet)."""
        return copy.deepcopy(self.materials)

    # -- modification

    def set_materials(self, materials, current=None):
        """Remplace toute la liste. Le matériau choisi devient `current` s'il
        existe, sinon le précédent s'il existe encore, sinon le premier."""
        self.materials = {name: self._complete(m) for name, m in (materials or {}).items()
                          if isinstance(m, dict)}
        wanted = current if current in self.materials else self.current
        self.current = wanted if wanted in self.materials else next(iter(self.materials), None)
        log.info("Matériaux : liste rechargée (%d matériaux), matériau choisi : %s",
                 len(self.materials), self.current)
        self.materials_reset.emit()
        self.changed.emit()

    def select(self, name):
        """Choisit le matériau `name`. Renvoie True s'il a changé."""
        if name not in self.materials or name == self.current:
            return False
        old, self.current = self.current, name
        log.info("Matériaux : matériau choisi %r -> %r", old, name)
        self.current_changed.emit(name)
        self.changed.emit()
        return True

    def store(self, name, material):
        """Enregistre `material` sous `name` : ajouté s'il n'existe pas,
        remplacé sinon. Renvoie True si quelque chose a changé."""
        material = self._complete(material)
        old = self.materials.get(name)
        if old == material:
            return False
        self.materials[name] = material
        if old is None:
            log.info("Matériaux : ajout de %r", name)
            self.material_added.emit(name)
        else:
            log.info("Matériaux : %r mis à jour : %s", name, _layers_diff(old, material) or "réglages")
            self.material_changed.emit(name)
        self.changed.emit()
        return True

    def remove(self, name):
        if name not in self.materials:
            return False
        del self.materials[name]
        log.info("Matériaux : suppression de %r", name)
        if self.current == name:
            self.current = next(iter(self.materials), None)
        self.material_removed.emit(name)
        self.changed.emit()
        return True
