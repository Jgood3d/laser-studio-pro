"""Bibliothèque de modèles : ouverture de la fenêtre et import du modèle
choisi dans l'éditeur vectoriel."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog, QMessageBox

from laser_studio.i18n import get_current_language, tr
from laser_studio.library.catalog import library_roots, load_catalog
from laser_studio.vector.svg_import import SvgImportError, import_svg

# Clé de UIConfig : taille des vignettes de la bibliothèque (px).
ICON_SIZE_SETTING = "library_icon_size"


def _settings():
    return QSettings("LaserStudioPro", "UIConfig")


class LibraryController:
    """Ouvre la bibliothèque et importe le modèle choisi.

        library = LibraryController(
            self, self.layer_manager,
            bed_height=lambda: self.machine.bed_h,
            add_to_vector_editor=self._add_objects_to_vector_editor,
        )
        action.triggered.connect(library.open)

    Chaque tracé du modèle va sur le calque de même rôle (découpe, gravure,
    marquage, voir vector.svg_import) ; sans calque de ce rôle, sur le
    calque SVG par défaut. `roots()` : dossiers de la bibliothèque (voir
    library_roots, remplaçable pour les tests).
    """

    def __init__(self, parent, layer_manager, bed_height, add_to_vector_editor,
                 roots=library_roots):
        self._parent = parent
        self._layers = layer_manager
        self._bed_height = bed_height
        self._add_to_vector_editor = add_to_vector_editor
        self._roots = roots

    def catalog(self):
        return load_catalog(self._roots(), get_current_language())

    def open(self):
        """Fenêtre de la bibliothèque ; importe le modèle choisi."""
        from laser_studio.ui.dialogs.library import LibraryDialog
        if not self._layers.layers:
            QMessageBox.warning(self._parent, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        categories = self.catalog()
        if not categories:
            QMessageBox.information(self._parent, tr("library.title"), tr("library.empty"))
            return
        try:
            icon_size = int(_settings().value(ICON_SIZE_SETTING, 160))
        except (TypeError, ValueError):
            icon_size = 160
        dialog = LibraryDialog(self._parent, categories, icon_size)
        dialog.icon_size_changed.connect(lambda size: _settings().setValue(ICON_SIZE_SETTING, size))
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.chosen() is None:
            return
        item, variants = dialog.chosen()
        self.import_item(item, variants)

    def layer_for_role(self, role):
        """Identifiant du calque de rôle `role`, sinon du calque SVG par défaut."""
        for layer in self._layers.layers:
            if getattr(layer, "role", None) == role:
                return layer.id
        return self._layers.default_svg_layer().id

    def import_item(self, item, variants=None):
        """Importe le modèle `item` (avec ses `variants`) dans l'éditeur
        vectoriel. Renvoie les objets ajoutés (liste vide en cas d'erreur)."""
        try:
            artwork = import_svg(item.svg_path, variants=variants, bed_h_mm=self._bed_height())
        except SvgImportError as e:
            QMessageBox.critical(self._parent, tr("vector.svg_error_title"),
                                 tr("vector.svg_error").format(error=e))
            return []
        if not artwork.items:
            QMessageBox.information(self._parent, tr("vector.svg_empty_title"), tr("vector.svg_empty"))
            return []
        for role, obj in artwork.items:
            obj.layer_id = self.layer_for_role(role)
        self._add_to_vector_editor(artwork.objects)
        return artwork.objects
