"""Valeurs fixes de l'application : liens et adresses utilisés par l'interface.

Les modifier ici les change partout où elles sont utilisées.
"""

# Page de soutien (bouton de soutien et boîte « Buy me a coffee »).
KOFI_URL = "https://ko-fi.com/jb3dlaser"

# Bannière de l'application (écran de démarrage, boîte « À propos »),
# cherchée à côté de l'exécutable puis dans le bundle PyInstaller.
BANNER_FILENAME = "laser_studio_pro_banner.png"

# Écran de démarrage : largeur de la bannière, en pixels.
SPLASH_SCREEN_WIDTH = 600

# Barre d'état : durée d'affichage d'un message d'information, en
# millisecondes.
STATUS_BAR_MESSAGE_DURATION = 8000

# Écran de démarrage : durée minimale d'affichage, en secondes.
SPLASH_SCREEN_DURATION = 2.0

# Écran de démarrage : pause entre deux vérifications de son affichage, en
# secondes. Elle évite d'occuper le processeur pendant l'attente, sans
# retard visible.
SPLASH_SCREEN_SLEEP_INTERVAL = 0.02
