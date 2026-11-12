"""Petits widgets réutilisables, partagés par plusieurs parties de l'interface.

Utilisation :

    from laser_studio.ui.widgets import AutoHideLabel, HistoryLineEdit, TabToolBar
"""

from laser_studio.ui.widgets.auto_hide_label import AutoHideLabel
from laser_studio.ui.widgets.fullscreen_window import FullscreenWindow
from laser_studio.ui.widgets.history_line_edit import HistoryLineEdit
from laser_studio.ui.widgets.slider_with_buttons import SliderWithButtons
from laser_studio.ui.widgets.tab_close_button import TabCloseButton
from laser_studio.ui.widgets.tab_toolbar import TabToolBar
from laser_studio.ui.widgets.zoomable_graphics_view import ZoomableGraphicsView

__all__ = [
    "AutoHideLabel",
    "FullscreenWindow",
    "HistoryLineEdit",
    "SliderWithButtons",
    "TabCloseButton",
    "TabToolBar",
    "ZoomableGraphicsView",
]
