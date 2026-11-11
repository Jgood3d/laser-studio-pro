"""Onglet « Séparation Couleur / Verre » : réglages et aperçus.

Utilisation :

    from ui.tabs.separation import SeparationTab

    tab = SeparationTab()
    tab.tone_changed.connect(...)
"""

from ui.tabs.separation.tab import SeparationTab

__all__ = ["SeparationTab"]
