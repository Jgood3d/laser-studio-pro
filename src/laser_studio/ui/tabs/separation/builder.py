"""Onglet « Séparation Couleur / Verre » (vue SeparationTab), ses réglages (SeparationSettings) et
sa logique (SeparationController), reliés à « Graver une image ».

    tab, separation = build_separation_tab(image_settings, image, job, dialogs, image_actions, parent,
                                           lines_mm=resolution_box.lines_per_mm)
"""
from laser_studio.controllers.separation import SeparationController
from laser_studio.models.separation import SeparationSettings
from laser_studio.ui.tabs.separation.tab import SeparationTab
from laser_studio.ui.utils import busy_cursor


def build_separation_tab(image_settings, image, job, dialogs, image_actions, parent, *, lines_mm):
    """La tonalité de l'image devient l'image de « Graver une image » (`image`, ImageController), dont le
    calque noir revient aux aperçus ; résolution de gravure : `lines_mm()` ; test du gain de point par
    `job`. Pivoter, miroirs, supprimer : inscrits dans `image_actions`.
    Renvoie (SeparationTab, SeparationController) ; les réglages sont `controller.settings`."""
    tab = SeparationTab()
    settings = SeparationSettings(parent)
    tab.bind_settings(settings)
    separation = SeparationController(
        settings, image_settings,
        frame_args=tab.frame_args, engrave_lmm=lines_mm,
        dialogs=dialogs,
        engraved=lambda: image.processed_array,
        image_busy=image.is_busy,
        current_preview=tab.preview_tabs.currentIndex,
        is_visible=tab.isVisible,
        busy=busy_cursor,
        parent=parent,
    )
    tab.load_requested.connect(separation.open_image)
    tab.image_dropped.connect(separation.load_path)
    tab.tone_changed.connect(separation.schedule_push)
    tab.preview_changed.connect(separation.schedule_previews)
    tab.gain_test_requested.connect(job.generate_gain_test)
    tab.export_requested.connect(separation.export_files)
    tab.preview_tab_changed.connect(separation.render_current)
    separation.source_changed.connect(tab.set_source)
    separation.source_changed.connect(image_actions.update_state)
    image_actions.add(
        tab, has_image=separation.has_image,
        rotate=lambda clockwise: separation.rotate_image(-90 if clockwise else 90),   # PIL : positif = antihoraire
        clear=separation.clear)
    separation.image_loaded.connect(tab.fit_plate_to_image)
    separation.image_rotated.connect(tab.swap_plate_size)
    separation.preview_ready.connect(tab.show_preview)
    separation.previews_invalidated.connect(separation.refresh_previews)
    separation.engrave_dpi_changed.connect(tab.set_engrave_dpi)
    separation.tone_ready.connect(image.set_image)
    # Liens avec « Graver une image » : réglages du verre rendus quand une image y est
    # chargée, oubliés à la réinitialisation ; calque noir recalculé : aperçus à refaire.
    image.loading_file.connect(separation.release_glass_settings)
    image.resetting.connect(separation.forget_glass_settings)
    image.processed.connect(lambda *_args: separation.engraved_changed())
    tab.set_engrave_dpi(separation.engrave_dpi())
    return tab, separation
