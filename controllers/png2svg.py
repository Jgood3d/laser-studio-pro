"""Envoi vers l'éditeur vectoriel du SVG créé par l'onglet « Vectorisation
d'image » (Png2SvgTab)."""

import os
import tempfile

from PyQt6.QtWidgets import QMessageBox

from i18n import tr
from vector_layers import extract_svg_objects


class Png2SvgController:
    """Transforme le SVG de l'onglet en objets de l'éditeur vectoriel.

    Même chemin que l'import SVG classique (extract_svg_objects), via un
    fichier temporaire : le convertisseur ne travaille qu'en mémoire.

        png2svg = Png2SvgController(
            self, self.layer_manager,
            bed_height=lambda: self.spin_machine_h.value(),
            add_to_vector_editor=self._add_objects_to_vector_editor,
        )
        tab.send_to_vector_requested.connect(png2svg.send_to_vector_editor)

    `parent` : fenêtre des messages. `layer_manager` : calques (les objets
    vont sur le calque SVG par défaut). `bed_height()` : profondeur du lit
    en mm. `add_to_vector_editor(objects)` : ajoute les objets à l'éditeur
    et l'affiche.
    """

    def __init__(
        self, parent, layer_manager, bed_height, add_to_vector_editor
    ):
        self._parent = parent
        self._layers = layer_manager
        self._bed_height = bed_height
        self._add_to_vector_editor = add_to_vector_editor

    def send_to_vector_editor(self, svg_text):
        """Ajoute les objets du SVG à l'éditeur vectoriel, puis le dit."""
        if not self._layers.layers:
            QMessageBox.warning(
                self._parent,
                tr("vector.no_layer_title"),
                tr("vector.no_layer_body"),
            )
            return
        try:
            layer = self._layers.default_svg_layer()
            objects = self._svg_objects(svg_text, layer.id)
        except Exception as e:
            QMessageBox.critical(
                self._parent,
                tr("vector.svg_error_title"),
                tr("vector.svg_error").format(error=e),
            )
            return
        if not objects:
            QMessageBox.information(
                self._parent,
                tr("vector.svg_empty_title"),
                tr("vector.svg_empty"),
            )
            return
        self._add_to_vector_editor(objects)
        QMessageBox.information(
            self._parent,
            tr("vector.svg_success_title"),
            tr("vector.svg_success").format(
                count=len(objects), layer=layer.name
            ),
        )

    def _svg_objects(self, svg_text, layer_id):
        """Objets vectoriels du SVG (extract_svg_objects attend un
        chemin : le texte passe par un fichier temporaire)."""
        fd, path = tempfile.mkstemp(suffix=".svg")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(svg_text)
            return extract_svg_objects(path, layer_id, self._bed_height())
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
