"""Onglet « Vectorisation d'image » : conversion PNG / JPEG -> SVG.

Utilisation :

    from ui.tabs.png2svg import Png2SvgTab

    tab = Png2SvgTab()
    tab.send_to_vector_requested.connect(self._on_png2svg_send_to_vector)
"""

from ui.tabs.png2svg.tab import Png2SvgTab

__all__ = ["Png2SvgTab"]
