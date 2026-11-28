"""Carte d'accueil posée au centre d'une zone vide (canevas, aperçu d'image) : un titre et des rangées de gros
boutons pour commencer, masquée dès que la zone a un contenu.

    hint = StartHint(view, tr("img.empty_title"), [(None, [("open", tr("img.empty_open"), "document-open")], 40)],
                     is_empty=lambda: image is None)
    hint.command.connect(...)                    # nom du bouton cliqué
    hint.refresh()                               # après un changement de contenu
"""
from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from laser_studio.ui.utils import palette_icon


class StartHint(QWidget):
    """Posée au centre de `host`, visible tant que `is_empty()` est vrai. `rows` : (sous-titre ou None,
    [(nom, libellé, icône Breeze)], taille des icônes en px) ; chaque bouton émet command(nom)."""

    command = pyqtSignal(str)

    def __init__(self, host, title, rows, is_empty):
        super().__init__(host)
        self.host = host
        self._is_empty = is_empty
        self.setObjectName("start_hint")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "#start_hint { background: palette(window); border: 1px solid palette(mid); border-radius: 14px; }"
            " QToolButton { background: palette(button); border: 1px solid palette(mid); border-radius: 10px;"
            " padding: 16px 20px; min-width: 120px; }"
            " QToolButton:hover { border: 1px solid palette(highlight); }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(self._label(title, "font-size: 15px;"))
        self.buttons = {}
        for subtitle, entries, icon_px in rows:
            if subtitle:
                layout.addWidget(self._label(subtitle, ""))
            layout.addLayout(self._row(entries, icon_px))
        host.installEventFilter(self)
        self.refresh()

    @staticmethod
    def _label(text, style):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: palette(placeholder-text); {style}")
        return label

    def _row(self, entries, icon_px):
        """Rangée de gros boutons (icône au-dessus du libellé)."""
        row = QHBoxLayout()
        row.setSpacing(12)
        for name, text, icon in entries:
            button = QToolButton()
            button.setText(text)
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
        """Visible si la zone est vide, centrée sur elle."""
        self.setVisible(self._is_empty())
        self.adjustSize()
        self.move((self.host.width() - self.width()) // 2, (self.host.height() - self.height()) // 2)
        self.raise_()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.refresh()
        return super().eventFilter(watched, event)
