"""Import d'un dessin dans l'éditeur vectoriel : SVG ou DXF choisi ou déposé, export de Stencil Studio (objets
rangés dans les calques d'après leur calque d'origine). La lecture est dans vector/ (svg_tree_import, dxf,
importers), le placement du dessin par VectorEditorController.import_objects.

    importer = VectorImporter(editor)        # editor.importer
    importer.open_dialog()                   # « Importer SVG / DXF »
    importer.import_file(path)               # glisser-déposer
    importer.import_stencil_export(path)     # signal export_ready de Stencil Studio
"""
from laser_studio.controllers.stencil_import import (
    import_summary, remove_temporary_export, route_objects, route_tree,
)
from laser_studio.i18n import tr
from laser_studio.vector import dxf as dxf_import
from laser_studio.vector.importers import dxf_to_objects
from laser_studio.vector.svg_tree_import import import_svg_tree, svg_tree_counts


class VectorImporter:
    """`editor` : VectorEditorController (calques, machine, boîtes de dialogue, placement, barre d'état)."""

    def __init__(self, editor):
        self.editor = editor

    def open_dialog(self):
        """Importe un SVG ou un DXF choisi par l'utilisateur. Le dessin arrive groupé (un objet, ou un par calque
        DXF) : on le manipule d'un bloc ; clic droit › Dégrouper pour séparer les tracés."""
        editor = self.editor
        if not editor.require_layers():
            return
        path = editor.dialogs.open_file(tr("vector.import_title"), tr("vector.import_filter"))
        if path:
            self.import_file(path)

    def import_file(self, path):
        """Importe le fichier SVG ou DXF `path` (aussi appelé par le glisser-déposer)."""
        editor = self.editor
        if not editor.require_layers():
            return
        layers = editor.layers
        default_layer = layers.default_svg_layer()
        if path.lower().endswith(".dxf"):
            self._import_dxf(path, default_layer)
            return
        try:
            # Calques et groupes du fichier gardés ; calque de chaque objet d'après sa couleur ; ce qui est
            # masqué dans le fichier arrive sur le calque « Ignoré » (vector/svg_tree_import.py).
            objects = import_svg_tree(path, lambda role: layers.layer_for_role(role).id if role
                                      else default_layer.id, editor.machine.bed_h)
        except Exception as e:
            editor.dialogs.error(tr("vector.svg_error_title"), tr("vector.svg_error").format(error=e))
            return
        if not objects or all(obj.is_ignored() for obj in objects):
            editor.dialogs.info(tr("vector.svg_empty_title"), tr("vector.svg_empty"))
            return
        if not editor.import_objects(objects):
            return
        editor.dialogs.info(tr("vector.svg_success_title"),
                            tr("vector.svg_tree_success").format(**svg_tree_counts(objects, layers)))

    def import_stencil_export(self, path):
        """Fichier SVG ou DXF exporté par Stencil Studio : objets rangés dans les calques de LSP d'après leur
        calque d'origine (controllers/stencil_import.py), en une étape d'annulation. En cas d'échec, import
        standard (import_file), qui explique le problème. Le fichier temporaire est ensuite supprimé."""
        editor = self.editor
        try:
            stats = None
            lower = path.lower()
            if lower.endswith((".dxf", ".svg")) and editor.layers.layers:
                default_layer = editor.layers.default_svg_layer()
                if lower.endswith(".dxf"):
                    objects = dxf_to_objects(dxf_import.read_dxf(path), default_layer.id)
                    route = route_objects
                else:
                    # Même lecture que « Importer » ; les groupes de l'export (CUT, ENGRAVE…) sont gardés.
                    objects = import_svg_tree(path, lambda _role: default_layer.id, editor.machine.bed_h)
                    route = route_tree
                if not objects:
                    raise ValueError(tr("vector.svg_empty"))
                stats = route(objects, editor.layers, default_layer.id, focal=editor.machine.focal)
                if not editor.import_objects(objects):
                    return
            else:
                self.import_file(path)
            editor.status.emit(import_summary(path, stats))
        except Exception as e:  # fichier illisible ou vide : l'import standard affiche l'erreur
            editor.status.emit(tr("stencil.import_fallback").format(error=e))
            self.import_file(path)
        finally:
            remove_temporary_export(path)

    def _import_dxf(self, path, default_layer):
        """Import d'un DXF (texte ASCII) : tracés regroupés par calque DXF, calque LSP par défaut."""
        dialogs = self.editor.dialogs
        try:
            drawing = dxf_import.read_dxf(path)
        except dxf_import.DxfError as e:
            key = f"vector.dxf_err.{e.code}"
            text = tr(key)
            if text == key:
                text = tr("vector.dxf_error").format(error=e)
            else:
                text = text.format(**e.info) if e.info else text
            dialogs.error(tr("vector.dxf_title"), text)
            return
        except Exception as e:
            dialogs.error(tr("vector.dxf_title"), tr("vector.dxf_error").format(error=e))
            return
        skipped = ", ".join(f"{kind} x{count}" for kind, count in sorted(drawing.skipped.items()))
        objects = dxf_to_objects(drawing, default_layer.id)
        if not objects:
            message = tr("vector.dxf_empty")
            if skipped:
                message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
            dialogs.info(tr("vector.dxf_title"), message)
            return
        if not self.editor.import_objects(objects):
            return
        message = tr("vector.dxf_success").format(
            count=len(objects), layer=default_layer.name, unit=dxf_import.units_label(drawing))
        if skipped:
            message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
        dialogs.info(tr("vector.dxf_title"), message)
