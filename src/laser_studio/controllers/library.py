"""Bibliothèque de modèles : catalogue (page « Bibliothèque » de la fenêtre des générateurs, voir
GeneratorsController) et import du modèle choisi dans l'éditeur vectoriel."""

from laser_studio.i18n import get_current_language, tr
from laser_studio.library.catalog import library_roots, load_catalog
from laser_studio.vector.svg_import import SvgImportError
from laser_studio.vector.svg_tree_import import import_library_svg
from laser_studio.core.preferences import ui_preferences

# Clé de UIConfig : taille des vignettes de la bibliothèque (px).
ICON_SIZE_SETTING = "library_icon_size"


class LibraryController:
    """Catalogue de la bibliothèque et import du modèle choisi.

        library = LibraryController(
            layers, bed_height=lambda: machine.bed_h,
            add_to_vector_editor=editor.import_objects, dialogs=dialogs,
        )
        generators = GeneratorsController(editor, layout, forms, library=library)

    La bibliothèque est une page de la fenêtre des générateurs (EditorForms.generators) : le contrôleur
    ne construit aucune fenêtre.

    Le modèle est lu comme un SVG ordinaire (vector.svg_tree_import) : chaque
    tracé va sur le calque du rôle de sa couleur (découpe, gravure, marquage) ;
    sans calque de ce rôle, sur le calque SVG par défaut. `roots()` : dossiers de la bibliothèque (voir
    library_roots, remplaçable pour les tests).
    """

    def __init__(self, layer_manager, bed_height, add_to_vector_editor, *, dialogs, roots=library_roots):
        # Messages (UserDialogs) : ceux de la fenêtre, ou un objet qui répond à la place de l'utilisateur.
        self._dialogs = dialogs
        self._layers = layer_manager
        self._bed_height = bed_height
        self._add_to_vector_editor = add_to_vector_editor
        self._roots = roots

    def catalog(self):
        return load_catalog(self._roots(), get_current_language())

    def generator_request(self):
        """Arguments de la page « Bibliothèque » de la fenêtre des générateurs (EditorForms.generators) :
        (catégories, taille des vignettes, rappel qui la mémorise), ou None si la bibliothèque est vide."""
        categories = self.catalog()
        if not categories:
            return None
        try:
            icon_size = ui_preferences().get_int(ICON_SIZE_SETTING, 160)
        except (TypeError, ValueError):
            icon_size = 160
        return categories, icon_size, lambda size: ui_preferences().set(ICON_SIZE_SETTING, size)

    def import_choice(self, chosen):
        """Importe le choix de la page « Bibliothèque » : (modèle, variantes, textes)."""
        item, variants, texts = chosen
        return self.import_item(item, variants, texts)

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
