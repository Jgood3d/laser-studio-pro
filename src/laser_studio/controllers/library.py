"""Bibliothèque de modèles : choix d'un modèle (fenêtre ouverte par EditorForms) et import dans
l'éditeur vectoriel."""

from laser_studio.i18n import get_current_language, tr
from laser_studio.library.catalog import library_roots, load_catalog
from laser_studio.vector.svg_import import SvgImportError
from laser_studio.vector.svg_tree_import import import_library_svg
from laser_studio.core.preferences import ui_preferences

# Clé de UIConfig : taille des vignettes de la bibliothèque (px).
ICON_SIZE_SETTING = "library_icon_size"


class LibraryController:
    """Ouvre la bibliothèque et importe le modèle choisi.

        library = LibraryController(
            layers, bed_height=lambda: machine.bed_h,
            add_to_vector_editor=editor.import_objects, forms=EditorForms(window), dialogs=dialogs,
        )
        action.triggered.connect(library.open)

    La fenêtre de la bibliothèque est ouverte par `forms.library(...)` (ui/vector_editor/forms.py) :
    le contrôleur ne construit aucune fenêtre.

    Le modèle est lu comme un SVG ordinaire (vector.svg_tree_import) : chaque
    tracé va sur le calque du rôle de sa couleur (découpe, gravure, marquage) ;
    sans calque de ce rôle, sur le calque SVG par défaut. `roots()` : dossiers de la bibliothèque (voir
    library_roots, remplaçable pour les tests).
    """

    def __init__(self, layer_manager, bed_height, add_to_vector_editor, *, forms, dialogs,
                 roots=library_roots):
        # Fenêtres (EditorForms) et messages (UserDialogs) : ceux de la fenêtre, ou des objets qui répondent
        # à la place de l'utilisateur dans les tests.
        self._forms = forms
        self._dialogs = dialogs
        self._layers = layer_manager
        self._bed_height = bed_height
        self._add_to_vector_editor = add_to_vector_editor
        self._roots = roots

    def catalog(self):
        return load_catalog(self._roots(), get_current_language())

    def open(self):
        """Fenêtre de la bibliothèque ; importe le modèle choisi."""
        if not self._layers.layers:
            self._dialogs.warning(tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        categories = self.catalog()
        if not categories:
            self._dialogs.info(tr("library.title"), tr("library.empty"))
            return
        try:
            icon_size = ui_preferences().get_int(ICON_SIZE_SETTING, 160)
        except (TypeError, ValueError):
            icon_size = 160
        chosen = self._forms.library(categories, icon_size,
                                     on_icon_size=lambda size: ui_preferences().set(ICON_SIZE_SETTING, size))
        if chosen is None:
            return
        item, variants, texts = chosen
        self.import_item(item, variants, texts)

    def layer_for_role(self, role):
        """Identifiant du calque de rôle `role`, sinon du calque SVG par défaut."""
        return self._layers.layer_for_role(role).id

    def import_item(self, item, variants=None, texts=None):
        """Importe le modèle `item` (avec ses `variants` et ses `texts`
        remplacés) dans l'éditeur vectoriel. Renvoie les objets ajoutés
        (liste vide en cas d'erreur)."""
        try:
            objects = import_library_svg(item.svg_path, self.layer_for_role, self._bed_height(),
                                         variants=variants, texts=texts)
        except SvgImportError as e:
            self._dialogs.error(tr("vector.svg_error_title"), tr("vector.svg_error").format(error=e))
            return []
        if not objects or all(obj.is_ignored() for obj in objects):
            self._dialogs.info(tr("vector.svg_empty_title"), tr("vector.svg_empty"))
            return []
        self._add_to_vector_editor(objects)
        return objects
