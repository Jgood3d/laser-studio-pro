"""Groupes de l'éditeur vectoriel : grouper (chaque objet reste entier), combiner (union, différence…),
changer l'opération d'un groupe, dégrouper, éclater en segments. Chacune est une étape d'annulation ; les
opérations géométriques sont dans vector/boolean_ops.py et vector/path_ops.py.

    grouping = GroupingActions(editor)        # editor.grouping
    grouping.group_selection(boolean_ops.UNION)
"""
from laser_studio.models.vector_objects import GroupObject
from laser_studio.vector import boolean_ops, path_ops


class GroupingActions:
    """`editor` : VectorEditorController (sélection, document, canevas, signal properties_changed)."""

    def __init__(self, editor):
        self.editor = editor

    def group_selection(self, operation=boolean_ops.GROUP):
        """Groupe la sélection (simple groupe) ou la combine (union, différence…) ; un groupe seul change
        d'opération. Renvoie le groupe, ou None."""
        objects = self.editor.selected_objects()
        if len(objects) == 1 and isinstance(objects[0], GroupObject):
            group = objects[0]
            self.set_operation(group, operation)
        else:
            group = self.group(objects, operation)
        if group is not None:
            self.editor.properties_changed.emit(group)
        return group

    def group(self, objects, operation=boolean_ops.GROUP):
        """Groupe `objects` (au moins 2) : chaque objet reste entier (un texte redevient un texte modifiable au
        dégroupage) et le groupe se manipule d'un bloc. Avec une opération booléenne, les objets ne forment
        plus qu'un tracé, sur le calque de celui du dessous. Le groupe prend la place du plus haut des objets
        dans l'empilement. Renvoie le groupe, ou None."""
        if len(objects) < 2:
            return None
        editor, document = self.editor, self.editor.document
        order = {id(obj): index for index, obj in enumerate(document.objects)}
        objects = sorted(objects, key=lambda obj: order.get(id(obj), 0))
        group = GroupObject(objects, operation=operation)
        top = max(order[id(obj)] for obj in objects)
        editor.canvas.push_undo_snapshot()
        document.replace(objects, [group])
        above = sum(1 for obj in document.objects[:-1] if order.get(id(obj), -1) > top)
        for _ in range(above):
            document.move([group], -1)
        editor.canvas.select_objects([group])
        return group

    def set_operation(self, group, operation):
        """Change l'opération d'un groupe (simple groupe, union, différence…). True si elle a changé."""
        if not isinstance(group, GroupObject) or group.operation == operation:
            return False
        with self.editor.changing([group], show=False):
            group.set_operation(operation)
        return True

    def ungroup_selection(self):
        """Dégroupe la sélection : un groupe rend ses objets, à leur place dans l'empilement (un texte redevient
        un texte) ; un tracé importé est séparé en sous-tracés. Renvoie les nouveaux objets."""
        editor, document = self.editor, self.editor.document
        targets = [obj for obj in editor.selected_objects()
                   if isinstance(obj, GroupObject) or path_ops.can_ungroup(obj)]
        if not targets:
            return []
        editor.canvas.push_undo_snapshot()
        released = []
        for obj in targets:
            if isinstance(obj, GroupObject):
                index = document.objects.index(obj)
                children = obj.released_children()
                document.replace([obj], children)
                for _ in range(len(document.objects) - len(children) - index):
                    document.move(children, -1)
            else:
                children = path_ops.ungroup_object(obj)
                if not children:
                    continue                      # rien d'utile à séparer : l'objet reste tel quel
                document.replace([obj], children)
            released += children
        editor.canvas.select_objects(released)
        editor.properties_changed.emit(released[0] if released else None)
        return released

    def explode_selection(self):
        """Découpe chaque objet sélectionné en segments indépendants (une ligne = un objet) : supprimer une
        seule encoche ou un seul trait, puis le redessiner. Renvoie les segments."""
        editor = self.editor
        editor.canvas.nodes.exit()
        targets = [obj for obj in editor.selected_objects() if path_ops.can_explode(obj)]
        if not targets:
            return []
        editor.canvas.push_undo_snapshot()
        segments = []
        for obj in targets:
            parts = path_ops.explode_object(obj)
            if parts:
                editor.document.replace([obj], parts)
                segments += parts
        editor.canvas.select_objects(segments)
        return segments
