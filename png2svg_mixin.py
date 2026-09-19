"""Intégration de l'onglet PNG -> SVG : construction de l'onglet et envoi
du SVG généré vers l'Éditeur Vectoriel (réutilise le même pipeline que
l'import SVG classique — extract_svg_objects — via un fichier temporaire,
puisque le convertisseur ne travaille qu'en mémoire)."""
import os
import tempfile

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QWidget

from png2svg_widget import PngToSvgWidget
from vector_layers import extract_svg_objects
from i18n import tr


class Png2SvgMixin:
    def _init_png2svg_tab(self):
        """Construit le conteneur de l'onglet PNG -> SVG : une barre d'outils
        (bouton plein écran, comme l'Éditeur Vectoriel) au-dessus du widget
        de conversion. Renvoie ce conteneur (self.tab_png2svg), à insérer
        dans main_tabs_view par l'appelant (ui_setup_mixin)."""
        self.tab_png2svg = QWidget()
        layout = QVBoxLayout(self.tab_png2svg)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        btn_fullscreen_png2svg = QPushButton(tr("png2svg.fullscreen"))
        btn_fullscreen_png2svg.clicked.connect(self.toggle_fullscreen_png2svg)
        toolbar.addWidget(btn_fullscreen_png2svg)
        layout.addLayout(toolbar)

        self.png2svg_widget = PngToSvgWidget()
        self.png2svg_widget.sendToVectorEditor.connect(self._on_png2svg_send_to_vector)
        layout.addWidget(self.png2svg_widget)

        return self.tab_png2svg

    def toggle_fullscreen_png2svg(self):
        """Ouvre l'onglet PNG -> SVG dans une fenêtre à part, maximisée,
        exactement comme toggle_fullscreen_vector_editor (voir
        vector_editing_mixin.py) : mêmes mécanismes de va-et-vient du
        widget entre l'onglet et la fenêtre plein écran."""
        idx = self.main_tabs_view.indexOf(self.tab_png2svg)
        if idx == -1:
            return  # déjà sorti (fenêtre plein écran probablement déjà ouverte)

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.WindowType.Window)
        dialog.setWindowTitle(tr("png2svg.fullscreen_title"))

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(4, 4, 4, 4)

        btn_close_fullscreen = QPushButton(tr("png2svg.close_fullscreen"))
        btn_close_fullscreen.setStyleSheet(
            "background-color: #8f2b2b; color: white; padding: 6px; font-weight: bold;"
        )
        btn_close_fullscreen.clicked.connect(dialog.close)
        dlg_layout.addWidget(btn_close_fullscreen)

        dlg_layout.addWidget(self.tab_png2svg)
        self.tab_png2svg.setVisible(True)

        def restore(_result=None):
            dlg_layout.removeWidget(self.tab_png2svg)
            self.tab_png2svg.setParent(None)
            self.main_tabs_view.insertTab(idx, self.tab_png2svg, tr("png2svg.tab_title"))
            self.main_tabs_view.setCurrentWidget(self.tab_png2svg)
            self.tab_png2svg.setVisible(True)

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)

    def _on_png2svg_send_to_vector(self, svg_text):
        """Reçoit le SVG généré par l'onglet PNG -> SVG, l'écrit dans un
        fichier temporaire (extract_svg_objects attend un chemin) et
        ajoute les objets résultants au canevas vectoriel, comme le fait
        l'import SVG classique (import_svg_to_vector_editor)."""
        if not self.layer_manager.layers:
            QMessageBox.warning(
                self,
                tr("vector.no_layer_title"),
                tr("vector.no_layer_body"),
            )
            return

        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".svg")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(svg_text)
            default_layer_id = self.layer_manager.layers[0].id
            objects = extract_svg_objects(tmp_path, default_layer_id, self.spin_machine_h.value())
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("vector.svg_error_title"),
                tr("vector.svg_error").format(error=e),
            )
            return
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        if not objects:
            QMessageBox.information(
                self,
                tr("vector.svg_empty_title"),
                tr("vector.svg_empty"),
            )
            return

        self.vector_canvas.push_undo_snapshot()
        for obj in objects:
            self.vector_canvas.add_object(obj)
        self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
        QMessageBox.information(
            self,
            tr("vector.svg_success_title"),
            tr("vector.svg_success").format(
                count=len(objects),
                layer=self.layer_manager.layers[0].name,
            ),
        )
