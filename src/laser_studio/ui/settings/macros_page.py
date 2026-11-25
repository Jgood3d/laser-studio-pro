"""Page « Macros » de la fenêtre Paramètres : l'éditeur des macros (MacroEditorDialog), posé comme un widget.
« Enregistrer » remplace la liste (save), « Annuler les modifications » revient à la liste enregistrée.

    page = MacrosPage(lambda: MacroEditorDialog(*macros.editor_args()), macros.save)
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout, QWidget

from laser_studio.i18n import tr


class MacrosPage(QWidget):
    """`make_editor()` : un éditeur neuf, rempli des macros enregistrées ; `save(macros)` : enregistre la liste
    validée. L'éditeur n'est construit qu'au premier affichage de la page (et refait après chaque
    enregistrement ou annulation)."""

    def __init__(self, make_editor, save, parent=None):
        super().__init__(parent)
        self._make_editor = make_editor
        self._save = save
        self.editor = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def showEvent(self, event):
        if self.editor is None:
            self.reload()
        super().showEvent(event)

    def reload(self):
        """Éditeur neuf, sur la liste enregistrée."""
        if self.editor is not None:
            self.editor.setParent(None)
            self.editor.deleteLater()
        editor = self._make_editor()
        editor.setWindowFlags(Qt.WindowType.Widget)
        for box in editor.findChildren(QDialogButtonBox):
            ok = box.button(QDialogButtonBox.StandardButton.Ok)
            cancel = box.button(QDialogButtonBox.StandardButton.Cancel)
            if ok is not None:
                ok.setText(tr("common.save"))
            if cancel is not None:
                cancel.setText(tr("macros.discard"))
        editor.accepted.connect(lambda: self._saved(editor))
        editor.rejected.connect(self.reload)
        self._layout.addWidget(editor)
        self.editor = editor

    def _saved(self, editor):
        self._save(editor.result_macros)
        self.reload()
