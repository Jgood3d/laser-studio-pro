"""SVG créé par l'onglet « Vectorisation d'image » (Png2SvgTab) : envoi vers l'éditeur vectoriel et
enregistrement dans un fichier."""

import os
import tempfile

from laser_common.files import atomic_write_text
from laser_studio.i18n import tr
from laser_studio.vector.svg_tree_import import import_svg_tree


class Png2SvgController:
    """Transforme le SVG de l'onglet en objets de l'éditeur vectoriel, ou l'enregistre.

    Même lecture que le bouton « Importer » (vector/svg_tree_import.py), via un fichier temporaire : le
    convertisseur ne travaille qu'en mémoire. Tout va sur le calque SVG par défaut.

        png2svg = Png2SvgController(
            self, self.layer_manager,
            bed_height=lambda: self.machine.bed_h,
            add_to_vector_editor=self.vector_editor.add_objects,
        )
        tab.send_to_vector_requested.connect(png2svg.send_to_vector_editor)
        tab.export_requested.connect(png2svg.export_svg)

    `parent` : fenêtre des messages. `layer_manager` : calques (les objets
    vont sur le calque SVG par défaut). `bed_height()` : profondeur du lit
    en mm. `add_to_vector_editor(objects)` : ajoute les objets à l'éditeur
    et l'affiche.
    """

    def __init__(
        self, parent, layer_manager, bed_height, add_to_vector_editor, dialogs=None
    ):
        # Boîtes de dialogue (UserDialogs) : celles de la fenêtre, ou un objet
        # qui répond à la place de l'utilisateur dans les tests.
        if dialogs is None:
            from laser_studio.ui.user_dialogs import UserDialogs
            dialogs = UserDialogs(parent)
        self._dialogs = dialogs
        self._layers = layer_manager
        self._bed_height = bed_height
        self._add_to_vector_editor = add_to_vector_editor

    def send_to_vector_editor(self, svg_text):
        """Ajoute les objets du SVG à l'éditeur vectoriel, puis le dit."""
        if not self._layers.layers:
            self._dialogs.warning(tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        try:
            layer = self._layers.default_svg_layer()
            objects = self._svg_objects(svg_text, layer.id)
        except Exception as e:
            self._dialogs.error(tr("vector.svg_error_title"), tr("vector.svg_error").format(error=e))
            return
        if not objects:
            self._dialogs.info(tr("vector.svg_empty_title"), tr("vector.svg_empty"))
            return
        self._add_to_vector_editor(objects)
        self._dialogs.notify(tr("vector.svg_success").format(count=len(objects), layer=layer.name))

    def export_svg(self, svg_text):
        """Enregistre le SVG dans le fichier choisi par l'utilisateur. Renvoie le chemin, ou None."""
        path = self._dialogs.save_file(tr("png2svg.export_svg"), "vectorisation.svg", "SVG (*.svg)")
        if not path:
            return None
        if not path.lower().endswith(".svg"):
            path += ".svg"
        try:
            atomic_write_text(path, svg_text)
        except OSError as error:
            self._dialogs.error(tr("png2svg.export_svg"), str(error))
            return None
        self._dialogs.notify(tr("png2svg.export_success"))
        return path

    def _svg_objects(self, svg_text, layer_id):
        """Objets vectoriels du SVG, tous sur `layer_id` (l'importeur lit un fichier : le texte passe par
        un fichier temporaire)."""
        fd, path = tempfile.mkstemp(suffix=".svg")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(svg_text)
            return import_svg_tree(path, lambda _role: layer_id, self._bed_height())
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
