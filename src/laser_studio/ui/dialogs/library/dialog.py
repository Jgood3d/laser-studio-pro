"""Fenêtre « Bibliothèque » : les modèles prêts à graver ou découper, filtrés
par catégorie et par recherche, en grille dont on règle la taille."""
from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListView, QListWidget, QListWidgetItem, QSlider, QSplitter, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.dialogs.library.thumbnails import item_image, photo_image, render_svg
from laser_studio.ui.widgets import ZoomableGraphicsView
from laser_studio.vector.svg_import import (
    SvgImportError, document_size_mm, find_texts, find_variant_groups, svg_preview,
)

ICON_SIZE_MIN = 80
ICON_SIZE_MAX = 360
ICON_SIZE_DEFAULT = 160
ALL_CATEGORIES = "*"


class LibraryDialog(QDialog):
    """Grille des modèles (LibraryItem) des catégories `categories`.

    - Catégories à gauche (« Toutes » en tête), recherche en haut.
    - Curseur « Taille des aperçus » : les vignettes grandissent et le nombre
      de colonnes suit la largeur de la fenêtre (icon_size_changed(px)).
    - Double-clic ou « Détails » : fiche du modèle (LibraryItemDialog).
    - « Importer » (ici ou dans la fiche) : la fenêtre se ferme acceptée, le
      choix est dans chosen() -> (modèle, {groupe de variantes: option},
      {texte: nouveau contenu}).

        dialog = LibraryDialog(self, load_catalog(library_roots()), icon_size=200)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item, variants, texts = dialog.chosen()
    """

    icon_size_changed = pyqtSignal(int)

    def __init__(self, parent, categories, icon_size=ICON_SIZE_DEFAULT):
        super().__init__(parent)
        self.setWindowTitle(tr("library.title"))
        self.resize(1100, 720)
        self._categories = categories
        self._items = {item.key: item for c in categories for item in c.items}
        self._icons = {}
        self._chosen = None
        self._details_open = False

        layout = QVBoxLayout(self)
        layout.addLayout(self._header(icon_size))
        splitter = QSplitter()
        splitter.addWidget(self._category_list())
        splitter.addWidget(self._grid(icon_size))
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 880])
        layout.addWidget(splitter, 1)
        self.count_label = QLabel()
        buttons = QDialogButtonBox()
        self.details_button = buttons.addButton(tr("library.details"), QDialogButtonBox.ButtonRole.ActionRole)
        self.import_button = buttons.addButton(tr("library.import"), QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(tr("library.close"), QDialogButtonBox.ButtonRole.RejectRole)
        self.details_button.clicked.connect(self.show_details)
        self.import_button.clicked.connect(lambda: self._import(self.current_item(), None, None))
        buttons.rejected.connect(self.reject)
        bottom = QHBoxLayout()
        bottom.addWidget(self.count_label, 1)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)
        self.refresh()

    # -- construction

    def _header(self, icon_size):
        row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("library.search"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.refresh)
        row.addWidget(self.search_edit, 1)
        row.addSpacing(16)
        row.addWidget(QLabel(tr("library.icon_size")))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(ICON_SIZE_MIN, ICON_SIZE_MAX)
        self.size_slider.setSingleStep(10)
        self.size_slider.setPageStep(40)
        self.size_slider.setValue(max(ICON_SIZE_MIN, min(ICON_SIZE_MAX, icon_size)))
        self.size_slider.setFixedWidth(200)
        self.size_slider.valueChanged.connect(self._apply_icon_size)
        self.size_slider.valueChanged.connect(self.icon_size_changed)
        row.addWidget(self.size_slider)
        return row

    def _category_list(self):
        self.category_list = QListWidget()
        total = sum(len(c.items) for c in self._categories)
        entry = QListWidgetItem(f"{tr('library.all')} ({total})")
        entry.setData(Qt.ItemDataRole.UserRole, ALL_CATEGORIES)
        self.category_list.addItem(entry)
        for category in self._categories:
            entry = QListWidgetItem(f"{category.title} ({len(category.items)})")
            entry.setData(Qt.ItemDataRole.UserRole, category.key)
            self.category_list.addItem(entry)
        self.category_list.setCurrentRow(0)
        self.category_list.currentRowChanged.connect(self.refresh)
        return self.category_list

    def _grid(self, icon_size):
        self.grid = QListWidget()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        # Colonnes recalculées à chaque redimensionnement de la fenêtre.
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setWrapping(True)
        self.grid.setWordWrap(True)
        self.grid.setSpacing(6)
        # Double-clic ou Entrée. Pas aussi itemDoubleClicked : un double-clic émet les deux
        # signaux, et la fiche s'ouvrait deux fois de suite (la seconde, vierge, après l'import).
        self.grid.itemActivated.connect(lambda _item: self.show_details())
        self.grid.currentItemChanged.connect(lambda *_a: self._update_buttons())
        self._apply_icon_size(icon_size)
        return self.grid

    def _cell_size(self, size):
        """Case d'un modèle : la vignette et deux lignes de titre."""
        return QSize(size + 24, size + 48)

    def _apply_icon_size(self, size):
        self.grid.setIconSize(QSize(size, size))
        self.grid.setGridSize(self._cell_size(size))
        # Chaque case prend la taille de la vignette (sinon la largeur du titre
        # peut l'emporter et écraser l'image).
        for row in range(self.grid.count()):
            self.grid.item(row).setSizeHint(self._cell_size(size))

    # -- état

    def icon_size(self):
        return self.size_slider.value()

    def current_category(self):
        entry = self.category_list.currentItem()
        return entry.data(Qt.ItemDataRole.UserRole) if entry else ALL_CATEGORIES

    def visible_items(self):
        """Modèles affichés : catégorie choisie et recherche."""
        category = self.current_category()
        text = self.search_edit.text().strip()
        return [item for c in self._categories for item in c.items
                if category in (ALL_CATEGORIES, c.key) and (not text or item.matches(text))]

    def current_item(self):
        entry = self.grid.currentItem()
        return self._items.get(entry.data(Qt.ItemDataRole.UserRole)) if entry else None

    def chosen(self):
        """(modèle, variantes, textes remplacés) choisis par « Importer », ou None."""
        return self._chosen

    def _icon(self, item):
        icon = self._icons.get(item.key)
        if icon is None:
            pixmap = QPixmap.fromImage(item_image(item))
            icon = QIcon(pixmap)
            # Même image une fois sélectionnée (sinon Qt la teinte de la couleur de sélection).
            icon.addPixmap(pixmap, QIcon.Mode.Selected)
            self._icons[item.key] = icon
        return icon

    def refresh(self, *_args):
        """Remplit la grille d'après la catégorie et la recherche."""
        current = self.current_item()
        self.grid.clear()
        items = self.visible_items()
        for item in items:
            entry = QListWidgetItem(self._icon(item), item.title)
            entry.setData(Qt.ItemDataRole.UserRole, item.key)
            entry.setToolTip(item.description or item.title)
            entry.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            entry.setSizeHint(self._cell_size(self.icon_size()))
            self.grid.addItem(entry)
            if current is not None and item.key == current.key:
                self.grid.setCurrentItem(entry)
        if self.grid.currentItem() is None and self.grid.count():
            self.grid.setCurrentRow(0)
        self.count_label.setText(tr("library.count").format(count=len(items)))
        self._update_buttons()

    def _update_buttons(self):
        selected = self.current_item() is not None
        self.details_button.setEnabled(selected)
        self.import_button.setEnabled(selected)

    # -- actions

    def show_details(self):
        item = self.current_item()
        # Une seule fiche à la fois, et plus aucune une fois le modèle choisi.
        if item is None or self._details_open or self._chosen is not None:
            return
        details = LibraryItemDialog(self, item, self._icon(item))
        self._details_open = True
        try:
            accepted = details.exec() == QDialog.DialogCode.Accepted
        finally:
            self._details_open = False
        if accepted:
            self._import(item, details.variants(), details.texts())

    def _import(self, item, variants, texts):
        if item is None:
            return
        if variants is None:
            try:
                variants = {g.key: g.default for g in find_variant_groups(item.svg_path)}
            except SvgImportError:
                variants = {}
        self._chosen = (item, variants, texts or {})
        self.accept()


class LibraryItemDialog(QDialog):
    """Fiche d'un modèle : aperçu de la pièce en grand (zoom à la molette),
    dessin du SVG et photo éventuelle, avec la variante choisie, informations, texte d'accompagnement (readme),
    choix des variantes, textes à remplacer (nom de la régate...).
    « Importer » ferme la fiche acceptée : variants(), texts()."""

    def __init__(self, parent, item, icon=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(item.title)
        self.resize(1000, 720)
        try:
            self._groups = find_variant_groups(item.svg_path)
        except SvgImportError:
            self._groups = []
        self._combos = {}
        self._text_edits = {}
        self._typed = {}           # textes saisis, gardés quand la variante change

        splitter = QSplitter()
        # Aperçu de la pièce (calculé, suit les options et les textes), fichier SVG, et photo
        # fournie avec le modèle s'il y en a une.
        self.views = QTabWidget()
        self.preview_view = ZoomableGraphicsView()
        self.views.addTab(self.preview_view, tr("library.preview_tab"))
        self.drawing_view = ZoomableGraphicsView()
        self.views.addTab(self.drawing_view, tr("library.drawing_tab"))
        self.photo_view = None
        photo = photo_image(item)
        if not photo.isNull():
            self.photo_view = ZoomableGraphicsView()
            self.photo_view.set_image(photo)
            self.views.addTab(self.photo_view, tr("library.photo_tab"))
        # Recalcul des aperçus peu après la dernière frappe (l'import complet prend un instant).
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(250)
        self._refresh_timer.timeout.connect(self.refresh_drawing)
        splitter.addWidget(self.views)
        splitter.addWidget(self._side_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        buttons = QDialogButtonBox()
        import_button = buttons.addButton(tr("library.import_to_vector"), QDialogButtonBox.ButtonRole.AcceptRole)
        import_button.setDefault(True)
        buttons.addButton(tr("library.close"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addWidget(buttons)

        self.refresh_drawing()

    def _side_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        title = QLabel(self.item.title)
        font = QFont(title.font())
        font.setPointSizeF(font.pointSizeF() * 1.5)
        font.setBold(True)
        title.setFont(font)
        title.setWordWrap(True)
        layout.addWidget(title)
        if self.item.description:
            description = QLabel(self.item.description)
            description.setWordWrap(True)
            layout.addWidget(description)
        form = QFormLayout()
        try:
            size = document_size_mm(self.item.svg_path)
        except SvgImportError:
            size = None
        if size:
            form.addRow(tr("library.size"), QLabel(tr("library.size_value").format(w=size[0], h=size[1])))
        if self.item.author:
            form.addRow(tr("library.author"), QLabel(self.item.author))
        if self.item.license:
            license_label = QLabel(self.item.license)
            license_label.setWordWrap(True)
            form.addRow(tr("library.license"), license_label)
        for group in self._groups:
            combo = QComboBox()
            for key, name in group.options:
                combo.addItem(name, key)
            combo.setCurrentIndex(max(0, combo.findData(group.default)))
            combo.currentIndexChanged.connect(self._variant_changed)
            self._combos[group.key] = combo
            form.addRow(f"{group.label} :", combo)
        layout.addLayout(form)
        # Textes du modèle, remplaçables avant l'import (reconstruits si la variante change).
        self.texts_box = QGroupBox(tr("library.texts"))
        self._texts_form = QFormLayout(self.texts_box)
        layout.addWidget(self.texts_box)
        self._fill_texts()
        if self.item.readme:
            readme = QTextBrowser()
            readme.setPlainText(self.item.readme)
            readme.setFont(QFont("monospace"))
            readme.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
            layout.addWidget(readme, 1)
        else:
            layout.addStretch(1)
        return panel

    def showEvent(self, event):
        """Aperçus affichés en entier à l'ouverture (la taille des vues
        n'est connue qu'une fois la fiche affichée)."""
        super().showEvent(event)
        QTimer.singleShot(0, self.fit_views)

    def fit_views(self):
        for view in (self.preview_view, self.drawing_view, self.photo_view):
            if view is not None:
                view.fitInView(view.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def variants(self):
        """{groupe de variantes: option choisie}."""
        return {key: combo.currentData() for key, combo in self._combos.items()}

    def texts(self):
        """{texte: nouveau contenu}, pour les textes modifiés seulement."""
        return {key: edit.text() for key, edit in self._text_edits.items()
                if edit.text() != edit.property("original")}

    def _fill_texts(self):
        while self._texts_form.rowCount():
            self._texts_form.removeRow(0)
        self._text_edits = {}
        try:
            fields = find_texts(self.item.svg_path, self.variants())
        except SvgImportError:
            fields = []
        for field in fields:
            edit = QLineEdit(self._typed.get(field.key, field.text))
            edit.setProperty("original", field.text)
            edit.textEdited.connect(lambda text, key=field.key: self._typed.__setitem__(key, text))
            edit.textChanged.connect(lambda _text: self._refresh_timer.start())
            self._text_edits[field.key] = edit
            self._texts_form.addRow(f"{field.label} :", edit)
        self.texts_box.setVisible(bool(fields))

    def _variant_changed(self, *_args):
        self._fill_texts()
        self.refresh_drawing()

    def refresh_drawing(self, *_args):
        """Aperçu de la pièce et dessin du SVG, avec les options choisies et
        les textes saisis."""
        preview = item_image(self.item, 1600, self.variants(), self.texts())
        if not preview.isNull():
            self.preview_view.set_image(preview)
        try:
            data = svg_preview(self.item.svg_path, self.variants(), self.texts())
        except SvgImportError:
            return
        except Exception:
            data = None
        image = render_svg(data if data is not None else self.item.svg_path, 1600)
        if not image.isNull():
            self.drawing_view.set_image(image)
