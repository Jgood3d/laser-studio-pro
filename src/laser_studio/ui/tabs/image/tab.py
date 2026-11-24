"""Onglet « Graver une image » : réglages, aperçus original et tramé."""

from PyQt6.QtCore import QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QImage, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from laser_studio.i18n import tr
from laser_studio.ui.tabs.image.settings_panel import ImageSettingsPanel
from laser_studio.ui.utils import painted_icon, palette_icon, zoom_shortcuts
from laser_studio.ui.widgets import TabToolBar, ZoomableGraphicsView


class ImageTab(QWidget):
    """Réglages de l'image à gauche, aperçus original et tramé à droite.

    Les réglages sont dans `settings` (ImageSettingsPanel), qui émet ses
    propres signaux. La barre d'outils émet compare_requested
    (comparaison des algorithmes de tramage).
    L'image originale est masquée par défaut ; la case « Afficher
    l'originale » la montre, à côté du rendu tramé et de même largeur.

        tab = ImageTab()
        tab.settings.processing_changed.connect(image.schedule_processing)
        image.source_changed.connect(tab.show_source)
        image.processed.connect(tab.show_processed)

    `preview_area` (les deux aperçus) accueille la barre flottante annuler /
    refaire / pivoter / miroirs (FloatingToolBar), posée par la fenêtre.
    """

    compare_requested = pyqtSignal()
    crop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = ImageSettingsPanel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.toolbar = self._toolbar()
        layout.addWidget(self.toolbar)
        row = QHBoxLayout()
        # Réglages de l'image à gauche, comme dans Séparation.
        self._settings_scroll = self._side_scroll(self.settings)
        self.fit_settings_width()
        row.addWidget(self._settings_scroll)
        row.addWidget(self._previews(), 1)
        layout.addLayout(row)
        # Loupes : placées par la fenêtre dans la barre flottante des aperçus (avec annuler, pivoter…).
        self.zoom_in_action = self._zoom_action("zoom-in", "ui.zoom_in_tip", self.zoom_in)
        self.zoom_out_action = self._zoom_action("zoom-out", "ui.zoom_out_tip", self.zoom_out)
        # Recadrer : dans la même barre flottante ; actif seulement avec une image (set_crop_enabled).
        self.crop_action = QAction(self._crop_icon(), tr("img.crop_tip"), self)
        self.crop_action.setToolTip(tr("img.crop_tip"))
        self.crop_action.triggered.connect(lambda: self.crop_requested.emit())
        self.crop_action.setEnabled(False)
        zoom_shortcuts(self, self.zoom_in, self.zoom_out)

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

    def _toolbar(self):
        """Comparaison des algorithmes et « Afficher l'originale »."""
        compare_icon = QIcon.fromTheme(
            "view-app-grid",
            QIcon.fromTheme(
                "view-list-icons",
                self.style().standardIcon(
                    QStyle.StandardPixmap.SP_FileDialogListView
                ),
            ),
        )
        self.show_original_check = QCheckBox(tr("img.show_original"))
        self.show_original_check.setToolTip(tr("img.show_original_tip"))
        self.show_original_check.toggled.connect(self._show_original)
        toolbar = TabToolBar(
            self,
            left_actions=[
                (
                    compare_icon,
                    tr("img.compare_algos"),
                    tr("img.compare_algos_tip"),
                    lambda: self.compare_requested.emit(),
                ),
            ],
            left_widgets=[self.show_original_check],
        )
        return toolbar

    def _previews(self):
        """Image originale et rendu tramé, côte à côte dans un séparateur."""
        self._source_box, self.source_view = self._preview_box(
            "ui.source_image_box"
        )
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
        needed = (
            self.settings.minimumSizeHint().width()
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
        if image is None:
            self.source_view.clear_image()
            self.dither_view.clear_image()
            return
        self.source_view.set_image(self._grayscale_qimage(image))

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
