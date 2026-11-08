"""Écran de démarrage de Laser Studio Pro.

Utilisation (main.py) :

    from ui.splashscreen import StartupSplash

    splash = StartupSplash()
    splash.show_and_wait()
    ...
    splash.finish(window)
"""

from ui.splashscreen.splash import StartupSplash

__all__ = ["StartupSplash"]
