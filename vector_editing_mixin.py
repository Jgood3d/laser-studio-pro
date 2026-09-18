"""Édition des objets vectoriels (texte, formes, SVG) sur le canevas."""
from PyQt6.QtWidgets import (QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QDialog)
from PyQt6.QtCore import Qt
from vector_layers import (
    TextInsertDialog, ShapeInsertDialog, TextObject, SvgPathObject, extract_svg_objects, AssignLayerDialog
)
from i18n import tr

class VectorEditingMixin:
    def update_vector_work_area(self, *args):
        """Synchronise la zone de travail de l'éditeur vectoriel avec les
        dimensions physiques du graveur (onglet 'Paramètres Machine'), et non
        plus avec les dimensions du job en cours."""
        if hasattr(self, "vector_canvas") and hasattr(self, "spin_machine_w"):
            self.vector_canvas.set_work_area(self.spin_machine_w.value(), self.spin_machine_h.value())

    def on_layers_changed(self):
        """Un calque a changé (couleur, mode, puissance, ajout/suppression...) :
        on rafraîchit les couleurs des objets du canevas et la table de
        l'onglet 'Calques' (sauf si c'est elle-même qui vient d'émettre le
        changement, pour ne pas interrompre une saisie en cours, ex: en train
        de taper un nom)."""
        if hasattr(self, "vector_canvas"):
            self.vector_canvas.refresh_all()
        sender = self.sender()
        if hasattr(self, "layer_widget") and sender is not self.layer_widget:
            self.layer_widget.refresh()
        self._refresh_engrave_layer_combo()
        self._on_engrave_layer_selected()

    def _refresh_engrave_layer_combo(self):
        """Tient à jour la liste déroulante 'Calque pour la gravure image',
        sans perdre la sélection courante si le calque existe encore."""
        if not hasattr(self, "combo_engrave_layer"):
            return
        current_id = self.combo_engrave_layer.currentData()
        self.combo_engrave_layer.blockSignals(True)
        self.combo_engrave_layer.clear()
        for layer in self.layer_manager.layers:
            self.combo_engrave_layer.addItem(f"{layer.name}  [{layer.mode}]", layer.id)
        if current_id:
            idx = self.combo_engrave_layer.findData(current_id)
            if idx >= 0:
                self.combo_engrave_layer.setCurrentIndex(idx)
        self.combo_engrave_layer.blockSignals(False)

    def _on_engrave_layer_selected(self, *_args):
        """La gravure image utilise toujours la puissance/vitesse du calque
        choisi ici (plus de saisie manuelle séparée)."""
        if not hasattr(self, "combo_engrave_layer"):
            return
        layer_id = self.combo_engrave_layer.currentData()
        layer = self.layer_manager.get(layer_id) if layer_id else None
        if layer:
            self.spin_speed_engrave.setValue(int(layer.speed))
            self.spin_power_engrave.setValue(int(layer.power))

    def insert_text_object(self):
        if not self.layer_manager.layers:
            QMessageBox.warning(
    self,
    tr("vector.no_layer_title"),
    tr("vector.no_layer_body")
)
            return
        dialog = TextInsertDialog(self.layer_manager, parent=self)
        if dialog.exec():
            obj = dialog.get_object()
            self.vector_canvas.push_undo_snapshot()
            self.vector_canvas.add_object(obj)

    def insert_shape_object(self):
        if not self.layer_manager.layers:
            QMessageBox.warning(self, "Aucun calque", "Créez d'abord un calque dans l'onglet 'Calques (Layers)'.")
            return
        dialog = ShapeInsertDialog(self.layer_manager, parent=self)
        if dialog.exec():
            obj = dialog.get_object()
            self.vector_canvas.push_undo_snapshot()
            self.vector_canvas.add_object(obj)

    def edit_selected_vector_object(self):
        item, obj = self.vector_canvas.selected_object()
        if obj is None:
            QMessageBox.information(
    self,
    tr("vector.selection_title"),
    tr("vector.no_selection")
)
            return
        self._open_edit_dialog(item, obj)

    def edit_vector_object(self, obj):
        """Appelé sur double-clic d'un objet du canevas."""
        item, current_obj = self.vector_canvas.selected_object()
        if current_obj is not obj:
            # Sécurité : retrouve l'item correspondant si la sélection n'est pas
            # encore synchronisée au moment du double-clic.
            for it in self.vector_canvas.scene_obj.items():
                if getattr(it, "obj", None) is obj:
                    item = it
                    break
        self._open_edit_dialog(item, obj)

    def _open_edit_dialog(self, item, obj):
        if isinstance(obj, TextObject):
            dialog = TextInsertDialog(self.layer_manager, text_obj=obj, parent=self)
            if dialog.exec():
                self.vector_canvas.push_undo_snapshot()
                dialog.get_object()
                item.refresh()
                self.on_vector_selection_changed(obj)
        elif isinstance(obj, SvgPathObject):
            dialog = AssignLayerDialog(self.layer_manager, svg_obj=obj,
                                        title=tr("vector.svg_properties"), parent=self)
            if dialog.exec():
                self.vector_canvas.push_undo_snapshot()
                dialog.apply_to(obj)
                item.refresh()
                self.on_vector_selection_changed(obj)
        else:
            dialog = ShapeInsertDialog(self.layer_manager, shape_obj=obj, parent=self)
            if dialog.exec():
                self.vector_canvas.push_undo_snapshot()
                dialog.get_object()
                item.refresh()
                self.on_vector_selection_changed(obj)

    def rotate_selected_vector_object(self):
        item, obj = self.vector_canvas.selected_object()
        if obj is None:
            QMessageBox.information(self, "Sélection", "Sélectionnez d'abord un objet dans le canevas.")
            return
        self.vector_canvas.push_undo_snapshot()
        obj.rotation_deg = (obj.rotation_deg + 90.0) % 360.0
        item.refresh()
        self.on_vector_selection_changed(obj)

    def duplicate_selected_vector_object(self):
        self.vector_canvas.duplicate_selected()

    def delete_selected_vector_object(self):
        self.vector_canvas.remove_selected()

    def on_vector_selection_changed(self, obj):
        if obj is None:
            self.lbl_vector_selection.setText("Aucune sélection")
            self.pos_box_vector.setEnabled(False)
            return
        layer = self.layer_manager.get(obj.layer_id)
        layer_name = layer.name if layer else "?"
        if isinstance(obj, TextObject):
            desc = f"Texte : « {obj.text} » — police {obj.font_family}, {obj.size_mm:.1f} mm — Calque : {layer_name}"
        elif isinstance(obj, SvgPathObject):
            desc = f"Élément SVG importé ({obj.source_tag}) — Calque : {layer_name} — double-clic pour changer de calque/taille"
        else:
            desc = f"Forme : {obj.shape_type} ({obj.width_mm:.1f} x {obj.height_mm:.1f} mm) — Calque : {layer_name}"
        self.lbl_vector_selection.setText(desc)

        self.pos_box_vector.setEnabled(True)
        self.spin_vec_x.blockSignals(True)
        self.spin_vec_y.blockSignals(True)
        self.spin_vec_rot.blockSignals(True)
        self.spin_vec_x.setValue(obj.x_mm)
        self.spin_vec_y.setValue(obj.y_mm)
        self.spin_vec_rot.setValue(obj.rotation_deg)
        self.spin_vec_x.blockSignals(False)
        self.spin_vec_y.blockSignals(False)
        self.spin_vec_rot.blockSignals(False)

        self.combo_vec_layer.blockSignals(True)
        self.combo_vec_layer.clear()
        for l in self.layer_manager.layers:
            self.combo_vec_layer.addItem(f"{l.name}  [{l.mode}]", l.id)
        idx = self.combo_vec_layer.findData(obj.layer_id)
        if idx >= 0:
            self.combo_vec_layer.setCurrentIndex(idx)
        self.combo_vec_layer.blockSignals(False)

    def on_vector_layer_spin_changed(self, _idx):
        item, obj = self.vector_canvas.selected_object()
        if obj is None:
            return
        new_layer_id = self.combo_vec_layer.currentData()
        if new_layer_id and new_layer_id != obj.layer_id:
            self.vector_canvas.push_undo_snapshot()
            obj.layer_id = new_layer_id
            item.refresh()

    def on_vector_object_moved(self, obj):
        """Objet déplacé à la souris : on met à jour les champs X/Y sans
        redéclencher on_vector_position_spin_changed (boucle de signaux)."""
        if self.pos_box_vector.isEnabled():
            self.spin_vec_x.blockSignals(True)
            self.spin_vec_y.blockSignals(True)
            self.spin_vec_x.setValue(obj.x_mm)
            self.spin_vec_y.setValue(obj.y_mm)
            self.spin_vec_x.blockSignals(False)
            self.spin_vec_y.blockSignals(False)

    def on_vector_position_spin_changed(self, _value):
        """Saisie manuelle d'un offset X/Y/rotation précis pour l'objet sélectionné."""
        item, obj = self.vector_canvas.selected_object()
        if obj is None:
            return
        self.vector_canvas.set_object_position(
            obj, self.spin_vec_x.value(), self.spin_vec_y.value(), self.spin_vec_rot.value()
        )

    def toggle_fullscreen_vector_editor(self):
        """Ouvre l'éditeur vectoriel (texte/formes/SVG) dans une fenêtre à
        part, maximisée, pour travailler plus confortablement. Fermer cette
        fenêtre (bouton dédié, Échap, ou la croix) remet l'éditeur à sa place
        normale dans l'onglet."""
        idx = self.main_tabs_view.indexOf(self.tab_vector_editor)
        if idx == -1:
            return  # déjà sorti (fenêtre plein écran probablement déjà ouverte)

        dialog = QDialog(self)
        # Fenêtre indépendante à part entière (pas une simple boîte de
        # dialogue) : ça lui donne les boutons minimiser/agrandir/fermer
        # standards de Windows et un vrai comportement plein écran.
        dialog.setWindowFlags(Qt.WindowType.Window)
        dialog.setWindowTitle(tr("vector.fullscreen_title"))

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(4, 4, 4, 4)

        btn_close_fullscreen = QPushButton(
    tr("vector.close_fullscreen")
)
        btn_close_fullscreen.setStyleSheet("background-color: #8f2b2b; color: white; padding: 6px; font-weight: bold;")
        btn_close_fullscreen.clicked.connect(dialog.close)
        dlg_layout.addWidget(btn_close_fullscreen)

        dlg_layout.addWidget(self.tab_vector_editor)
        self.tab_vector_editor.setVisible(True)

        def restore(_result=None):
            dlg_layout.removeWidget(self.tab_vector_editor)
            self.tab_vector_editor.setParent(None)
            self.main_tabs_view.insertTab(
    idx,
    self.tab_vector_editor,
    tr("tab.vector_editor")
)
            self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
            self.tab_vector_editor.setVisible(True)

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)

    def import_svg_to_vector_editor(self):
        """Importe un SVG dans l'éditeur vectoriel : chaque tracé/forme devient
        un objet indépendant (« dégroupé »), assignable à un calque différent
        (découpe, gravure remplie...), avec aperçu visuel immédiat."""
        if not self.layer_manager.layers:
            QMessageBox.warning(self, "Aucun calque", "Créez d'abord un calque dans l'onglet 'Calques (Layers)'.")
            return
        path, _ = QFileDialog.getOpenFileName(
    self,
    tr("vector.import_title"),
    "",
    tr("vector.svg_filter")
)
        if not path:
            return
        default_layer_id = self.layer_manager.layers[0].id
        try:
            objects = extract_svg_objects(path, default_layer_id, self.spin_machine_h.value())
        except Exception as e:
            QMessageBox.critical(
    self,
    tr("vector.svg_error_title"),
    tr("vector.svg_error").format(error=e)
)
            return
        if not objects:
            QMessageBox.information(
    self,
    tr("vector.svg_empty_title"),
    tr("vector.svg_empty")
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
        layer=self.layer_manager.layers[0].name
    )
)

    def load_svg(self):
        path, _ = QFileDialog.getOpenFileName(
    self,
    tr("vector.open_svg_title"),
    "",
    tr("vector.svg_filter")
)
        if path:
            self.loaded_svg_path = path
            self.txt_console.append(
    tr("vector.svg_loaded").format(path=path)
)
