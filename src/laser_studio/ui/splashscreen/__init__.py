"""Écran de démarrage de Laser Studio Pro.

Utilisation (main.py) :

    from laser_studio.ui.splashscreen import StartupSplash

    splash = StartupSplash()
    splash.show_and_wait()
    ...
    splash.finish(window)
"""

from laser_studio.ui.splashscreen.splash import StartupSplash

__all__ = ["StartupSplash"]
