"""Onglet « Graver une image », disposé comme « Graver une image vectorielle » : le gros bouton « Charger Image »
en haut, les aperçus original et tramé, puis à droite la barre d'édition et les propriétés de l'image (affichées
une fois l'image chargée)."""

from PyQt6.QtCore import QPointF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QImage, QPen, QPolygonF
from PIL import ImageOps
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.image.dithering import tone_preview
from laser_studio.ui.tabs.image.settings_panel import ImageSettingsPanel
from laser_studio.ui.utils import import_button, painted_icon, palette_icon, zoom_shortcuts
from laser_studio.ui.widgets import FloatingToolBar, ZoomableGraphicsView
from laser_studio.ui.widgets.start_hint import StartHint


class ImageTab(QWidget):
    """« Charger Image » en haut (émet load_requested), aperçus original et tramé, puis à droite la barre
    d'édition `edit_toolbar` (verticale, remplie par la fenêtre : recadrer, pivoter, miroirs, annuler, loupes)
    et les propriétés de l'image, masquées tant qu'aucune image n'est chargée.

    Les réglages sont dans `settings` (ImageSettingsPanel), qui émet ses
    propres signaux. La barre flottante à gauche des aperçus (`view_toolbar`)
    émet compare_requested (comparaison des algorithmes de tramage) et porte
    « Afficher l'originale » (`show_original_action`, cochable) : l'image
    originale, masquée par défaut, s'affiche à côté du rendu tramé, de même
    largeur. La case `preview_tones_check`, au-dessus de l'originale, lui applique
    luminosité, contraste, gamma et netteté en direct, et `preview_invert_check` l'affiche
    en négatif (aperçus seulement, sans effet sur la gravure).

        tab = ImageTab()
        tab.settings.processing_changed.connect(image.schedule_processing)
        image.source_changed.connect(tab.show_source)
        image.processed.connect(tab.show_processed)

    """

    load_requested = pyqtSignal()
    compare_requested = pyqtSignal()
    crop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = ImageSettingsPanel()
        self._source_image = None            # originale (PIL), pour l'aperçu avec réglages
        self._tones_timer = QTimer(self)
        self._tones_timer.setSingleShot(True)
        self._tones_timer.setInterval(80)
        self._tones_timer.timeout.connect(self._show_source_image)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        top = QHBoxLayout()
        self.load_button = import_button(tr("img.load"), self._picture_icon())
        self.load_button.clicked.connect(lambda: self.load_requested.emit())
        top.addWidget(self.load_button)
        top.addStretch()
        layout.addLayout(top)
        row = QHBoxLayout()
        row.addWidget(self._previews(), 1)
        # Aucune image : carte d'accueil au centre du rendu tramé, comme le canevas vide de l'éditeur vectoriel.
        self.start_hint = StartHint(self.dither_view, tr("img.empty_title"),
                                    [(None, [("open", tr("img.empty_open"), "document-open")], 40)],
                                    is_empty=lambda: self._source_image is None)
        self.start_hint.command.connect(lambda _name: self.load_requested.emit())
        # À droite, comme dans l'éditeur vectoriel : barre d'édition, puis les propriétés de l'image.
        side = QWidget()
        side.setProperty("role", "sidebar")              # panneau latéral (thèmes modernes : plus sombre, à plat)
        side_row = QHBoxLayout(side)
        side_row.setContentsMargins(0, 0, 0, 0)
        self.edit_toolbar = QToolBar()
        self.edit_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.edit_toolbar.setIconSize(QSize(20, 20))
        side_row.addWidget(self.edit_toolbar)
        properties = QGroupBox(tr("img.properties_box"))
        QVBoxLayout(properties).addWidget(self.settings)
        holder = QWidget()                               # fond du panneau latéral sous le cadre
        holder.setProperty("role", "sidebar")
        QVBoxLayout(holder).addWidget(properties)
        self._settings_scroll = self._side_scroll(holder)
        self._settings_scroll.setVisible(False)          # affichées une fois l'image chargée (show_source)
        self.fit_settings_width()
        side_row.addWidget(self._settings_scroll)
        row.addWidget(side)
        layout.addLayout(row, 1)
        # Loupes : placées par la fenêtre dans la barre flottante des aperçus (avec annuler, pivoter…).
        self.zoom_in_action = self._zoom_action("zoom-in", "ui.zoom_in_tip", self.zoom_in)
        self.zoom_out_action = self._zoom_action("zoom-out", "ui.zoom_out_tip", self.zoom_out)
        # Recadrer : dans la même barre flottante ; actif seulement avec une image (set_crop_enabled).
        self.crop_action = QAction(self._crop_icon(), tr("img.crop_tip"), self)
        self.crop_action.setToolTip(tr("img.crop_tip"))
        self.crop_action.triggered.connect(lambda: self.crop_requested.emit())
        self.crop_action.setEnabled(False)
        zoom_shortcuts(self, self.zoom_in, self.zoom_out)
        self.view_toolbar = self._view_toolbar()
        # Un réglage de tons change : l'aperçu de l'originale suit (regroupé sur 80 ms) quand la case est cochée.
        self.settings.processing_changed.connect(self._tones_changed)

    # -- construction

    def zoom_in(self):
        """Loupe « + » : les deux aperçus (originale et rendu tramé) ensemble."""
        for view in (self.source_view, self.dither_view):
            view.zoom_in()

    def zoom_out(self):
        for view in (self.source_view, self.dither_view):
            view.zoom_out()

    def set_crop_enabled(self, enabled):
        self.crop_action.setEnabled(bool(enabled))

    def _crop_icon(self):
        """Recadrer : deux équerres croisées, dans la couleur du texte du thème."""
        def draw(painter, color):
            painter.setPen(QPen(color, 2.5))
            painter.drawPolyline(QPolygonF([QPointF(9, 3), QPointF(9, 23), QPointF(29, 23)]))
            painter.drawPolyline(QPolygonF([QPointF(3, 9), QPointF(23, 9), QPointF(23, 29)]))
        return painted_icon(self.palette(), draw)

    def _zoom_action(self, icon, tip_key, slot):
        action = QAction(palette_icon(icon, self.palette()), tr(tip_key), self)
        action.setToolTip(tr(tip_key))
        action.triggered.connect(slot)
        return action

    def _view_toolbar(self):
        """Barre flottante à gauche des aperçus : comparaison des algorithmes de tramage et « Afficher
        l'originale »."""
        self.compare_action = QAction(palette_icon("view-app-grid", self.palette()), tr("img.compare_algos"), self)
        self.compare_action.setToolTip(tr("img.compare_algos_tip"))
        self.compare_action.triggered.connect(lambda: self.compare_requested.emit())
        self.show_original_action = QAction(self._original_icon(), tr("img.show_original"), self)
        self.show_original_action.setToolTip(tr("img.show_original_tip"))
        self.show_original_action.setCheckable(True)
        self.show_original_action.toggled.connect(self._show_original)
        return FloatingToolBar([self.compare_action, self.show_original_action], self.preview_area,
                               anchor="left")

    def _picture_icon(self):
        """Icône « image » : cadre, montagnes et soleil, dans la couleur du texte du thème."""
        def draw(painter, color):
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(3, 5, 26, 22, 3, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(22, 12), 3, 3)
            painter.drawPolygon(QPolygonF([QPointF(5, 25), QPointF(13, 14), QPointF(19, 21), QPointF(22, 18),
                                           QPointF(27, 25)]))
        return painted_icon(self.palette(), draw)

    def _original_icon(self):
        """Afficher l'originale : deux cadres côte à côte, dans la couleur du texte du thème."""
        def draw(painter, color):
            painter.setPen(QPen(color, 2.5))
            painter.drawRect(3, 7, 11, 18)
            painter.drawRect(18, 7, 11, 18)
        return painted_icon(self.palette(), draw)

    def _previews(self):
        """Image originale et rendu tramé, côte à côte dans un séparateur."""
        self._source_box, self.source_view = self._preview_box(
            "ui.source_image_box"
        )
        # Case au-dessus de l'originale : l'affiche avec les réglages de tons.
        self.preview_tones_check = QCheckBox(tr("img.preview_tones"))
        self.preview_tones_check.setToolTip(tr("img.preview_tones_tip"))
        self.preview_tones_check.toggled.connect(lambda _checked: self._show_source_image())
        # À côté : l'aperçu en négatif (affichage seulement, indépendant de « Inverser Couleurs » et des réglages).
        self.preview_invert_check = QCheckBox(tr("img.preview_invert"))
        self.preview_invert_check.setToolTip(tr("img.preview_invert_tip"))
        self.preview_invert_check.toggled.connect(lambda _checked: self._show_source_image())
        preview_options = QHBoxLayout()
        preview_options.addWidget(self.preview_tones_check)
        preview_options.addWidget(self.preview_invert_check)
        preview_options.addStretch(1)
        self._source_box.layout().insertLayout(0, preview_options)
        dither_box, self.dither_view = self._preview_box("ui.final_raster_box")
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._source_box)
        self._splitter.addWidget(dither_box)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setChildrenCollapsible(False)
        # Image originale masquée par défaut : le rendu tramé prend toute
        # la place.
        self._source_box.setVisible(False)
        self.preview_area = self._splitter
        return self._splitter

    @staticmethod
    def _preview_box(title_key):
        box = QGroupBox(tr(title_key))
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        view = ZoomableGraphicsView()
        layout.addWidget(view)
        box.setLayout(layout)
        box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        return box, view

    @staticmethod
    def _side_scroll(content):
        """Panneau de réglages sur le côté : défilement vertical si la
        hauteur manque, jamais horizontal (voir fit_settings_width)."""
        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        return scroll

    def fit_settings_width(self, width=360):
        """Largeur fixe du panneau de réglages, comme celui de l'onglet
        Séparation, élargie au besoin pour que le contenu tienne sans
        défilement horizontal.

        À rappeler quand les textes du panneau changent de longueur (par
        exemple après avoir rempli l'information sur la focale).
        """
        scroll = self._settings_scroll
        # La mise en page garde en cache la taille de chaque champ jusqu'au
        # prochain tour de la boucle d'événements : chaque champ signale la
        # sienne, recalculée avec les textes actuels.
        for child in self.settings.findChildren(QWidget):
            child.updateGeometry()
        self.settings.layout().invalidate()
        self.settings.updateGeometry()                # le cadre « Propriétés de l'image » relit sa taille
        for widget in scroll.widget().findChildren(QGroupBox):
            widget.updateGeometry()
            widget.layout().invalidate()
        scroll.widget().layout().invalidate()
        needed = (
            scroll.widget().minimumSizeHint().width()
            + scroll.verticalScrollBar().sizeHint().width()
            + 2 * scroll.frameWidth()
        )
        scroll.setFixedWidth(max(width, needed))

    # -- affichage

    @staticmethod
    def _grayscale_qimage(image):
        """QImage d'une image PIL en niveaux de gris (copie : indépendante des octets de PIL)."""
        data = image.tobytes()
        return QImage(data, image.width, image.height, image.width, QImage.Format.Format_Grayscale8).copy()

    def show_source(self, image):
        """Image chargée (PIL, niveaux de gris), ou None : les deux aperçus sont vidés."""
        self._source_image = image
        self._settings_scroll.setVisible(image is not None)
        self.start_hint.refresh()
        # Nouvelle image (chargée, recadrée, pivotée) : aperçus vidés, donc cadrés sur elle à son affichage.
        self.source_view.clear_image()
        self.dither_view.clear_image()
        if image is None:
            return
        self._show_source_image()

    # Taille maximale (px) de l'image réglée pour l'aperçu : au-delà, elle est réduite puis remise à l'échelle.
    TONES_PREVIEW_MAX_PX = 1600

    def _tones_changed(self):
        if self.preview_tones_check.isChecked() and self._source_image is not None:
            self._tones_timer.start()

    def _show_source_image(self):
        """Originale affichée : telle quelle, avec luminosité / contraste / gamma / netteté si « Aperçu avec les
        réglages » est cochée, et/ou en négatif si « Inverser l'aperçu » l'est. L'image modifiée, calculée en
        taille réduite, est remise à l'échelle de l'originale pour que le zoom et la position ne bougent pas."""
        image = self._source_image
        if image is None:
            return
        view = self.source_view
        tones = self.preview_tones_check.isChecked()
        invert = self.preview_invert_check.isChecked()
        modified = tones or invert
        if not modified:
            view.pixmap_item.setScale(1.0)
            view.set_image(self._grayscale_qimage(image))
            return
        small = image.copy()
        small.thumbnail((self.TONES_PREVIEW_MAX_PX, self.TONES_PREVIEW_MAX_PX))
        if tones:
            values = self.settings.model.processing_params()
            small = tone_preview(small, values["bright"], values["contrast"], values["gamma"], values["sharp"])
        if invert:
            small = ImageOps.invert(small.convert("L"))
        view.pixmap_item.setScale(image.width / small.width)      # avant set_image : cadrage à la bonne taille
        view.set_image(self._grayscale_qimage(small))

    def show_processed(self, _array, image):
        """Rendu tramé (ImageController.processed)."""
        self.dither_view.set_image(self._grayscale_qimage(image))

    def _show_original(self, checked):
        """Affiche ou masque l'image originale ; quand elle est visible,
        les deux cadres ont la même largeur."""
        self._source_box.setVisible(bool(checked))
        if checked:
            # Après la mise en page de Qt.
            QTimer.singleShot(0, self._equalize_previews)

    def _equalize_previews(self):
        if not self._source_box.isVisible():
            return
        total = sum(self._splitter.sizes())
        if total <= 0:
            total = max(self._splitter.width(), 200)
        half = total // 2
        self._splitter.setSizes([half, total - half])
