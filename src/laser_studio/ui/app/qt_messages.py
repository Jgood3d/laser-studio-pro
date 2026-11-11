"""Avertissements de Qt sans conséquence, écartés de la console."""
import sys

from PyQt6.QtCore import QLoggingCategory, qInstallMessageHandler

# Messages écartés par qt_message_handler.
IGNORED_QT_MESSAGES = (
    # Sous Wayland, seule une fenêtre popup (menu, liste déroulante) peut
    # capturer la souris. Quand un widget de Qt le demande pour une fenêtre
    # normale, Qt ignore la demande et écrit ce message.
    "This plugin supports grabbing the mouse only for popup windows",
)


def qt_message_handler(mode, context, message):
    """Affiche les messages de Qt comme d'habitude, sauf ceux de
    IGNORED_QT_MESSAGES."""
    if any(ignored in message for ignored in IGNORED_QT_MESSAGES):
        return
    category = context.category
    prefix = f"{category}: " if category and category != "default" else ""
    sys.stderr.write(f"{prefix}{message}\n")


def install_qt_message_filters():
    """Installe les filtres, à appeler au lancement avant QApplication."""
    qInstallMessageHandler(qt_message_handler)
    # Sous Wayland, Qt affiche « qt.qpa.wayland.textinput: … Trying to
    # disable … but 0x0 is focused » quand le focus clavier change à la
    # fermeture d'une fenêtre : avertissement interne à Qt, sans conséquence.
    # On masque cette seule catégorie (QT_LOGGING_RULES permet de la
    # réactiver).
    QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput=false")
