"""Édition des objets vectoriels (texte, formes, SVG) sur le canevas."""
from PyQt6.QtWidgets import (QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QDialog, QApplication)
from PyQt6.QtCore import Qt
from vector_layers import (
    TextInsertDialog, ShapeInsertDialog, TextObject, SvgPathObject, extract_svg_objects, AssignLayerDialog
)
from i18n import tr
import box_generator
import dxf_import
from ui.dialogs.box_generator import BoxGeneratorDialog, error_message
from vector_import import box_to_objects, decor_to_objects, dxf_to_objects
import nesting
from nesting_apply import apply_result, build_pieces
from ui.dialogs.nesting import NestingDialog

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
        if hasattr(self, "layers_tab") and sender is not self.layers_tab:
            self.layers_tab.refresh()
        self._refresh_engrave_layer()
        self._on_engrave_layer_selected()

    def _refresh_engrave_layer(self):
        """Calque de la gravure image (engrave_layer_id) : garde le calque
        choisi s'il existe encore. Sinon (démarrage, calque supprimé), prend
        le premier calque en mode gravure, à défaut le premier calque."""
        if self.layer_manager.get(self.engrave_layer_id) is not None:
            return
        layers = self.layer_manager.layers
        self.engrave_layer_id = self._first_engrave_layer_id() or (layers[0].id if layers else None)

    def _first_engrave_layer_id(self):
        """Identifiant du premier calque en mode Gravure Remplie, ou None
        s'il n'y en a aucun."""
        for layer in self.layer_manager.layers:
            if layer.mode == "Gravure Remplie":
                return layer.id
        return None

    def _engrave_layer_label(self):
        """Nom et mode du calque de la gravure image, ex. « Gravure Texte  [Gravure Remplie] »."""
        layer = self.layer_manager.get(self.engrave_layer_id)
        return f"{layer.name}  [{layer.mode}]" if layer else ""

    def _ensure_engrave_layer_for_image(self):
        """Appelé avant la génération du G-Code d'une image (Image Tramage /
        Séparation couleur) : si le calque sélectionné n'est pas en mode
        gravure, bascule sur le premier calque de gravure et applique sa
        puissance/vitesse. Sans calque de gravure, ne change rien."""
        layer = self.layer_manager.get(self.engrave_layer_id)
        if layer and layer.mode == "Gravure Remplie":
            return
        layer_id = self._first_engrave_layer_id()
        if layer_id is None:
            self.show_status_message(tr("vector.no_engrave_layer"))
            return
        self.engrave_layer_id = layer_id
        self._on_engrave_layer_selected()
        self.show_status_message(tr("vector.engrave_layer_auto").format(name=self._engrave_layer_label()))

    def _on_engrave_layer_selected(self, *_args):
        """La gravure image utilise toujours la puissance/vitesse du calque
        de gravure (plus de saisie manuelle séparée)."""
        layer = self.layer_manager.get(self.engrave_layer_id)
        if layer:
            self.set_engrave_settings(layer.speed, layer.power)

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
            QMessageBox.warning(self, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        dialog = ShapeInsertDialog(self.layer_manager, parent=self)
        if dialog.exec():
            obj = dialog.get_object()
            self.vector_canvas.push_undo_snapshot()
            self.vector_canvas.add_object(obj)

    def set_vector_draw_tool(self, tool):
        """Active un outil de dessin à la souris sur le canevas vectoriel.

        tool: None/'select', 'line', 'rect', 'ellipse'.
        Clic-glisser crée la forme ; Échap ou clic droit annule l'outil.
        """
        if not hasattr(self, "vector_canvas"):
            return
        if tool and tool not in (None, "select") and not self.layer_manager.layers:
            QMessageBox.warning(self, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            tool = None
        layer = self.layer_manager.default_svg_layer() if self.layer_manager.layers else None
        layer_id = layer.id if layer else None
        resolved = None if tool in (None, "select") else tool
        self.vector_canvas.set_draw_tool(resolved, layer_id=layer_id)
        for key, btn in getattr(self, "_vector_draw_buttons", {}).items():
            btn.blockSignals(True)
            btn.setChecked(key == resolved)
            btn.blockSignals(False)

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
            QMessageBox.information(self, tr("vector.selection_title"), tr("vector.no_selection"))
            return
        self.vector_canvas.push_undo_snapshot()
        obj.rotation_deg = (obj.rotation_deg + 90.0) % 360.0
        item.refresh()
        self.on_vector_selection_changed(obj)

    def duplicate_selected_vector_object(self):
        self.vector_canvas.duplicate_selected()

    def delete_selected_vector_object(self):
        self.vector_canvas.remove_selected()
        
    def _selected_vector_items(self):
        """Renvoie les éléments vectoriels sélectionnés dans le canevas."""
        return self.vector_canvas.selected_items_vector()

    def on_vector_selection_changed(self, obj):
        items = self._selected_vector_items()

        if not items:
            self.lbl_vector_selection.setText(tr("ui.no_selection_label"))
            self.pos_box_vector.setEnabled(False)
            self.pos_box_vector.setVisible(False)
            if hasattr(self, "pos_size_anchor_widget"):
                self.pos_size_anchor_widget.setVisible(False)
            return

        objects = [item.obj for item in items]

        boxes = [obj.world_path().boundingRect() for obj in objects]
        group_left = min(box.left() for box in boxes)
        group_bottom = min(box.top() for box in boxes)
        group_right = max(box.right() for box in boxes)
        group_top = max(box.bottom() for box in boxes)

        if len(objects) > 1:
            desc = (
                f"{len(objects)} objets sélectionnés — "
                f"Zone : {group_right - group_left:.2f} × "
                f"{group_top - group_bottom:.2f} mm"
            )
        else:
            obj = objects[0]
            layer = self.layer_manager.get(obj.layer_id)
            layer_name = layer.name if layer else "?"

            if isinstance(obj, TextObject):
                desc = (
                    f"Texte : « {obj.text} » — "
                    f"police {obj.font_family}, {obj.size_mm:.1f} mm — "
                    f"Calque : {layer_name}"
                )
            elif isinstance(obj, SvgPathObject):
                desc = (
                    f"Élément SVG importé ({obj.source_tag}) — "
                    f"Calque : {layer_name}"
                )
            else:
                desc = (
                    f"Forme : {obj.shape_type} "
                    f"({obj.width_mm:.1f} × {obj.height_mm:.1f} mm) — "
                    f"Calque : {layer_name}"
                )

        self.lbl_vector_selection.setText(desc)
        self.pos_box_vector.setEnabled(True)
        self.pos_box_vector.setVisible(True)

        self.spin_vec_x.blockSignals(True)
        self.spin_vec_y.blockSignals(True)
        self.spin_vec_rot.blockSignals(True)
        if hasattr(self, "spin_vec_w"):
            self.spin_vec_w.blockSignals(True)
            self.spin_vec_h.blockSignals(True)

        # X/Y : coin inférieur gauche du groupe
        self.spin_vec_x.setValue(group_left)
        self.spin_vec_y.setValue(group_bottom)
        self.spin_vec_rot.setValue(objects[0].rotation_deg)

        # Largeur / hauteur / ancrage : uniquement pour une forme (pas SVG ni texte)
        can_size = (
            len(objects) == 1
            and hasattr(objects[0], "width_mm")
            and hasattr(objects[0], "height_mm")
            and getattr(objects[0], "kind", None) == "shape"
        )
        if hasattr(self, "pos_size_anchor_widget"):
            self.pos_size_anchor_widget.setVisible(can_size)
        if hasattr(self, "spin_vec_w") and can_size:
            self.spin_vec_w.setValue(float(objects[0].width_mm))
            self.spin_vec_h.setValue(float(objects[0].height_mm))

        self.spin_vec_x.blockSignals(False)
        self.spin_vec_y.blockSignals(False)
        self.spin_vec_rot.blockSignals(False)
        if hasattr(self, "spin_vec_w"):
            self.spin_vec_w.blockSignals(False)
            self.spin_vec_h.blockSignals(False)

        self.combo_vec_layer.blockSignals(True)
        self.combo_vec_layer.clear()

        for layer in self.layer_manager.layers:
            self.combo_vec_layer.addItem(
                f"{layer.name}  [{layer.mode}]",
                layer.id
            )

        if len(objects) == 1:
            idx = self.combo_vec_layer.findData(objects[0].layer_id)
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
        """Déplace l'objet ou le groupe sélectionné vers l'offset demandé."""
        items = self._selected_vector_items()

        if not items:
            return

        objects = [item.obj for item in items]
        boxes = [obj.world_path().boundingRect() for obj in objects]

        current_left = min(box.left() for box in boxes)
        current_bottom = min(box.top() for box in boxes)

        target_left = self.spin_vec_x.value()
        target_bottom = self.spin_vec_y.value()

        delta_x = target_left - current_left
        delta_y = target_bottom - current_bottom

        self.vector_canvas.push_undo_snapshot()

        for item in items:
            item.obj.x_mm += delta_x
            item.obj.y_mm += delta_y
            item.refresh()

        # La rotation de groupe n'est pas modifiée ici.
        # Pour un seul objet, on conserve le comportement actuel.
        if len(items) == 1:
            item = items[0]
            item.obj.rotation_deg = self.spin_vec_rot.value()
            item.refresh()

    def _shape_world_corners(self, obj):
        """4 coins de la forme en coordonnées machine (après local_path + world_transform)."""
        from PyQt6.QtCore import QPointF
        path = obj.local_path()
        br = path.boundingRect()
        locals_pts = [
            QPointF(br.left(), br.top()),
            QPointF(br.right(), br.top()),
            QPointF(br.left(), br.bottom()),
            QPointF(br.right(), br.bottom()),
        ]
        wt = obj.world_transform()
        return [wt.map(p) for p in locals_pts]

    def _shape_world_anchor(self, obj, anchor_id):
        """Coin d'ancrage en mm machine (Y vers le haut).

        - origin : point de placement (x_mm, y_mm) = 1er point lors d'un tracé A→B
        - bl/br/tl/tr : coins du bounding box monde
        """
        from PyQt6.QtCore import QPointF
        if anchor_id == "origin":
            return QPointF(float(obj.x_mm), float(obj.y_mm))
        corners = self._shape_world_corners(obj)
        # Machine : Y haut → « bas » = plus petite ordonnée
        if anchor_id == "bl":
            return min(corners, key=lambda p: (p.y(), p.x()))
        if anchor_id == "br":
            return min(corners, key=lambda p: (p.y(), -p.x()))
        if anchor_id == "tl":
            return max(corners, key=lambda p: (p.y(), -p.x()))
        if anchor_id == "tr":
            return max(corners, key=lambda p: (p.y(), p.x()))
        return QPointF(float(obj.x_mm), float(obj.y_mm))

    def on_vector_size_spin_changed(self, _value):
        """Modifie largeur / hauteur d'une forme. Si l'ancrage est verrouillé,
        le coin (ou l'origine = 1er point) reste fixe dans le plan machine."""
        items = self._selected_vector_items()
        if len(items) != 1:
            return
        item = items[0]
        obj = item.obj
        if getattr(obj, "kind", None) != "shape":
            return
        if not hasattr(obj, "width_mm") or not hasattr(obj, "height_mm"):
            return
        new_w = self.spin_vec_w.value()
        new_h = self.spin_vec_h.value()
        if abs(new_w - obj.width_mm) < 1e-9 and abs(new_h - obj.height_mm) < 1e-9:
            return

        lock = bool(getattr(self, "chk_vec_anchor_lock", None) and self.chk_vec_anchor_lock.isChecked())
        anchor_id = "origin"
        if hasattr(self, "combo_vec_anchor") and self.combo_vec_anchor.currentData():
            anchor_id = self.combo_vec_anchor.currentData()

        self.vector_canvas.push_undo_snapshot()

        if lock:
            before = self._shape_world_anchor(obj, anchor_id)
            obj.width_mm = new_w
            obj.height_mm = new_h
            # Recalcule le coin après changement de taille
            after = self._shape_world_anchor(obj, anchor_id)
            obj.x_mm += before.x() - after.x()
            obj.y_mm += before.y() - after.y()
        else:
            obj.width_mm = new_w
            obj.height_mm = new_h

        item.refresh()
        # Rafraîchir X/Y affichés sans reboucler sur les spins de taille
        self.spin_vec_x.blockSignals(True)
        self.spin_vec_y.blockSignals(True)
        self.spin_vec_x.setValue(obj.x_mm)
        self.spin_vec_y.setValue(obj.y_mm)
        self.spin_vec_x.blockSignals(False)
        self.spin_vec_y.blockSignals(False)

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
        self._show_fullscreen_control(self.tab_vector_editor, False)

        def restore(_result=None):
            self._show_fullscreen_control(self.tab_vector_editor, True)
            dlg_layout.removeWidget(self.tab_vector_editor)
            self.tab_vector_editor.setParent(None)
            self.main_tabs_view.insertTab(
    idx,
    self.tab_vector_editor,
    tr("tab.vector_editor")
)
            self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
            self.tab_vector_editor.setVisible(True)
            self.vector_canvas.request_recenter()

        dialog.finished.connect(restore)
        dialog.show()
        dialog.setWindowState(Qt.WindowState.WindowMaximized)
        # Recentre la vue sur le contenu une fois la fenêtre maximisée.
        self.vector_canvas.request_recenter()

    def import_svg_to_vector_editor(self):
        """Importe un SVG ou un DXF dans l'éditeur vectoriel.

        Par défaut le dessin arrive **groupé** (un objet, ou un par calque DXF) :
        on le manipule d'un bloc. Pour séparer les tracés, clic droit → Dégrouper.
        """
        if not self.layer_manager.layers:
            QMessageBox.warning(self, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("vector.import_title"),
            "",
            tr("vector.import_filter")
        )
        if not path:
            return
        self._import_vector_file(path)

    def _import_vector_file(self, path):
        """Importe le fichier SVG ou DXF `path` (aussi appelé par le glisser-déposer)."""
        if not self.layer_manager.layers:
            QMessageBox.warning(self, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        default_layer = self.layer_manager.default_svg_layer()
        default_layer_id = default_layer.id
        if path.lower().endswith(".dxf"):
            self._import_dxf_file(path, default_layer)
            return
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
        new_items = [self.vector_canvas.add_object(obj) for obj in objects]
        self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
        # Centre la grille sur le SVG importé (au lieu de laisser
        # l'utilisateur le chercher en faisant défiler la vue).
        self.vector_canvas.request_recenter(new_items)
        QMessageBox.information(
            self,
            tr("vector.svg_success_title"),
            tr("vector.svg_success").format(
                count=len(objects),
                layer=default_layer.name
            )
        )

    def _import_dxf_file(self, path, default_layer):
        """Import d'un DXF (texte ASCII) : tracés regroupés par calque DXF, calque LSP par défaut."""
        try:
            drawing = dxf_import.read_dxf(path)
        except dxf_import.DxfError as e:
            key = f"vector.dxf_err.{e.code}"
            text = tr(key)
            if text == key:
                text = tr("vector.dxf_error").format(error=e)
            else:
                text = text.format(**e.info) if e.info else text
            QMessageBox.critical(self, tr("vector.dxf_title"), text)
            return
        except Exception as e:
            QMessageBox.critical(self, tr("vector.dxf_title"), tr("vector.dxf_error").format(error=e))
            return
        skipped = ", ".join(f"{kind} x{count}" for kind, count in sorted(drawing.skipped.items()))
        objects = dxf_to_objects(drawing, default_layer.id)
        if not objects:
            message = tr("vector.dxf_empty")
            if skipped:
                message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
            QMessageBox.information(self, tr("vector.dxf_title"), message)
            return
        self.vector_canvas.push_undo_snapshot()
        new_items = [self.vector_canvas.add_object(obj) for obj in objects]
        self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
        self.vector_canvas.request_recenter(new_items)
        message = tr("vector.dxf_success").format(
            count=len(objects), layer=default_layer.name, unit=dxf_import.units_label(drawing))
        if skipped:
            message += "\n\n" + tr("vector.dxf_skipped").format(skipped=skipped)
        QMessageBox.information(self, tr("vector.dxf_title"), message)

    def open_nesting(self):
        """Placement automatique : range les pièces sélectionnées (ou toutes) sur la feuille pour
        gaspiller le moins de matière possible. Un trou ou un détail gravé reste avec sa pièce."""
        canvas = self.vector_canvas
        enabled_ids = {layer.id for layer in self.layer_manager.layers if layer.enabled}
        candidates = [o for o in canvas.objects if o.layer_id in enabled_ids]
        selected = [item.obj for item in canvas.scene_obj.selectedItems() if hasattr(item, "obj") and item.obj in candidates]
        if not candidates:
            QMessageBox.information(self, tr("nest.title"), tr("nest.no_objects"))
            return
        dialog = NestingDialog(self, self.spin_machine_w.value(), self.spin_machine_h.value(),
                               len(selected), len(candidates), getattr(self, "_nesting_settings", None))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._nesting_settings = dialog.settings()
        objects = selected if dialog.scope() == "selection" and selected else candidates
        options = dialog.options()
        pieces, members = build_pieces(objects)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = nesting.nest(pieces, options["sheet_w"], options["sheet_h"], spacing=options["spacing"],
                                  margin=options["margin"], angles=options["angles"], cell=options["cell"],
                                  origin=options["origin"])
        finally:
            QApplication.restoreOverrideCursor()
        if not result.placements:
            QMessageBox.warning(self, tr("nest.title"), tr("nest.nothing_placed"))
            return
        canvas.push_undo_snapshot()
        moved = apply_result(canvas, members, result)
        moved_ids = {id(o) for o in moved}
        items = [item for item in canvas.scene_obj.items() if hasattr(item, "obj") and id(item.obj) in moved_ids]
        if items:
            canvas.request_recenter(items)
        message = tr("nest.done").format(
            placed=len(result.placements), sheet_w=options["sheet_w"], sheet_h=options["sheet_h"],
            percent=result.utilization * 100.0, ext_w=result.extent[0], ext_h=result.extent[1])
        if result.unplaced:
            message += "\n\n" + tr("nest.unplaced").format(count=len(result.unplaced))
        QMessageBox.information(self, tr("nest.title"), message)

    def open_box_generator(self):
        """Fenêtre du générateur de boîte à encoches : crée les panneaux (calque de découpe) et le
        décor texte/SVG (calque de gravure) dans l'éditeur vectoriel."""
        if not self.layer_manager.layers:
            QMessageBox.warning(self, tr("vector.no_layer_title"), tr("vector.no_layer_body"))
            return
        dialog = BoxGeneratorDialog(
            self, self.layer_manager.layers, self.spin_machine_w.value(), self.spin_machine_h.value(),
            getattr(self, "_box_settings", None))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._box_settings = dialog.settings()
        try:
            result = box_generator.build_box(dialog.params())
        except box_generator.BoxError as e:
            QMessageBox.warning(self, tr("box.title"), error_message(e))
            return
        offset = 10.0
        panels = box_to_objects(result, dialog.cut_layer_id(), offset, offset)
        by_name = {panel.name: panel for panel, _ in panels}
        decor_objects = []
        bed_h = self.spin_machine_h.value()
        for decor in dialog.decors():
            panel = by_name.get(decor.face)
            if panel is None:
                continue                       # face absente (ex. dessus d'une boîte ouverte)
            try:
                decor_objects += decor_to_objects(decor, panel, dialog.engrave_layer_id(), bed_h, offset, offset)
            except Exception as e:
                QMessageBox.warning(self, tr("box.title"), tr("box.decor_error").format(error=e))
        self.vector_canvas.push_undo_snapshot()
        new_items = [self.vector_canvas.add_object(obj) for _, obj in panels]
        new_items += [self.vector_canvas.add_object(obj) for obj in decor_objects]
        self.main_tabs_view.setCurrentWidget(self.tab_vector_editor)
        self.vector_canvas.request_recenter(new_items)
        message = tr("box.done").format(count=len(panels), decor=len(decor_objects),
                                        w=result.width, h=result.height)
        if result.width > self.spin_machine_w.value() - 2 * offset or result.height > self.spin_machine_h.value() - 2 * offset:
            message += "\n\n" + tr("box.too_big").format(bed_w=self.spin_machine_w.value(), bed_h=self.spin_machine_h.value())
        QMessageBox.information(self, tr("box.title"), message)


    # ------------------------------------------------------------------
    # Alignement / distribution multi-objets
    # ------------------------------------------------------------------
    def align_vector_selection(self, mode):
        """Aligne les objets sélectionnés les uns par rapport aux autres
        (mode: 'left', 'right', 'center_h', 'top', 'bottom', 'middle_v').
        Le repère est la boîte englobante de l'ENSEMBLE de la sélection —
        avec un seul objet sélectionné, ne fait donc rien (rien à aligner
        par rapport à soi-même)."""
        items = self._selected_vector_items()
        if len(items) < 2:
            return

        boxes = [(it, it.obj.world_path().boundingRect()) for it in items]
        group_left = min(b.left() for _, b in boxes)
        group_right = max(b.right() for _, b in boxes)
        # Convention déjà établie ailleurs dans ce fichier (voir
        # on_vector_position_spin_changed) : box.top() correspond au bord
        # BAS de l'objet en mm, box.bottom() à son bord HAUT.
        group_bottom = min(b.top() for _, b in boxes)
        group_top = max(b.bottom() for _, b in boxes)

        self.vector_canvas.push_undo_snapshot()
        for it, b in boxes:
            dx = dy = 0.0
            if mode == "left":
                dx = group_left - b.left()
            elif mode == "right":
                dx = group_right - b.right()
            elif mode == "center_h":
                dx = (group_left + group_right) / 2.0 - (b.left() + b.right()) / 2.0
            elif mode == "bottom":
                dy = group_bottom - b.top()
            elif mode == "top":
                dy = group_top - b.bottom()
            elif mode == "middle_v":
                dy = (group_bottom + group_top) / 2.0 - (b.top() + b.bottom()) / 2.0
            it.obj.x_mm += dx
            it.obj.y_mm += dy
            it.refresh()

        self.on_vector_selection_changed(items[0].obj)

    def distribute_vector_selection(self, axis):
        """Répartit les objets sélectionnés avec un espacement égal entre
        eux (axis: 'h' ou 'v'), en gardant fixes les deux objets aux
        extrémités. Nécessite au moins 3 objets — avec 2, il n'y a qu'un
        seul espacement possible, rien à répartir."""
        items = self._selected_vector_items()
        if len(items) < 3:
            return

        boxes = [(it, it.obj.world_path().boundingRect()) for it in items]
        self.vector_canvas.push_undo_snapshot()

        if axis == "h":
            boxes.sort(key=lambda pair: pair[1].left())
            span = boxes[-1][1].right() - boxes[0][1].left()
            total_size = sum(b.width() for _, b in boxes)
            gap = (span - total_size) / (len(boxes) - 1)
            cursor = boxes[0][1].left()
            for it, b in boxes:
                it.obj.x_mm += cursor - b.left()
                it.refresh()
                cursor += b.width() + gap
        else:  # "v"
            boxes.sort(key=lambda pair: pair[1].top())  # bas -> haut, en mm
            span = boxes[-1][1].bottom() - boxes[0][1].top()
            total_size = sum(b.height() for _, b in boxes)
            gap = (span - total_size) / (len(boxes) - 1)
            cursor = boxes[0][1].top()
            for it, b in boxes:
                it.obj.y_mm += cursor - b.top()
                it.refresh()
                cursor += b.height() + gap

        self.on_vector_selection_changed(items[0].obj)

    def set_vector_snap_enabled(self, enabled):
        self.vector_canvas.snap_enabled = bool(enabled)

    def set_vector_snap_step(self, value):
        self.vector_canvas.snap_step_mm = float(value)
