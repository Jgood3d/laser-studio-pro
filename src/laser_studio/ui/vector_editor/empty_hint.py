"""Accueil du canevas vide, au centre : de gros boutons pour commencer (importer un fichier, dessiner une forme,
ouvrir la bibliothèque, vectoriser une image), puis un par générateur ; masqués dès qu'un objet est sur le
canevas (carte commune : ui/widgets/start_hint.py).

    hint = EmptyCanvasHint(canvas)
    hint.command.connect(tab.command)            # « import », « shape », « library », « vectorize », « box »…
"""
from laser_studio.i18n import tr
from laser_studio.ui.widgets.start_hint import StartHint

# (commande de l'onglet, clé du libellé, icône Breeze) : pour commencer, puis les générateurs.
BUTTONS = (
    ("import", "vector.empty_import", "document-import"),
    ("shape", "vector.empty_shape", "shape-choose"),
    ("library", "vector.empty_library", "view-app-grid"),
    ("vectorize", "vector.empty_vectorize", "draw-bezier-curves"),
)
GENERATOR_BUTTONS = (
    ("box", "ui.vector_box_generator", "draw-cuboid"),
    ("puzzle", "ui.vector_puzzle_generator", "games-config-board"),
    ("ornament", "ui.vector_ornament_generator", "draw-ellipse"),
    ("keychain", "ui.vector_keychain_generator", "keychain"),
)


def _without_emoji(label):
    """Libellé sans son emoji de tête (📦, 🧩), qui ferait doublon avec l'icône."""
    return label.split(" ", 1)[-1] if label and not label[0].isalnum() else label


class EmptyCanvasHint(StartHint):
    """Posé au centre de `canvas` (VectorCanvasView), visible tant que son document est vide."""

    def __init__(self, canvas):
        self.canvas = canvas
        document = canvas.document
        super().__init__(canvas, tr("vector.empty_title"), [
            (None, [(name, tr(key), icon) for name, key, icon in BUTTONS], 40),
            (tr("vector.empty_generators"),
             [(name, _without_emoji(tr(key)), icon) for name, key, icon in GENERATOR_BUTTONS], 28),
        ], is_empty=lambda: not document.objects)
        for signal in (document.object_added, document.object_removed, document.objects_reset):
            signal.connect(self.refresh)
