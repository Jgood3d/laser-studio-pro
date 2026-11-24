"""Menu du clic droit sur le canevas vectoriel : actions sur la sélection (calque, taille, groupe, texte sur
contour, nœuds, rotation, duplication…) puis, toujours, « Ajouter une forme » à l'endroit cliqué. Chaque
entrée appelle une méthode publique du canevas ou émet l'un de ses signaux."""
from PyQt6.QtWidgets import QMenu

from laser_studio.i18n import tr
from laser_studio.models.layers import layer_label
from laser_studio.models.vector_objects import TextObject


def build_context_menu(canvas, selected, click_mm):
    """Menu pour les éléments `selected` (VectorGraphicsItem) et le point cliqué `click_mm` (x, y) mm."""
    menu = QMenu(canvas)
    if selected:
        add_selection_entries(menu, canvas, selected)
        menu.addSeparator()
    add_insert_entries(menu, canvas, click_mm)
    return menu


def add_selection_entries(menu, canvas, selected):
    """Entrées qui agissent sur la sélection courante."""
    n = len(selected)
    label_suffix = tr("vector.n_objects").format(n=n) if n > 1 else ""

    layer_menu = menu.addMenu(tr("vector.assign_to_layer") + label_suffix)
    for layer in canvas.layer_manager.layers:
        action = layer_menu.addAction(layer_label(layer))
        action.triggered.connect(lambda checked=False, lid=layer.id: canvas.assign_layer(selected, lid))

    menu.addAction(tr("vector.resize_ellipsis") + label_suffix).triggered.connect(
        lambda: canvas.resize_group(selected))

    if n >= 2:
        menu.addAction(tr("vector.group_objects").format(n=n)).triggered.connect(canvas.group_selected)
    if any(canvas.can_ungroup_item(it) for it in selected):
        menu.addAction(tr("vector.ungroup_objects")).triggered.connect(canvas.ungroup_selected)
    if any(canvas.can_explode_item(it) for it in selected):
        menu.addAction(tr("vector.explode_path")).triggered.connect(canvas.explode_selected)

    pair = canvas.text_follow_candidates()
    if pair is not None:
        already = bool(getattr(pair[0].obj, "follow_points", None))
        menu.addAction(tr("vector.text_resync" if already else "vector.text_follow")).triggered.connect(
            canvas.make_text_follow_object)
    elif n == 1 and isinstance(selected[0].obj, TextObject) \
            and canvas.linked_guide_item(selected[0].obj) is not None:
        menu.addAction(tr("vector.text_resync")).triggered.connect(lambda: canvas.resync_text_guide(selected[0]))
    if canvas.medal_guide_item() is not None:
        menu.addAction(tr("vector.medal")).triggered.connect(canvas.medal_text_requested.emit)

    if n == 1:
        menu.addAction(tr("vector.edit_nodes")).triggered.connect(lambda: canvas.enter_node_edit(selected[0]))
    if canvas.nodes.active:
        menu.addSeparator()
        menu.addAction(tr("vector.exit_nodes")).triggered.connect(canvas.exit_node_edit)
        menu.addAction(tr("vector.delete_node")).triggered.connect(canvas.delete_selected_node)

    menu.addSeparator()
    menu.addAction(tr("ui.vector_rotate_90")).triggered.connect(lambda: canvas.rotate_quarter(selected))
    menu.addAction(tr("ui.vector_duplicate")).triggered.connect(canvas.duplicate_selected)
    menu.addAction(tr("ui.vector_serial_duplicate")).triggered.connect(
        lambda: canvas.serial_duplicate_requested.emit())
    menu.addAction(tr("ui.vector_jig")).triggered.connect(lambda: canvas.jig_requested.emit())
    menu.addAction(tr("ui.vector_delete")).triggered.connect(canvas.remove_selected)


def add_insert_entries(menu, canvas, click_mm):
    """Sous-menu « Ajouter une forme » : texte, ligne, carré, cercle, centrés sur le point cliqué."""
    add_menu = menu.addMenu(tr("vector.ctx_add_shape"))
    x_mm, y_mm = click_mm
    add_menu.addAction(tr("vector.ctx_text")).triggered.connect(
        lambda checked=False: canvas.insert_text_requested.emit(x_mm, y_mm))
    for key, kind in (("vector.ctx_line", "Ligne"), ("vector.ctx_square", "Carré"), ("vector.ctx_circle", "Cercle")):
        add_menu.addAction(tr(key)).triggered.connect(
            lambda checked=False, kind=kind: canvas.add_basic_shape(kind, x_mm, y_mm))
    add_menu.addSeparator()
    add_menu.addAction(tr("ui.vector_jig")).triggered.connect(lambda checked=False: canvas.jig_requested.emit())
