"""Petits widgets réutilisables, partagés par plusieurs parties de l'interface.

Utilisation :

    from laser_studio.ui.widgets import AutoHideLabel, FloatingToolBar, HistoryLineEdit
"""

from laser_studio.ui.widgets.auto_hide_label import AutoHideLabel
from laser_studio.ui.widgets.floating_toolbar import FloatingToolBar
from laser_studio.ui.widgets.fullscreen_window import FullscreenWindow
from laser_studio.ui.widgets.history_line_edit import HistoryLineEdit
from laser_studio.ui.widgets.slider_with_buttons import SliderWithButtons
from laser_studio.ui.widgets.start_hint import StartHint
from laser_studio.ui.widgets.zoomable_graphics_view import ZoomableGraphicsView

__all__ = [
    "AutoHideLabel",
    "FloatingToolBar",
    "FullscreenWindow",
    "HistoryLineEdit",
    "SliderWithButtons",
    "StartHint",
    "ZoomableGraphicsView",
]
