"""Catalogue des machines : liste par marque (avec recherche) et fiche du modèle choisi (surface, point,
vitesse, laser, notes, sources). « Créer le profil » ferme la fenêtre ; chosen() donne le modèle."""
import html

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr


def _number(value):
    return f"{value:g}"


class MachineCatalogDialog(QDialog):
    """`models` : liste de library.machine_catalog.MachineModel."""

    def __init__(self, models, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("catalog.title"))
        self.setModal(False)                       # non modale : GNOME accrocherait une fenêtre modale
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(900, 560)
        self._models = list(models)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("catalog.search"))
        self.search.textChanged.connect(self._fill)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._show)
        self.tree.itemDoubleClicked.connect(lambda item, _col: self.accept() if self._model_of(item) else None)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setOpenExternalLinks(True)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.tree, 1)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 600])
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("catalog.create"))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("common.cancel"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        intro = QLabel(tr("catalog.intro"))
        intro.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(splitter, 1)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.buttons)
        layout.addLayout(row)
        self._fill()

    def _model_of(self, item):
        return item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None

    def _fill(self, *_args):
        query = self.search.text().strip().casefold()
        self.tree.clear()
        brands = {}
        first = None
        for model in self._models:
            if query and query not in model.title.casefold():
                continue
            brand = brands.get(model.brand)
            if brand is None:
                brand = brands[model.brand] = QTreeWidgetItem(self.tree, [model.brand])
                brand.setFlags(brand.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item = QTreeWidgetItem(brand, [model.model])
            item.setData(0, Qt.ItemDataRole.UserRole, model)
            first = first or item
        self.tree.expandAll()
        if first is not None:
            self.tree.setCurrentItem(first)
        else:
            self._show(None)

    def chosen(self):
        """Modèle choisi (MachineModel), ou None."""
        return self._model_of(self.tree.currentItem())

    def _show(self, item, _previous=None):
        model = self._model_of(item)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(model is not None)
        if model is None:
            self.details.setText(f"<i>{html.escape(tr('catalog.none'))}</i>")
            return
        unknown = f"<i>{html.escape(tr('catalog.unpublished'))}</i>"
        rows = [(tr("catalog.area"), f"{_number(model.work_area_mm[0])} × {_number(model.work_area_mm[1])} mm")]
        rows.append((tr("catalog.spot"), f"{_number(model.spot_mm[0])} × {_number(model.spot_mm[1])} mm"
                     if model.spot_mm else unknown))
        speeds = model.max_speed_mm_min or {}
        if speeds:
            text = " / ".join(f"{axis.upper()} {_number(v)}" for axis, v in sorted(speeds.items())) + " mm/min"
        else:
            text = unknown
        rows.append((tr("catalog.speed"), text))
        laser = " · ".join(part for part in (f"{_number(model.power_w)} W" if model.power_w else "",
                                             f"{_number(model.wavelength_nm)} nm" if model.wavelength_nm else "")
                           if part)
        rows.append((tr("catalog.laser"), laser or unknown))
        table = "".join(f"<tr><td style='padding-right:12px'><b>{html.escape(k)}</b></td><td>{v}</td></tr>"
                        for k, v in rows)
        sources = "".join(f"<li><a href='{html.escape(url, quote=True)}'>{html.escape(url[:90])}</a></li>"
                          for url in model.sources)
        notes = f"<p>{html.escape(model.notes)}</p>" if model.notes else ""
        checked = f"<p><i>{html.escape(tr('catalog.checked').format(date=model.checked))}</i></p>" if model.checked else ""
        self.details.setText(
            f"<h3>{html.escape(model.title)}</h3><table>{table}</table>{notes}"
            f"<p>{html.escape(tr('catalog.after'))}</p>"
            f"<p><b>{html.escape(tr('catalog.sources'))}</b></p><ul>{sources}</ul>{checked}")
