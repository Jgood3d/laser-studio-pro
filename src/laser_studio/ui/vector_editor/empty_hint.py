"""Accueil du canevas vide, au centre : de gros boutons pour commencer (importer un fichier, dessiner une forme,
ouvrir la bibliothèque, vectoriser une image), puis un par générateur ; masqués dès qu'un objet est sur le
canevas.

    hint = EmptyCanvasHint(canvas)
    hint.command.connect(tab.command)            # « import », « shape », « library », « vectorize », « box »…
"""
from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.utils import palette_icon

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


class EmptyCanvasHint(QWidget):
    """Posé au centre de `canvas` (VectorCanvasView), visible tant que son document est vide."""

    command = pyqtSignal(str)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.setObjectName("empty_canvas_hint")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "#empty_canvas_hint { background: palette(window); border: 1px solid palette(mid); border-radius: 14px; }"
            " QToolButton { background: palette(button); border: 1px solid palette(mid); border-radius: 10px;"
            " padding: 16px 20px; min-width: 120px; }"
            " QToolButton:hover { border: 1px solid palette(highlight); }")
        title = QLabel(tr("vector.empty_title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: palette(placeholder-text); font-size: 15px;")
        self.buttons = {}
        start = self._row(BUTTONS, 40)
        generators_title = QLabel(tr("vector.empty_generators"))
        generators_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        generators_title.setStyleSheet("color: palette(placeholder-text);")
        generators = self._row([(name, _without_emoji(tr(key)), icon) for name, key, icon in GENERATOR_BUTTONS], 28,
                               translate=False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addLayout(start)
        layout.addWidget(generators_title)
        layout.addLayout(generators)
        document = canvas.document
        for signal in (document.object_added, document.object_removed, document.objects_reset):
            signal.connect(self.refresh)
        canvas.installEventFilter(self)
        self.refresh()

    def _row(self, entries, icon_px, translate=True):
        """Rangée de gros boutons (icône au-dessus du libellé) ; chacun émet command(nom)."""
        row = QHBoxLayout()
        row.setSpacing(12)
        for name, text, icon in entries:
            button = QToolButton()
            button.setText(tr(text) if translate else text)
            button.setIcon(palette_icon(icon, self.palette()))
            button.setIconSize(QSize(icon_px, icon_px))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)   # libellé jamais rogné
            button.clicked.connect(lambda _checked=False, n=name: self.command.emit(n))
            row.addWidget(button)
            self.buttons[name] = button
        return row

    def refresh(self, *_args):
        """Visible si le canevas n'a aucun objet, centré sur lui."""
        self.setVisible(not self.canvas.document.objects)
        self.adjustSize()
        self.move((self.canvas.width() - self.width()) // 2, (self.canvas.height() - self.height()) // 2)
        self.raise_()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.refresh()
        return super().eventFilter(watched, event)
