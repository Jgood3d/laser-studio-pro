"""Éditeur vectoriel complet : canevas (vue du document), onglet (VectorEditorTab), logique
(VectorEditorController, GeneratorsController, LayoutController), bibliothèque de modèles et panneau des
propriétés, reliés. Les contrôleurs ouvrent leurs fenêtres par un seul EditorForms.

    editor = build_vector_editor(document, layers, machine, dialogs, parent, image_frame=..., status=...)
    window.main_tabs_view.addTab(editor.tab, ...)
"""
from dataclasses import dataclass

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
    generators = GeneratorsController(controller, layout, forms, image_frame=image_frame, busy=busy_cursor)
    # Bibliothèque de modèles (resources/library/) : import dans l'éditeur.
    library = LibraryController(layers, bed_height=lambda: machine.bed_h,
                                add_to_vector_editor=controller.import_objects, forms=forms, dialogs=dialogs)
    tab = VectorEditorTab(canvas)
    commands = {**controller.commands(), **generators.commands(), **layout.commands(), "library": library.open}
    tab.command.connect(lambda name: commands[name]())
    tab.draw_tool_requested.connect(controller.choose_draw_tool)
    controller.draw_tool_changed.connect(tab.show_draw_tool)
    controller.show_editor.connect(lambda: show_tab(tab))
    controller.status.connect(status)
    # Panneau des propriétés : rempli d'après la sélection, saisies transmises au contrôleur.
    properties = VectorPropertiesPanel(tab.properties_widgets, layers, canvas, controller, parent=parent)
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
