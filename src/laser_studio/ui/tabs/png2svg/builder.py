"""Onglet « Vectorisation d'image » relié à sa logique (Png2SvgController).

    tab, png2svg = build_png2svg_tab(layers, machine, dialogs, image_actions, parent, add_to_vector_editor=...)
"""
from laser_studio.controllers.png2svg import Png2SvgController
from laser_studio.ui.tabs.png2svg.tab import Png2SvgTab


def build_png2svg_tab(layers, machine, dialogs, image_actions, parent, *, add_to_vector_editor):
    """Le SVG produit va dans l'éditeur vectoriel (`add_to_vector_editor(objets)`), sur les calques de
    `layers`, à la hauteur du plateau de `machine`. Pivoter et supprimer : inscrits dans
    `image_actions` (pas de miroirs, que la conversion n'utilise pas). Renvoie (Png2SvgTab, Png2SvgController)."""
    tab = Png2SvgTab()
    png2svg = Png2SvgController(parent, layers, bed_height=lambda: machine.bed_h,
                                add_to_vector_editor=add_to_vector_editor, dialogs=dialogs)
    tab.send_to_vector_requested.connect(png2svg.send_to_vector_editor)
    tab.image_changed.connect(image_actions.update_state)
    converter = tab.converter
    image_actions.add(
        tab, has_image=lambda: bool(converter.image_path),
        rotate=lambda clockwise: converter.rotate_image(90 if clockwise else -90),
        clear=converter.clear_image, mirrors=False)       # la conversion n'utilise pas les miroirs
    return tab, png2svg
