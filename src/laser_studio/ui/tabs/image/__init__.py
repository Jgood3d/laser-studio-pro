"""Onglet « Graver une image » : réglages, aperçus original et tramé.

Utilisation :

    from laser_studio.ui.tabs.image import ImageTab

    tab = ImageTab()
    tab.settings.processing_changed.connect(image.schedule_processing)
"""

from laser_studio.ui.tabs.image.settings_panel import ImageSettingsPanel
from laser_studio.ui.tabs.image.tab import ImageTab

__all__ = ["ImageSettingsPanel", "ImageTab"]
