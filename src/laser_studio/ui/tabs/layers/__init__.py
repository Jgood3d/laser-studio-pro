"""Onglet « Calques » : liste des calques et de leurs réglages laser.

Utilisation :

    from laser_studio.ui.tabs.layers import LayersTab

    tab = LayersTab(layer_manager, focal_getter=lambda: 0.1)
    tab.layers_changed.connect(self.on_layers_changed)
"""

from laser_studio.ui.tabs.layers.tab import LayersTab

__all__ = ["LayersTab"]
