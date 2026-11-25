"""Éditeur vectoriel complet : canevas (vue du document), onglet (VectorEditorTab), logique
(VectorEditorController, GeneratorsController, LayoutController), bibliothèque de modèles et panneau des
propriétés, reliés. Les contrôleurs ouvrent leurs fenêtres par un seul EditorForms.

    editor = build_vector_editor(document, layers, machine, dialogs, parent, image_frame=..., status=...)
    window.main_tabs_view.addTab(editor.tab, ...)
"""
from dataclasses import dataclass

from PyQt6.QtCore import QTimer

from laser_studio.controllers.generators import GeneratorsController
from laser_studio.controllers.layout import LayoutController
from laser_studio.controllers.library import LibraryController
from laser_studio.controllers.vector_editor import VectorEditorController
from laser_studio.ui.utils import busy_cursor
from laser_studio.ui.vector_editor.canvas import VectorCanvasView
from laser_studio.ui.vector_editor.forms import EditorForms
from laser_studio.ui.vector_editor.properties_panel import VectorPropertiesPanel
from laser_studio.ui.vector_editor.tab import VectorEditorTab


@dataclass
class VectorEditor:
    """Objets de l'éditeur vectoriel construits par build_vector_editor."""
    tab: VectorEditorTab
    canvas: VectorCanvasView
    controller: VectorEditorController
    generators: GeneratorsController
    layout: LayoutController
    library: LibraryController
    properties: VectorPropertiesPanel


def _connect_objects_panel(panel, document, canvas, layers, controller):
    """Liste des objets à droite du canevas : suit le document et la sélection du canevas ; ses boutons
    passent par le contrôleur de l'éditeur. La liste est remplie une fois par tour de boucle d'événements
    (un groupement retire et ajoute plusieurs objets d'un coup)."""
    timer = QTimer(panel)
    timer.setSingleShot(True)
    timer.setInterval(0)

    def refresh():
        panel.show_objects(document.objects, layers.get)
        panel.show_selection([item.obj for item in canvas.selected_items_vector()])

    timer.timeout.connect(refresh)

    def schedule(*_args):
        timer.start()

    for signal in (document.object_added, document.object_removed, document.objects_changed,
                   document.objects_reset, document.order_changed, layers.changed):
        signal.connect(schedule)
    canvas.selection_changed.connect(
        lambda _obj: panel.show_selection([item.obj for item in canvas.selected_items_vector()]))
    panel.selection_requested.connect(canvas.select_objects)
    panel.move_requested.connect(controller.move_objects)
    panel.group_requested.connect(controller.group_selection)
    panel.ungroup_requested.connect(controller.ungroup_selection)
    panel.rename_requested.connect(controller.rename_object)
    panel.visibility_requested.connect(controller.set_object_visible)
    panel.ignore_requested.connect(controller.toggle_ignored)
    panel.delete_requested.connect(controller.delete_object)
    refresh()


def build_vector_editor(document, layers, machine, dialogs, parent, *, image_frame, status, show_tab,
                        overscan_margin=lambda width_mm: 0.0):
    """Éditeur de `document` (VectorDocument) sur les calques de `layers` ; plateau de `machine`.
    `image_frame()` : cadre de l'image de « Graver une image » (puzzle) ; `status(texte)` : barre
    d'état ; `show_tab(onglet)` : affiche l'onglet (après un import, un générateur) ;
    `overscan_margin(largeur_mm)` : marge de surbalayage devant un dessin importé."""
    canvas = VectorCanvasView(layers, document=document)
    forms = EditorForms(parent)
    controller = VectorEditorController(document, canvas, layers, machine, dialogs, parent, forms=forms,
                                        overscan_margin=overscan_margin)
    layout = LayoutController(controller, forms, busy=busy_cursor)
    # Bibliothèque de modèles (resources/library/) : une page de la fenêtre des générateurs.
    library = LibraryController(layers, bed_height=lambda: machine.bed_h,
                                add_to_vector_editor=controller.import_objects, dialogs=dialogs)
    generators = GeneratorsController(controller, layout, forms, image_frame=image_frame, busy=busy_cursor,
                                      library=library)
    tab = VectorEditorTab(canvas)
    commands = {**controller.commands(), **generators.commands(), **layout.commands()}
    tab.command.connect(lambda name: commands[name]())
    # Clavier et clic droit du canevas : mêmes commandes que les boutons de l'onglet.
    canvas.command_requested.connect(lambda name: commands[name]())
    canvas.nudge_requested.connect(controller.nudge_selection)
    canvas.layer_requested.connect(controller.assign_layer)
    canvas.combine_requested.connect(controller.group_selection)
    canvas.shape_requested.connect(controller.add_basic_shape)
    canvas.text_resync_requested.connect(controller.resync_text_guide)
    canvas.objects_moved.connect(controller.resync_linked_texts)
    tab.draw_tool_requested.connect(controller.choose_draw_tool)
    controller.draw_tool_changed.connect(tab.show_draw_tool)
    controller.show_editor.connect(lambda: show_tab(tab))
    controller.status.connect(status)
    # Panneau des propriétés : rempli d'après la sélection, saisies transmises au contrôleur.
    properties = VectorPropertiesPanel(tab.properties_widgets, layers, canvas, controller, parent=parent)
    _connect_objects_panel(tab.objects_panel, document, canvas, layers, controller)
    canvas.edit_requested.connect(controller.edit_object)
    canvas.insert_text_requested.connect(controller.insert_text)
    canvas.serial_duplicate_requested.connect(layout.open_serial_duplicate)
    canvas.jig_requested.connect(generators.open_jig_generator)
    canvas.medal_text_requested.connect(controller.open_medal_text)
    # Couleurs des objets suivant celles des calques ; zone de travail à la taille du plateau.
    layers.changed.connect(canvas.refresh_all)
    machine.changed.connect(lambda fields: canvas.set_work_area(machine.bed_w, machine.bed_h)
                            if {"bed_w", "bed_h"} & set(fields) else None)
    canvas.set_work_area(machine.bed_w, machine.bed_h)
    return VectorEditor(tab, canvas, controller, generators, layout, library, properties)
