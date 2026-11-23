"""Document de l'éditeur vectoriel : la liste des objets, l'historique
d'annulation et le presse-papiers. Sans widget : le canevas
(ui/vector_editor/canvas.py) en est une vue, qui crée ou retire ses éléments
graphiques quand le document le signale.

    document = VectorDocument()
    document.object_added.connect(view.on_object_added)
    document.push_snapshot()                 # avant une modification annulable
    document.add(ShapeObject("Rectangle", 30, 20))
    document.undo()

Les opérations de géométrie (grouper, dégrouper, exploser…) sont dans
vector/path_ops.py : elles fabriquent les nouveaux objets, le document les
remplace (replace).
"""
import uuid

from PyQt6.QtCore import QObject, pyqtSignal

from laser_studio.models.vector_objects import VectorObject
from laser_studio.core.debug_log import get_logger

log = get_logger()

# Nombre d'étapes gardées pour Annuler et pour Refaire.
MAX_UNDO = 30
# Décalage (mm) d'une copie collée ou dupliquée, pour la distinguer de l'original.
PASTE_OFFSET_MM = 5


def clone_object(obj_or_dict, offset_mm=PASTE_OFFSET_MM):
    """Copie d'un objet (ou d'un dictionnaire to_dict), avec un nouvel
    identifiant, décalée de `offset_mm` en X et en Y."""
    data = obj_or_dict.to_dict() if isinstance(obj_or_dict, VectorObject) else obj_or_dict
    clone = VectorObject.from_dict(data)
    clone.id = uuid.uuid4().hex[:8]
    clone.x_mm += offset_mm
    clone.y_mm += offset_mm
    return clone


class VectorDocument(QObject):
    """Objets du dessin, dans l'ordre (l'ordre de la liste est l'ordre de
    création ; le calque du plus ancien l'emporte quand on groupe).

    Signaux, émis après la modification :
    - object_added(obj) ;
    - object_removed(obj) ;
    - objects_changed(liste) : ces objets ont changé (position, calque, taille…) :
      les vues les redessinent ;
    - objects_reset() : toute la liste a changé (annuler, refaire, charger).

    `objects` se lit librement ; pour le modifier, passer par add, remove,
    replace ou load, pour que les vues suivent.
    """

    object_added = pyqtSignal(object)
    object_removed = pyqtSignal(object)
    objects_changed = pyqtSignal(list)
    objects_reset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.objects = []
        self._undo_stack = []
        self._redo_stack = []
        self.max_undo = MAX_UNDO
        # Objets copiés (Ctrl+C), en dictionnaires : propres à l'éditeur, pas le presse-papiers système.
        self.clipboard = None

    # -- liste

    def add(self, obj):
        self.objects.append(obj)
        self.object_added.emit(obj)
        return obj

    def remove(self, obj):
        """Retire `obj`. False s'il n'était pas dans le document."""
        try:
            self.objects.remove(obj)
        except ValueError:
            return False
        self.object_removed.emit(obj)
        return True

    def replace(self, old_objects, new_objects):
        """Retire `old_objects` puis ajoute `new_objects` (grouper, exploser…)."""
        for obj in old_objects:
            self.remove(obj)
        for obj in new_objects:
            self.add(obj)

    def notify_changed(self, objects):
        """Signale que `objects` ont été modifiés (les vues les redessinent)."""
        objects = list(objects)
        if objects:
            self.objects_changed.emit(objects)

    def object_by_id(self, obj_id):
        for obj in self.objects:
            if obj.id == obj_id:
                return obj
        return None

    # -- enregistrement

    def serialize(self):
        return [o.to_dict() for o in self.objects]

    def load(self, data):
        """Remplace tous les objets (projet ouvert, « Tout supprimer »). Un objet
        illisible interrompt le chargement (l'erreur remonte)."""
        self.objects = []
        try:
            for d in (data or []):
                self.objects.append(VectorObject.from_dict(d))
        finally:
            self.objects_reset.emit()

    def _restore(self, snapshot):
        """Remplace tous les objets par un instantané ; un objet illisible est ignoré."""
        self.objects = []
        for d in snapshot:
            try:
                self.objects.append(VectorObject.from_dict(d))
            except Exception:
                log.warning("Annuler / refaire : objet illisible ignoré : %r", d, exc_info=True)
                continue
        self.objects_reset.emit()

    # -- annuler / refaire

    def push_snapshot(self):
        """À appeler AVANT toute action qui modifie les objets (ajout,
        suppression, déplacement, redimensionnement...), pour pouvoir revenir
        en arrière avec Annuler. Toute nouvelle action vide Refaire."""
        try:
            snapshot = [o.to_dict() for o in self.objects]
        except Exception:
            log.exception("Annuler : instantané impossible, étape non mémorisée")
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self.max_undo:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def drop_last_snapshot(self):
        """Oublie la dernière étape d'annulation (action abandonnée, ex. boîte
        de dialogue annulée après un aperçu)."""
        if self._undo_stack:
            self._undo_stack.pop()

    def can_undo(self):
        return bool(self._undo_stack)

    def can_redo(self):
        return bool(self._redo_stack)

    def undo(self):
        if not self._undo_stack:
            return False
        current = self.serialize()
        snapshot = self._undo_stack.pop()
        self._redo_stack.append(current)
        if len(self._redo_stack) > self.max_undo:
            self._redo_stack.pop(0)
        self._restore(snapshot)
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        current = self.serialize()
        snapshot = self._redo_stack.pop()
        self._undo_stack.append(current)
        if len(self._undo_stack) > self.max_undo:
            self._undo_stack.pop(0)
        self._restore(snapshot)
        return True

    # -- copier / coller / dupliquer

    def copy(self, objects):
        """Copie les objets dans le presse-papiers de l'éditeur (rien si vide)."""
        if objects:
            self.clipboard = [o.to_dict() for o in objects]

    def has_clipboard(self):
        return bool(self.clipboard)

    def paste(self):
        """Ajoute une copie décalée de chaque objet copié ; renvoie les objets
        ajoutés (un objet illisible est ignoré)."""
        pasted = []
        for d in self.clipboard or []:
            try:
                clone = clone_object(d)
            except Exception:
                log.warning("Coller : objet illisible ignoré : %r", d, exc_info=True)
                continue
            pasted.append(self.add(clone))
        return pasted

    def duplicate(self, objects):
        """Ajoute une copie décalée de chaque objet ; renvoie les copies."""
        return [self.add(clone_object(obj)) for obj in objects]
