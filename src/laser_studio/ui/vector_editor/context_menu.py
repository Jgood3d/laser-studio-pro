"""Menu du clic droit sur le canevas vectoriel : actions sur la sélection (calque, taille, groupe, texte sur
contour, nœuds, rotation, duplication…) puis, toujours, « Ajouter une forme » à l'endroit cliqué. Chaque
entrée émet un signal du canevas (traité par VectorEditorController), sauf le mode nœuds, outil du canevas."""
from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr
from laser_studio.models.layers import layer_label
from laser_studio.models.vector_objects import GroupObject, TextObject
from laser_studio.vector import boolean_ops, path_ops, text_follow


def build_context_menu(canvas, selected, click_mm):
    """Menu pour les éléments `selected` (VectorGraphicsItem) et le point cliqué `click_mm` (x, y) mm."""
    menu = QMenu(canvas)
    if selected:
        add_selection_entries(menu, canvas, selected)
        menu.addSeparator()
    add_insert_entries(menu, canvas, click_mm)
    return menu


def add_selection_entries(menu, canvas, selected):
    """Entrées qui agissent sur la sélection courante : chacune émet un signal du canevas (commande de
    l'éditeur, calque, opération booléenne…), traité par VectorEditorController."""
    n = len(selected)
    objects = [it.obj for it in selected]
    label_suffix = tr("vector.n_objects").format(n=n) if n > 1 else ""

    def command(name):
        return lambda _checked=False: canvas.command_requested.emit(name)

    layer_menu = menu.addMenu(tr("vector.assign_to_layer") + label_suffix)
    for layer in canvas.layer_manager.layers:
        action = layer_menu.addAction(layer_label(layer))
        action.triggered.connect(lambda _checked=False, lid=layer.id: canvas.layer_requested.emit(lid))

    menu.addAction(tr("vector.resize_ellipsis") + label_suffix).triggered.connect(command("resize"))

    if n >= 2:
        menu.addAction(tr("vector.group_objects").format(n=n)).triggered.connect(command("group"))
    if n >= 2 or (n == 1 and isinstance(objects[0], GroupObject)):
        # Opérations booléennes : grouper en combinant (ou changer l'opération d'un groupe).
        combine = menu.addMenu(tr("objects.boolean_menu"))
        for operation in boolean_ops.OPERATIONS:
            combine.addAction(tr(f"objects.op.{operation}")).triggered.connect(
                lambda _checked=False, op=operation: canvas.combine_requested.emit(op))
    if any(isinstance(o, GroupObject) or path_ops.can_ungroup(o) for o in objects):
        menu.addAction(tr("vector.ungroup_objects")).triggered.connect(command("ungroup"))
    if any(path_ops.can_explode(o) for o in objects):
        menu.addAction(tr("vector.explode_path")).triggered.connect(command("explode"))

    pair = text_follow.text_follow_pair(objects)
    if pair is not None:
        already = bool(getattr(pair[0], "follow_points", None))
        menu.addAction(tr("vector.text_resync" if already else "vector.text_follow")).triggered.connect(
            command("text_follow"))
    elif n == 1 and isinstance(objects[0], TextObject) \
            and text_follow.linked_guide(objects[0], canvas.document.objects) is not None:
        menu.addAction(tr("vector.text_resync")).triggered.connect(
            lambda _checked=False: canvas.text_resync_requested.emit(objects[0]))
    if text_follow.medal_guide(objects) is not None:
        menu.addAction(tr("vector.medal")).triggered.connect(canvas.medal_text_requested.emit)

    if n == 1:
        menu.addAction(tr("vector.edit_nodes")).triggered.connect(lambda: canvas.enter_node_edit(selected[0]))
    if canvas.nodes.active:
        menu.addSeparator()
        menu.addAction(tr("vector.exit_nodes")).triggered.connect(canvas.exit_node_edit)
        menu.addAction(tr("vector.delete_node")).triggered.connect(canvas.delete_selected_node)

    menu.addSeparator()
    menu.addAction(tr("ui.vector_rotate_90")).triggered.connect(command("rotate"))
    menu.addAction(tr("ui.vector_duplicate")).triggered.connect(command("duplicate"))
    menu.addAction(tr("ui.vector_serial_duplicate")).triggered.connect(
        lambda: canvas.serial_duplicate_requested.emit())
    menu.addAction(tr("ui.vector_jig")).triggered.connect(lambda: canvas.jig_requested.emit())
    menu.addAction(tr("ui.vector_delete")).triggered.connect(command("delete"))


def add_insert_entries(menu, canvas, click_mm):
    """Sous-menu « Ajouter une forme » : texte, ligne, carré, cercle, centrés sur le point cliqué."""
    add_menu = menu.addMenu(tr("vector.ctx_add_shape"))
    x_mm, y_mm = click_mm
    add_menu.addAction(tr("vector.ctx_text")).triggered.connect(
        lambda checked=False: canvas.insert_text_requested.emit(x_mm, y_mm))
    for key, kind in (("vector.ctx_line", "Ligne"), ("vector.ctx_square", "Carré"), ("vector.ctx_circle", "Cercle")):
        add_menu.addAction(tr(key)).triggered.connect(
            lambda checked=False, kind=kind: canvas.shape_requested.emit(kind, x_mm, y_mm))
    add_menu.addSeparator()
    add_menu.addAction(tr("ui.vector_jig")).triggered.connect(lambda checked=False: canvas.jig_requested.emit())
