"""Petits widgets réutilisables, partagés par plusieurs parties de l'interface.

Utilisation :

    from ui.widgets import AutoHideLabel, HistoryLineEdit, TabToolBar
"""

from ui.widgets.auto_hide_label import AutoHideLabel
from ui.widgets.fullscreen_window import FullscreenWindow
from ui.widgets.history_line_edit import HistoryLineEdit
from ui.widgets.tab_toolbar import TabToolBar
from ui.widgets.zoomable_graphics_view import ZoomableGraphicsView

__all__ = [
    "AutoHideLabel",
    "FullscreenWindow",
    "HistoryLineEdit",
    "TabToolBar",
    "ZoomableGraphicsView",
]
