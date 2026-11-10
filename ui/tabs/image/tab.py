"""Onglet « Graver une image » : réglages, aperçus original et tramé."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
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

from i18n import tr
from ui.tabs.image.settings_panel import ImageSettingsPanel
from ui.widgets import TabToolBar, ZoomableGraphicsView


class ImageTab(QWidget):
    """Réglages de l'image à gauche, aperçus original et tramé à droite.

    Les réglages sont dans `settings` (ImageSettingsPanel), qui émet ses
    propres signaux. La barre d'outils émet compare_requested
    (comparaison des algorithmes de tramage) et fullscreen_requested.
    L'image originale est masquée par défaut ; la case « Afficher
    l'originale » la montre, à côté du rendu tramé et de même largeur.

        tab = ImageTab()
        tab.settings.processing_changed.connect(self.update_image_processing)
        tab.compare_requested.connect(show_comparison)

    La fenêtre dessine dans source_view et dither_view.
    """

    compare_requested = pyqtSignal()
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = ImageSettingsPanel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._toolbar())
        row = QHBoxLayout()
        # Réglages de l'image à gauche, comme dans Séparation.
        self._settings_scroll = self._side_scroll(self.settings)
        self.fit_settings_width()
        row.addWidget(self._settings_scroll)
        row.addWidget(self._previews(), 1)
        layout.addLayout(row)

    # -- construction

    def _toolbar(self):
        """Comparaison des algorithmes et « Afficher l'originale » à
        gauche, plein écran à droite."""
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
                )
            ],
            left_widgets=[self.show_original_check],
        )
        toolbar.fullscreen_requested.connect(self.fullscreen_requested)
        self._fullscreen_control = toolbar.fullscreen_action
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
