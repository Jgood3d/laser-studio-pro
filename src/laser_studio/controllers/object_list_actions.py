"""Actions de la liste des objets de l'éditeur vectoriel (ObjectsPanel) : monter ou descendre, renommer,
masquer d'un œil, ignorer, supprimer, y compris un objet à l'intérieur d'un groupe. Chacune est une étape
d'annulation. L'arbre des groupes est parcouru par vector/object_tree.py.

    object_list = ObjectListActions(editor)        # editor.object_list
    panel.visibility_requested.connect(object_list.set_visible)
"""
from laser_studio.vector import object_tree


class ObjectListActions:
    """`editor` : VectorEditorController (document, canevas, calques, signal properties_changed)."""

    def __init__(self, editor):
        self.editor = editor

    def move(self, entries, step):
        """Monte (`step` > 0) ou descend des objets : [(groupe ou None, objet)]. Un objet du dessus de la pile
        change de place dans le document ; un objet d'un groupe, dans son groupe (l'ordre compte pour une
        différence). Renvoie True si quelque chose a bougé (sinon, pas d'étape d'annulation)."""
        editor, document = self.editor, self.editor.document
        top = [obj for parent, obj in entries if parent is None]
        inside = [(parent, obj) for parent, obj in entries if parent is not None]
        editor.canvas.push_undo_snapshot()
        changed = document.move(top, step) if top else False
        tops = []
        # Du plus haut au plus bas en montant (et l'inverse), pour qu'un objet ne bloque pas son voisin.
        for parent, obj in sorted(inside, key=lambda entry: entry[0].children.index(entry[1]), reverse=step > 0):
            if parent.move_child(obj, step):
                changed = True
                container = object_tree.refresh_ancestors(document.objects, obj)
                if container not in tops:
                    tops.append(container)
        if tops:
            document.notify_changed(tops)
            editor.properties_changed.emit(tops[0])
        if not changed:
            document.drop_last_snapshot()
        return changed

    def rename(self, obj, name):
        """Nom donné dans la liste (vide : nom par défaut)."""
        name = name.strip()
        if name == (getattr(obj, "name", "") or ""):
            return
        with self.editor.changing([obj], show=False):
            obj.name = name

    def set_visible(self, obj, visible):
        """Œil : masque l'objet à l'affichage (il reste gravé), en haut de la pile ou dans un groupe (le groupe
        est redessiné sans lui)."""
        if obj.is_hidden() == (not visible):
            return
        editor = self.editor
        editor.canvas.push_undo_snapshot()
        obj.hidden = not visible
        editor.document.notify_changed([object_tree.refresh_ancestors(editor.document.objects, obj)])

    def toggle_ignored(self, obj):
        """Tête laser : met l'objet sur le calque « Ignoré » (ni affiché, ni gravé, ni découpé) en retenant son
        calque, ou le lui rend. Un groupe ignore ou rend tous ses objets ; les groupes qui contiennent l'objet
        sont recalculés."""
        editor = self.editor
        editor.canvas.push_undo_snapshot()
        fallback = editor.layers.layers[0].id if editor.layers.layers else None
        obj.set_ignored(not obj.is_ignored(), fallback)
        editor.document.notify_changed([object_tree.refresh_ancestors(editor.document.objects, obj)])

    def delete(self, group, obj):
        """Poubelle : supprime `obj` du dessin (`group` None), ou le retire de son groupe (un groupe vidé
        disparaît à son tour)."""
        editor, document = self.editor, self.editor.document
        editor.canvas.nodes.exit()
        editor.canvas.push_undo_snapshot()
        changed, removed = (None, obj) if group is None else object_tree.remove_from_group(document.objects, obj)
        if removed is not None:
            document.remove(removed)
            editor.properties_changed.emit(None)
        else:
            document.notify_changed([changed])
            editor.properties_changed.emit(changed)
