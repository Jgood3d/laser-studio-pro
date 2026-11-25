"""Onglet « Graver une image » (vue ImageTab) et sa logique (ImageController), reliés.

    tab, image = build_image_tab(image_settings, image_history, machine, layers, dialogs, image_actions,
                                 configure_focal=..., compare=..., status=...)
"""
from laser_studio.controllers.image import ImageController
from laser_studio.ui.tabs.image.cartoon_dialog import CartoonFilterDialog
from laser_studio.ui.tabs.image.crop_dialog import CropDialog
from laser_studio.ui.tabs.image.resolution_box import RESOLUTION_LMM
from laser_studio.ui.tabs.image.settings_panel import FILTER_CARTOON
from laser_studio.ui.tabs.image.tab import ImageTab


def build_image_tab(image_settings, image_history, machine, layers, dialogs, image_actions, *,
                    configure_focal, compare, status, parent=None):
    """Champs liés à `image_settings` (annuler / refaire : `image_history`) ; taille réduite au plateau
    de `machine` ; liste « Calque de gravure » d'après `layers` ; actions de la barre d'outils
    inscrites dans `image_actions`. Rappels : `configure_focal()` (bouton de la focale), `compare()` (comparaison des algorithmes),
    `status(texte, infobulle)`. Renvoie (ImageTab, ImageController)."""
    tab = ImageTab()
    settings = tab.settings
    settings.bind_settings(image_settings)
    resolution = settings.resolution_box
    image = ImageController(
        image_settings, machine, dialogs,
        size_mm=settings.size_mm,
        set_size=settings.set_size,
        keep_ratio=settings.keep_ratio_check.isChecked,
        lines_mm=resolution.lines_per_mm,
        parent=parent,
    )
    tab.load_requested.connect(image.open_image)
    settings.processing_changed.connect(image.schedule_processing)
    # Matière choisie par l'utilisateur (pas par programme) : coche ou décoche le négatif.
    settings.material_combo.activated.connect(
        lambda _index: image_settings.choose_material(settings.material_combo.material()))
    # Calque de gravure choisi : sa vitesse et sa puissance deviennent celles de la gravure.
    settings.engrave_layer_changed.connect(layers.select_engrave_layer)
    settings.size_changed.connect(image.dimension_changed)
    # Résolution changée (saisie, DPI, focale, réglages restaurés) : image retraitée (la matrice
    # de test et la Séparation se branchent sur settings.resolution_changed à leur création).
    settings.resolution_changed.connect(image.schedule_processing)
    settings.configure_focal_requested.connect(configure_focal)
    # « Image déjà tramée » : la résolution se cale sur les pixels de l'image (1 pixel = 1 ligne de gravure,
    # la taille en mm venant des DPI du fichier). L'ancien mode de résolution est rendu à la désactivation.
    previous_resolution = []

    def match_pixels():
        if not image_settings.as_is or image.raw_image is None:
            return
        width_mm = settings.size_mm()[0]
        if width_mm > 0:
            resolution.mode_combo.setCurrentIndex(RESOLUTION_LMM)
            resolution.set_lines_per_mm(image.raw_image.width / width_mm)

    def as_is_clicked(checked):
        if checked:
            previous_resolution[:] = [resolution.saved_state()]
            match_pixels()
            image.warn_if_not_binary()
        elif previous_resolution:
            resolution.restore_state(*previous_resolution.pop())

    settings.as_is_check.clicked.connect(as_is_clicked)
    image.source_changed.connect(lambda source: (match_pixels(), image.warn_if_not_binary())
                                 if source is not None else None)
    # Algorithme choisi dans la liste par l'utilisateur (pas par programme) : mémorisé.
    settings.algorithm_combo.textActivated.connect(image.remember_algorithm)
    # « Appliquer un filtre » : Effet BD ouvre sa fenêtre (aperçu en direct, Annuler remet l'image) ;
    # « Aucun » retire l'effet. Fenêtre NON modale : un bureau comme GNOME accroche une fenêtre modale à
    # la fenêtre principale (la déplacer entraînait et redimensionnait la fenêtre principale).
    open_dialog = []

    def choose_filter(name):
        if name == FILTER_CARTOON:
            if open_dialog:                              # déjà ouverte : ramenée devant
                open_dialog[0].raise_()
                open_dialog[0].activateWindow()
                return
            dialog = CartoonFilterDialog(image_settings, parent or tab)
            dialog.finished.connect(lambda _result: open_dialog.clear())
            open_dialog.append(dialog)
            dialog.show()
        else:
            if open_dialog:
                open_dialog[0].accept()                  # fermée sans remettre l'ancien réglage
            image_settings.update(cartoon_radius=0)

    settings.filter_requested.connect(choose_filter)

    # « Recadrer » : l'image entière et le cadre actuel ; la taille en mm suit le cadre (ImageController.crop).
    # Fenêtre non modale (comme l'effet BD) : GNOME accrocherait une fenêtre modale à la fenêtre principale.
    open_crop_dialog = []

    def open_crop():
        if image.source_image is None or image.raw_image is None:
            return
        if open_crop_dialog:
            open_crop_dialog[0].raise_()
            open_crop_dialog[0].activateWindow()
            return
        mm_per_px = settings.size_mm()[0] / max(image.raw_image.width, 1)
        dialog = CropDialog(image.source_image, image.crop_box, mm_per_px, parent or tab)
        dialog.accepted.connect(lambda: image.crop(dialog.box()))
        dialog.finished.connect(lambda _result: open_crop_dialog.clear())
        open_crop_dialog.append(dialog)
        dialog.show()

    tab.crop_requested.connect(open_crop)
    image.source_changed.connect(lambda source: tab.set_crop_enabled(source is not None))
    settings.undo_requested.connect(image_history.undo)
    settings.redo_requested.connect(image_history.redo)
    tab.compare_requested.connect(compare)
    image.source_changed.connect(tab.show_source)
    image.source_changed.connect(image_actions.update_state)
    image_actions.add(
        tab, has_image=image.has_image,
        rotate=lambda clockwise: (image.rotate_right if clockwise else image.rotate_left)(),
        clear=image.clear, confirm_clear=False)          # clear() demande elle-même confirmation
    image.processed.connect(tab.show_processed)
    image.status.connect(status)

    def refresh_engrave_layers(*_args):
        """Liste « Calque de gravure » : calques ajoutés, supprimés, renommés ou changés de mode."""
        layer = layers.engrave_layer()
        settings.engrave_layer_combo.set_layers(layers.layers, layer.id if layer else None)

    refresh_engrave_layers()
    layers.changed.connect(refresh_engrave_layers)
    # Résolution calée sur la focale du laser au départ, puis largeur du
    # panneau d'après ses textes (dont l'information sur la focale).
    resolution.set_focal(machine.focal)
    resolution.refresh()
    tab.fit_settings_width()
    return tab, image
