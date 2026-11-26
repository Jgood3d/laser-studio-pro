"""Tableau des calques (LayerManagerWidget) : vue du modèle LayersModel,
dans l'onglet Calques."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QHeaderView, QColorDialog, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QLineEdit, QMessageBox, QAbstractItemView, QToolButton,
)
from laser_studio.i18n import tr
from laser_studio.models.layer_modes import CONTOUR_MODES
from laser_studio.models.layers import (
    CUT_MODE, ENGRAVE_MODE, LAYER_MODE_TR_KEYS, LAYER_MODES, KERF_WIDTH_MAX_MM, KERF_WIDTH_MIN_MM,
    LEAD_RADIUS_MAX_MM, LEAD_RADIUS_MIN_MM, TAB_COUNT_MAX, TAB_WIDTH_MAX_MM, TAB_WIDTH_MIN_MM, LaserLayer,
    LayersModel, PERF_LENGTH_MAX_MM, PERF_LENGTH_MIN_MM, PERF_MODE, RAMP_POWER_MAX_PCT,
    RAMP_POWER_MIN_PCT,
)


class LayerManagerWidget(QWidget):
    """Table façon LightBurn : Couleur | Nom | Mode | Puissance | Vitesse | Passes | Pas | Surbalayage | Laser | Ponts (case + nombre) | Larg. pont | Kerf | Arc | Perforation | Rampe | Actif

    Vue du modèle des calques (LayersModel) : chaque saisie appelle
    `mgr.update(...)`, et la table se met à jour à partir des signaux du
    modèle, quelle que soit l'origine du changement (saisie, matériau,
    profil machine, projet). `layers_changed` relaie `mgr.changed`."""

    layers_changed = pyqtSignal()

    COLUMN_KEYS = ["layers.col.color", "layers.col.name", "layers.col.mode",
                   "layers.col.power", "layers.col.speed", "layers.col.passes",
                   "layers.col.fill_step", "layers.col.overscan", "layers.col.laser", "layers.col.tab_count",
                   "layers.col.tab_width", "layers.col.kerf", "layers.col.lead",
                   "layers.col.perforation", "layers.col.ramp", "layers.col.active"]

    def __init__(self, layer_manager: LayersModel, parent=None, focal_getter=None):
        super().__init__(parent)
        self.mgr = layer_manager
        # Callable optionnel (ex. lambda: self.machine.focal)
        # renvoyant la taille du spot laser (mm) réglée dans Paramètres
        # Machine — même logique de lien que l'onglet Image & Filtres
        # (mode "Focale laser" pour l'intervalle de lignes du tramage).
        self.focal_getter = focal_getter
        # Éditeurs de chaque ligne, par identifiant de calque : {réglage: widget}.
        self._editors = {}

        self.COLUMNS = [tr(k) for k in self.COLUMN_KEYS]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Ajouter / supprimer / monter / descendre : des actions, affichées par
        # l'onglet Calques dans une barre flottante sur la table (LayersTab).
        self.layer_actions = []
        for key, tip_key, slot in (
            ("layers.add", None, self.on_add),
            ("layers.remove", None, self.on_remove),
            ("layers.move_up", "layers.move_up_tip", lambda: self.on_move(-1)),
            ("layers.move_down", "layers.move_down_tip", lambda: self.on_move(1)),
        ):
            action = QAction(tr(key), self)
            if tip_key:
                action.setToolTip(tr(tip_key))
            action.triggered.connect(lambda _checked=False, s=slot: s())
            self.layer_actions.append(action)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        # Chaque cellule contient un composant (setCellWidget) : sans réglage, les colonnes
        # gardent la largeur par défaut de Qt (100 px), plus étroite que leur contenu (en-têtes
        # coupés, champs qui débordent sur la colonne voisine). Chaque colonne prend donc la
        # largeur de son contenu, en-tête compris ; le nom prend la place restante.
        header = self.table.horizontalHeader()
        for col in range(len(self.COLUMNS)):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.Stretch if col == 1 else QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Abonnement au modèle.
        for signal in (self.mgr.layers_reset, self.mgr.layer_added,
                       self.mgr.layer_removed, self.mgr.layers_reordered):
            signal.connect(self.refresh)
        self.mgr.layer_changed.connect(self._sync_row)
        self.mgr.changed.connect(self.layers_changed)

        self.refresh()

    # -- construction des lignes -------------------------------------------------
    def refresh(self, *_args):
        """Reconstruit toutes les lignes à partir du modèle."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._editors = {}
        for layer in self.mgr.layers:
            self._add_row(layer)
        self.table.blockSignals(False)

    def _add_row(self, layer: LaserLayer):
        row = self.table.rowCount()
        self.table.insertRow(row)
        lid = layer.id
        editors = {}

        # Couleur (bouton pastille)
        btn_color = QToolButton()
        btn_color.setFixedSize(28, 22)
        self._style_color_button(btn_color, layer.color)
        btn_color.clicked.connect(lambda _=False, i=lid: self._pick_color(i))
        self.table.setCellWidget(row, 0, self._centered(btn_color))
        editors["color"] = btn_color

        name_edit = QLineEdit(layer.name)
        if self.mgr.is_base_layer(layer):
            # Calque de base : nom fixe (voir LayersModel.ensure_base_layers).
            name_edit.setReadOnly(True)
            name_edit.setToolTip(tr("layers.base_name_tip"))
        else:
            name_edit.textChanged.connect(lambda t, i=lid: self._set(i, "name", t))
        self.table.setCellWidget(row, 1, name_edit)
        editors["name"] = name_edit

        combo_mode = QComboBox()
        for mode_id in LAYER_MODES:
            combo_mode.addItem(tr(LAYER_MODE_TR_KEYS[mode_id]), mode_id)
        idx_mode = combo_mode.findData(layer.mode)
        if idx_mode >= 0:
            combo_mode.setCurrentIndex(idx_mode)
        combo_mode.currentIndexChanged.connect(
            lambda idx, i=lid, c=combo_mode: self._set(i, "mode", c.itemData(idx))
        )
        self.table.setCellWidget(row, 2, combo_mode)
        editors["mode"] = combo_mode

        spin_power = QDoubleSpinBox(); spin_power.setRange(0, 100); spin_power.setValue(layer.power)
        spin_power.valueChanged.connect(lambda v, i=lid: self._set(i, "power", v))
        self.table.setCellWidget(row, 3, spin_power)
        editors["power"] = spin_power

        spin_speed = QSpinBox(); spin_speed.setRange(1, 20000); spin_speed.setValue(layer.speed)
        spin_speed.valueChanged.connect(lambda v, i=lid: self._set(i, "speed", v))
        self.table.setCellWidget(row, 4, spin_speed)
        editors["speed"] = spin_speed

        spin_passes = QSpinBox(); spin_passes.setRange(1, 50); spin_passes.setValue(layer.passes)
        spin_passes.valueChanged.connect(lambda v, i=lid: self._set(i, "passes", v))
        self.table.setCellWidget(row, 5, spin_passes)
        editors["passes"] = spin_passes

        fill_cell = QWidget()
        fill_layout = QHBoxLayout(fill_cell)
        fill_layout.setContentsMargins(2, 0, 2, 0)
        fill_layout.setSpacing(2)

        spin_fill = QDoubleSpinBox(); spin_fill.setRange(0.02, 5.0); spin_fill.setSingleStep(0.02)
        spin_fill.setDecimals(2); spin_fill.setValue(layer.line_interval)
        spin_fill.valueChanged.connect(lambda v, i=lid: self._set(i, "line_interval", v))
        spin_fill.valueChanged.connect(lambda _v, s=spin_fill: self._update_fill_quality(s))
        fill_layout.addWidget(spin_fill)
        editors["line_interval"] = spin_fill

        btn_focal = QToolButton()
        btn_focal.setCheckable(True)
        btn_focal.setChecked(layer.line_interval_linked)
        btn_focal.setFixedSize(24, 22)
        btn_focal.setEnabled(self.focal_getter is not None)
        self._style_link_button(btn_focal, layer.line_interval_linked)
        btn_focal.toggled.connect(lambda checked, i=lid: self._on_link_toggled(checked, i))
        fill_layout.addWidget(btn_focal)
        spin_fill.setEnabled(not layer.line_interval_linked)
        editors["line_interval_linked"] = btn_focal

        self.table.setCellWidget(row, 6, fill_cell)
        self._update_fill_quality(spin_fill)

        # Surbalayage : propre à la gravure remplie (grisé pour les autres modes), et seulement si l'option
        # est activée dans Configuration GRBL, qui en donne le mode et la distance.
        chk_overscan = QCheckBox(); chk_overscan.setChecked(layer.overscan)
        chk_overscan.setToolTip(tr("layers.overscan_tip"))
        chk_overscan.setEnabled(layer.mode == ENGRAVE_MODE)
        chk_overscan.stateChanged.connect(lambda v, i=lid: self._set(i, "overscan", bool(v)))
        self.table.setCellWidget(row, 7, self._centered(chk_overscan))
        editors["overscan"] = chk_overscan

        # Commande laser du calque : celle de Configuration GRBL, ou M4 / M3 pour ce calque seulement.
        combo_laser = QComboBox()
        for cmd, key in (("", "layers.laser_auto"), ("M4", "layers.laser_m4"), ("M3", "layers.laser_m3")):
            combo_laser.addItem(tr(key), cmd)
        combo_laser.setCurrentIndex(max(0, combo_laser.findData(layer.laser_cmd)))
        combo_laser.setToolTip(tr("layers.laser_tip"))
        combo_laser.currentIndexChanged.connect(
            lambda idx, i=lid, c=combo_laser: self._set(i, "laser_cmd", c.itemData(idx))
        )
        self.table.setCellWidget(row, 8, combo_laser)
        editors["laser_cmd"] = combo_laser

        # Ponts de maintien : propres à la découpe (grisés pour les autres modes) ; la largeur ne sert que si
        # le calque a au moins un pont.
        tabs_cell = QWidget()
        tabs_layout = QHBoxLayout(tabs_cell)
        tabs_layout.setContentsMargins(2, 0, 2, 0)
        tabs_layout.setSpacing(4)
        chk_tabs = QCheckBox(); chk_tabs.setChecked(layer.tabs)
        chk_tabs.setToolTip(tr("layers.tabs_tip"))
        chk_tabs.setEnabled(layer.mode == CUT_MODE)
        chk_tabs.stateChanged.connect(lambda v, i=lid: self._set(i, "tabs", bool(v)))
        tabs_layout.addWidget(chk_tabs)
        spin_tabs = QSpinBox(); spin_tabs.setRange(1, TAB_COUNT_MAX); spin_tabs.setValue(max(1, layer.tab_count))
        spin_tabs.setToolTip(tr("layers.tab_count_tip"))
        spin_tabs.setEnabled(layer.mode == CUT_MODE and layer.tabs)
        spin_tabs.valueChanged.connect(lambda v, i=lid: self._set(i, "tab_count", v))
        tabs_layout.addWidget(spin_tabs)
        self.table.setCellWidget(row, 9, tabs_cell)
        editors["tabs"] = chk_tabs
        editors["tab_count"] = spin_tabs

        spin_tab_width = QDoubleSpinBox()
        spin_tab_width.setRange(TAB_WIDTH_MIN_MM, TAB_WIDTH_MAX_MM); spin_tab_width.setSingleStep(0.1)
        spin_tab_width.setDecimals(1); spin_tab_width.setValue(layer.tab_width)
        spin_tab_width.setToolTip(tr("layers.tab_width_tip"))
        spin_tab_width.setEnabled(layer.mode == CUT_MODE and layer.tabs)
        spin_tab_width.valueChanged.connect(lambda v, i=lid: self._set(i, "tab_width", v))
        self.table.setCellWidget(row, 10, spin_tab_width)
        editors["tab_width"] = spin_tab_width

        # Compensation du kerf : case + largeur de la saignée, propres à la découpe.
        kerf_cell = QWidget()
        kerf_layout = QHBoxLayout(kerf_cell)
        kerf_layout.setContentsMargins(2, 0, 2, 0)
        kerf_layout.setSpacing(4)
        chk_kerf = QCheckBox(); chk_kerf.setChecked(layer.kerf)
        chk_kerf.setToolTip(tr("layers.kerf_tip"))
        chk_kerf.setEnabled(layer.mode == CUT_MODE)
        chk_kerf.stateChanged.connect(lambda v, i=lid: self._set(i, "kerf", bool(v)))
        kerf_layout.addWidget(chk_kerf)
        spin_kerf = QDoubleSpinBox()
        spin_kerf.setRange(KERF_WIDTH_MIN_MM, KERF_WIDTH_MAX_MM); spin_kerf.setSingleStep(0.01)
        spin_kerf.setDecimals(2); spin_kerf.setValue(layer.kerf_width)
        spin_kerf.setToolTip(tr("layers.kerf_tip"))
        spin_kerf.setEnabled(layer.mode == CUT_MODE and layer.kerf)
        spin_kerf.valueChanged.connect(lambda v, i=lid: self._set(i, "kerf_width", v))
        kerf_layout.addWidget(spin_kerf)
        self.table.setCellWidget(row, 11, kerf_cell)
        editors["kerf"] = chk_kerf
        editors["kerf_width"] = spin_kerf

        # Arcs d'entrée et de sortie : case + rayon, propres à la découpe.
        lead_cell = QWidget()
        lead_layout = QHBoxLayout(lead_cell)
        lead_layout.setContentsMargins(2, 0, 2, 0)
        lead_layout.setSpacing(4)
        chk_lead = QCheckBox(); chk_lead.setChecked(layer.lead)
        chk_lead.setToolTip(tr("layers.lead_tip"))
        chk_lead.setEnabled(layer.mode == CUT_MODE)
        chk_lead.stateChanged.connect(lambda v, i=lid: self._set(i, "lead", bool(v)))
        lead_layout.addWidget(chk_lead)
        spin_lead = QDoubleSpinBox()
        spin_lead.setRange(LEAD_RADIUS_MIN_MM, LEAD_RADIUS_MAX_MM); spin_lead.setSingleStep(0.1)
        spin_lead.setDecimals(1); spin_lead.setValue(layer.lead_radius)
        spin_lead.setToolTip(tr("layers.lead_tip"))
        spin_lead.setEnabled(layer.mode == CUT_MODE and layer.lead)
        spin_lead.valueChanged.connect(lambda v, i=lid: self._set(i, "lead_radius", v))
        lead_layout.addWidget(spin_lead)
        self.table.setCellWidget(row, 12, lead_cell)
        editors["lead"] = chk_lead
        editors["lead_radius"] = spin_lead

        # Perforation (mode Perforation seulement) : longueur d'un trait | longueur d'un vide, en mm.
        perf_cell = QWidget()
        perf_layout = QHBoxLayout(perf_cell)
        perf_layout.setContentsMargins(2, 0, 2, 0)
        perf_layout.setSpacing(4)
        for field, editor_key in (("perf_dash", "perf_dash"), ("perf_gap", "perf_gap")):
            spin_perf = QDoubleSpinBox()
            spin_perf.setRange(PERF_LENGTH_MIN_MM, PERF_LENGTH_MAX_MM); spin_perf.setSingleStep(0.1)
            spin_perf.setDecimals(1); spin_perf.setValue(getattr(layer, field))
            spin_perf.setToolTip(tr("layers.perf_tip"))
            spin_perf.setEnabled(layer.mode == PERF_MODE)
            spin_perf.valueChanged.connect(lambda v, i=lid, f=field: self._set(i, f, v))
            perf_layout.addWidget(spin_perf)
            editors[editor_key] = spin_perf
        self.table.setCellWidget(row, 13, perf_cell)

        # Rampe de puissance : case + puissance de la dernière passe (%), pour les modes de contour.
        ramp_cell = QWidget()
        ramp_layout = QHBoxLayout(ramp_cell)
        ramp_layout.setContentsMargins(2, 0, 2, 0)
        ramp_layout.setSpacing(4)
        chk_ramp = QCheckBox(); chk_ramp.setChecked(layer.ramp)
        chk_ramp.setToolTip(tr("layers.ramp_tip"))
        chk_ramp.setEnabled(layer.mode in CONTOUR_MODES)
        chk_ramp.stateChanged.connect(lambda v, i=lid: self._set(i, "ramp", bool(v)))
        ramp_layout.addWidget(chk_ramp)
        spin_ramp = QDoubleSpinBox()
        spin_ramp.setRange(RAMP_POWER_MIN_PCT, RAMP_POWER_MAX_PCT); spin_ramp.setSingleStep(5.0)
        spin_ramp.setDecimals(0); spin_ramp.setValue(layer.ramp_power)
        spin_ramp.setToolTip(tr("layers.ramp_tip"))
        spin_ramp.setEnabled(layer.mode in CONTOUR_MODES and layer.ramp)
        spin_ramp.valueChanged.connect(lambda v, i=lid: self._set(i, "ramp_power", v))
        ramp_layout.addWidget(spin_ramp)
        self.table.setCellWidget(row, 14, ramp_cell)
        editors["ramp"] = chk_ramp
        editors["ramp_power"] = spin_ramp

        chk_enabled = QCheckBox(); chk_enabled.setChecked(layer.enabled)
        chk_enabled.stateChanged.connect(lambda v, i=lid: self._set(i, "enabled", bool(v)))
        self.table.setCellWidget(row, 15, self._centered(chk_enabled))
        editors["enabled"] = chk_enabled

        self._editors[lid] = editors
        self.table.setRowHeight(row, 30)
        self.table.setProperty(f"row_layer_{row}", lid)

    @staticmethod
    def _centered(widget):
        """Cellule qui centre `widget` (pastille de couleur, case « Actif »)."""
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignCenter)
        return cell

    @staticmethod
    def _style_color_button(button, color):
        button.setStyleSheet(f"background-color:{color}; border:1px solid #222;")

    # -- modèle -> vue -----------------------------------------------------------
    def _sync_row(self, layer_id, changes):
        """Un calque a changé dans le modèle : met à jour sa ligne, sans
        réémettre de saisie (signaux bloqués) et sans toucher à un champ qui
        affiche déjà la bonne valeur (une saisie en cours n'est pas perturbée)."""
        editors = self._editors.get(layer_id)
        layer = self.mgr.get(layer_id)
        if editors is None or layer is None:
            return
        for key in changes:
            widget = editors.get(key)
            if widget is None:
                continue
            value = getattr(layer, key)
            widget.blockSignals(True)
            try:
                if key == "color":
                    self._style_color_button(widget, value)
                elif key == "name":
                    if widget.text() != value:
                        widget.setText(value)
                elif key in ("mode", "laser_cmd"):
                    idx = widget.findData(value)
                    if idx >= 0 and idx != widget.currentIndex():
                        widget.setCurrentIndex(idx)
                elif key in ("line_interval_linked", "enabled", "overscan", "tabs", "kerf", "lead", "ramp"):
                    if widget.isChecked() != value:
                        widget.setChecked(value)
                elif widget.value() != value:
                    widget.setValue(value)
            finally:
                widget.blockSignals(False)
            if key == "mode" and "overscan" in editors:
                editors["overscan"].setEnabled(value == ENGRAVE_MODE)
            if key in ("mode", "tabs") and "tabs" in editors:
                is_cut = layer.mode == CUT_MODE
                editors["tabs"].setEnabled(is_cut)
                editors["tab_count"].setEnabled(is_cut and layer.tabs)
                editors["tab_width"].setEnabled(is_cut and layer.tabs)
            if key in ("mode", "kerf") and "kerf" in editors:
                is_cut = layer.mode == CUT_MODE
                editors["kerf"].setEnabled(is_cut)
                editors["kerf_width"].setEnabled(is_cut and layer.kerf)
            if key in ("mode", "lead") and "lead" in editors:
                is_cut = layer.mode == CUT_MODE
                editors["lead"].setEnabled(is_cut)
                editors["lead_radius"].setEnabled(is_cut and layer.lead)
            if key == "mode" and "perf_dash" in editors:
                editors["perf_dash"].setEnabled(layer.mode == PERF_MODE)
                editors["perf_gap"].setEnabled(layer.mode == PERF_MODE)
            if key in ("mode", "ramp") and "ramp" in editors:
                in_contour = layer.mode in CONTOUR_MODES
                editors["ramp"].setEnabled(in_contour)
                editors["ramp_power"].setEnabled(in_contour and layer.ramp)
            if key == "line_interval_linked":
                self._style_link_button(widget, value)
                editors["line_interval"].setEnabled(not value)
            if key == "line_interval":
                self._update_fill_quality(editors["line_interval"])

    # -- vue -> modèle -----------------------------------------------------------
    def _set(self, layer_id, attr, value):
        self.mgr.update(layer_id, **{attr: value})

    def _pick_color(self, layer_id):
        layer = self.mgr.get(layer_id)
        if layer is None:
            return
        color = QColorDialog.getColor(QColor(layer.color), self, tr("layers.color_dialog_title"))
        if color.isValid():
            self.mgr.update(layer_id, color=color.name())

    def _focal_interval(self, spin_fill=None):
        """Taille du spot laser (mm), ramenée dans les bornes du champ du pas
        de remplissage ; None si elle n'est pas connue."""
        if self.focal_getter is None:
            return None
        focal = self.focal_getter()
        if not focal or focal <= 0:
            return None
        if spin_fill is None:
            return focal
        return max(spin_fill.minimum(), min(spin_fill.maximum(), focal))

    def _style_link_button(self, button, linked):
        if linked:
            button.setText("🔗")
            button.setToolTip(tr("layers.link_tip_linked"))
            button.setStyleSheet("background-color:#2f6f4f;")
        else:
            button.setText("🎯")
            button.setToolTip(tr("layers.link_tip_unlinked"))
            button.setStyleSheet("")

    def _on_link_toggled(self, checked, layer_id):
        fields = {"line_interval_linked": checked}
        if checked:
            spin_fill = self._editors.get(layer_id, {}).get("line_interval")
            interval = self._focal_interval(spin_fill)
            if interval is not None:
                fields["line_interval"] = interval
        self.mgr.update(layer_id, **fields)

    def _update_fill_quality(self, spin_fill):
        """Colore la bordure du champ selon l'adéquation du pas choisi avec
        la taille du spot laser — mêmes seuils que la pastille de qualité de
        l'onglet Image & Filtres (ratio pas/focale)."""
        focal = self._focal_interval()
        if focal is None:
            spin_fill.setStyleSheet("")
            return
        ratio = spin_fill.value() / focal
        if ratio < 0.6:
            color = "#e05656"      # trop fin
        elif ratio < 0.9:
            color = "#e0a656"      # fin
        elif ratio <= 2.25:
            color = "#56c271"      # correct / recommandé
        else:
            color = "#999999"      # grossier mais correct
        spin_fill.setStyleSheet(f"border: 1px solid {color};")

    def refresh_focal_quality(self):
        """À appeler quand la taille du spot change dans Paramètres Machine.
        Les calques 'liés' voient leur pas remplissage recalculé
        automatiquement ; les autres n'ont que leur pastille de qualité
        rafraîchie."""
        for layer_id, editors in list(self._editors.items()):
            layer = self.mgr.get(layer_id)
            spin_fill = editors["line_interval"]
            interval = self._focal_interval(spin_fill)
            if layer is not None and layer.line_interval_linked and interval is not None:
                self.mgr.update(layer_id, line_interval=interval)
            self._update_fill_quality(spin_fill)

    def link_all_to_focal(self):
        """Lie tous les calques à la taille du spot en une fois ET applique
        immédiatement la valeur de la focale à chacun — appelé
        automatiquement au démarrage et à la validation des Paramètres
        Machine, pour éviter d'avoir à cocher le 🔗 sur chaque calque un par
        un.

        Les calques de contour (Découpe, Marquage) ne sont pas liés : ils
        gardent leur propre pas (ex. 0,06 mm pour le calque Marquage)."""
        if self.focal_getter is None:
            return
        focal = self._focal_interval()
        for layer in list(self.mgr.layers):
            if layer.mode in CONTOUR_MODES:
                self.mgr.update(layer.id, line_interval_linked=False)
                continue
            fields = {"line_interval_linked": True}
            if focal is not None:
                fields["line_interval"] = focal
            self.mgr.update(layer.id, **fields)

    def on_add(self):
        linked = self.focal_getter is not None
        default_interval = self.focal_getter() if linked else None
        self.mgr.add_layer(line_interval=default_interval, line_interval_linked=linked)

    def on_remove(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.mgr.layers):
            return
        layer = self.mgr.layers[row]
        if self.mgr.is_base_layer(layer):
            QMessageBox.information(self, tr("layers.base_title"), tr("layers.base_cannot_delete")
                                    .format(name=layer.name))
            return
        self.mgr.remove_layer(layer.id)

    def on_move(self, delta):
        """Monte (-1) ou descend (+1) le calque sélectionné, puis garde la
        ligne déplacée sélectionnée pour pouvoir enchaîner les clics."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.mgr.layers):
            return
        new_row = self.mgr.move_layer(self.mgr.layers[row].id, delta)
        if new_row is None:
            return
        self.table.setCurrentCell(new_row, 1)
        self.table.selectRow(new_row)

    def current_layer_id(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.mgr.layers):
            return self.mgr.layers[row].id
        return self.mgr.layers[0].id if self.mgr.layers else None
