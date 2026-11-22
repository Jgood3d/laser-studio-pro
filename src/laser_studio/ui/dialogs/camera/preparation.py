"""Préparer la calibration de la caméra : feuilles à imprimer et gabarit.

Actions communes à la fenêtre Caméra et aux assistants :

    print_board(parent)                     damier (calibration optique)
    print_tags(parent, targets)             AprilTags à taille réelle
    add_template_to_editor(parent, targets) cadres + numéros dans l'éditeur

Chaque feuille peut être imprimée ou enregistrée en PDF (`pdf=True`).
"""
from __future__ import annotations

from laser_studio.camera.print_layout import apriltag_pages, chessboard_pages
from laser_studio.i18n import tr
from laser_studio.ui.dialogs.camera.printing import print_sheets, save_sheets_pdf

# Coins intérieurs du damier (standard OpenCV 9×6), comme l'assistant d'optique.
PATTERN_SIZE = (9, 6)


def print_board(parent, pdf=False):
    """Damier de calibration optique, feuille paysage, à l'échelle réelle."""
    def build(width_mm, height_mm):
        pages, _square = chessboard_pages(
            PATTERN_SIZE, width_mm, height_mm,
            caption=lambda square: tr("camera.print.board_caption").format(
                cols=PATTERN_SIZE[0], rows=PATTERN_SIZE[1], square=f"{square:g}"),
        )
        return pages

    title = tr("camera.print.board_title")
    if pdf:
        return save_sheets_pdf(parent, title, build, "damier_calibration.pdf", landscape=True)
    return print_sheets(parent, title, build, landscape=True)


def print_tags(parent, targets, pdf=False):
    """AprilTags à découper et poser : un par cadre, avec son numéro et la
    position de son centre sur le plateau."""
    targets = list(targets)

    def build(width_mm, height_mm):
        return apriltag_pages(
            targets, width_mm, height_mm,
            label=lambda t: tr("camera.print.tag_label").format(
                id=t.tag_id, x=f"{t.cx_mm:.1f}", y=f"{t.cy_mm:.1f}"),
            footer=lambda t: tr("camera.print.tags_footer").format(size=f"{t.size_mm:g}"),
        )

    title = tr("camera.print.tags_title")
    if pdf:
        return save_sheets_pdf(parent, title, build, "apriltags_alignement.pdf")
    return print_sheets(parent, title, build)


def find_editor_window(widget):
    """La fenêtre principale (celle qui porte l'éditeur vectoriel) : on
    remonte les parents, puis on cherche parmi les fenêtres de l'application."""
    from PyQt6.QtWidgets import QApplication

    def is_editor(w):
        return hasattr(w, "vector_canvas") and hasattr(w, "layer_manager")

    current = widget
    while current is not None:
        if is_editor(current):
            return current
        current = current.parent()
    for top in QApplication.topLevelWidgets():
        if is_editor(top):
            return top
    return None


def add_template_to_editor(parent, targets):
    """Ajoute à l'éditeur vectoriel le gabarit de pose des tags (un cadre de
    la taille du tag et son numéro, aux positions du plateau), à marquer au
    laser sur le plateau. Renvoie True si le gabarit a été ajouté."""
    from PyQt6.QtWidgets import QMessageBox

    title = tr("camera.template.title")
    targets = list(targets)
    if not targets:
        QMessageBox.warning(parent, title, tr("camera.align_wizard.bad_grid"))
        return False
    editor = find_editor_window(parent)
    if editor is None:
        QMessageBox.warning(parent, title, tr("camera.align_wizard.tags_unavailable"))
        return False
    if not editor.layer_manager.layers:
        QMessageBox.warning(parent, title, tr("vector.no_layer_body"))
        return False
    try:
        from laser_studio.vector.importers import apriltag_template_to_objects

        layer = editor.layer_manager.engrave_layer() or editor.layer_manager.layers[0]
        objects = apriltag_template_to_objects(targets, layer.id, bed_w_mm=editor.machine.bed_w)
        canvas = editor.vector_canvas
        canvas.push_undo_snapshot()
        items = [canvas.add_object(obj) for obj in objects]
        canvas.scene_obj.clearSelection()
        for item in items:
            item.setSelected(True)
    except Exception as error:  # la vraie cause plutôt qu'un message vague
        import traceback

        traceback.print_exc()
        QMessageBox.critical(parent, title, f"{type(error).__name__}: {error}")
        return False
    QMessageBox.information(
        parent, title,
        tr("camera.template.added").format(
            n=len(targets), size=f"{targets[0].size_mm:g}", layer=layer.name),
    )
    return True
