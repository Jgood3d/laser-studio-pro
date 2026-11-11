"""Onglet « Séparation Couleur / Verre » : réglages et aperçus.

Utilisation :

    from laser_studio.ui.tabs.separation import SeparationTab

    tab = SeparationTab()
    tab.tone_changed.connect(...)
"""

from laser_studio.ui.tabs.separation.tab import SeparationTab

__all__ = ["SeparationTab"]
