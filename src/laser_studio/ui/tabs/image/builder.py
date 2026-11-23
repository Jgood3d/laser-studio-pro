"""Onglet « Graver une image » (vue ImageTab) et sa logique (ImageController), reliés.

    tab, image = build_image_tab(image_settings, image_history, machine, layers, dialogs, image_actions,
                                 resolution_changed=..., configure_focal=..., compare=..., status=...)
"""
from laser_studio.controllers.image import ImageController
from laser_studio.ui.tabs.image.tab import ImageTab


def build_image_tab(image_settings, image_history, machine, layers, dialogs, image_actions, *,
                    resolution_changed, configure_focal, compare, status, parent=None):
    """Champs liés à `image_settings` (annuler / refaire : `image_history`) ; taille réduite au plateau
    de `machine` ; liste « Calque de gravure » d'après `layers` ; actions de la barre d'outils
    inscrites dans `image_actions`. Rappels : `resolution_changed(lignes/mm)` (matrice, Séparation),
    `configure_focal()` (bouton de la focale), `compare()` (comparaison des algorithmes),
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
    settings.load_requested.connect(image.open_image)
    settings.processing_changed.connect(image.schedule_processing)
    # Matière choisie par l'utilisateur (pas par programme) : coche ou décoche le négatif.
    settings.material_combo.activated.connect(
        lambda _index: image_settings.choose_material(settings.material_combo.material()))
    # Calque de gravure choisi : sa vitesse et sa puissance deviennent celles de la gravure.
    settings.engrave_layer_changed.connect(layers.select_engrave_layer)
    settings.size_changed.connect(image.dimension_changed)
    # Résolution changée (saisie, DPI, focale, réglages restaurés) : image retraitée, puis la
    # matrice de test et la Séparation la reprennent.
    settings.resolution_changed.connect(image.schedule_processing)
    settings.resolution_changed.connect(resolution_changed)
    settings.configure_focal_requested.connect(configure_focal)
    # Algorithme choisi dans la liste par l'utilisateur (pas par programme) : mémorisé.
    settings.algorithm_combo.textActivated.connect(image.remember_algorithm)
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
