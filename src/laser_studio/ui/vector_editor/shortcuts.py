"""Raccourcis clavier du canevas, traduits en intentions : commande de l'éditeur (« undo », « group »…), zoom,
déplacement fin au clavier. Le canevas demande la traduction, le contrôleur exécute (command_requested,
nudge_requested).

    command = key_command(event)            # "copy", "delete"… ou None
    zoom_direction(event)                   # +1, -1 ou 0
    arrow_nudge(event)                      # (dx, dy, maj, alt) ou None
    command_shortcut("group")               # « Ctrl+G »
    with_shortcut("Grouper", "group")       # « Grouper (Ctrl+G) » : infobulle du bouton
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

from laser_studio.i18n import tr

# Raccourcis standard de la plateforme (Ctrl+Z, Ctrl+Y ou Ctrl+Maj+Z…) et leur commande.
STANDARD_COMMANDS = (
    (QKeySequence.StandardKey.Undo, "undo"),
    (QKeySequence.StandardKey.Redo, "redo"),
    (QKeySequence.StandardKey.Copy, "copy"),
    (QKeySequence.StandardKey.Paste, "paste"),
)
# Ctrl + touche, et touche seule.
CONTROL_COMMANDS = {Qt.Key.Key_G: "group", Qt.Key.Key_D: "duplicate"}
PLAIN_COMMANDS = {Qt.Key.Key_Delete: "delete", Qt.Key.Key_Backspace: "delete"}
# Flèches : direction du déplacement fin (repère machine, Y vers le haut).
ARROWS = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, 1), Qt.Key.Key_Down: (0, -1)}
ZOOM_IN_KEYS = (Qt.Key.Key_Plus, Qt.Key.Key_Equal)   # Ctrl+= : « + » est sur la touche « = » en QWERTY
ZOOM_OUT_KEYS = (Qt.Key.Key_Minus,)


def _control(event):
    return bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)


def key_command(event):
    """Commande de l'éditeur d'un raccourci clavier, ou None."""
    for sequence, command in STANDARD_COMMANDS:
        if event.matches(sequence):
            return command
    if _control(event) and event.key() in CONTROL_COMMANDS:
        return CONTROL_COMMANDS[event.key()]
    return PLAIN_COMMANDS.get(event.key())


def command_shortcut(command):
    """Raccourci de la commande `command` tel que l'affiche la plateforme (« Ctrl+G », « Suppr »…), ou "" :
    l'infobulle du bouton le montre, d'après la même table que le clavier."""
    sequences = [QKeySequence(standard) for standard, name in STANDARD_COMMANDS if name == command]
    sequences += [QKeySequence(Qt.KeyboardModifier.ControlModifier.value | key.value)
                  for key, name in CONTROL_COMMANDS.items() if name == command]
    if command in PLAIN_COMMANDS.values():
        return tr("keys.delete")                                  # Qt écrirait « Del » dans toutes les langues
    sequences += {"zoom_in": [QKeySequence(QKeySequence.StandardKey.ZoomIn)],
                  "zoom_out": [QKeySequence(QKeySequence.StandardKey.ZoomOut)]}.get(command, [])
    return sequences[0].toString(QKeySequence.SequenceFormat.NativeText) if sequences else ""


def with_shortcut(tooltip, command):
    """Infobulle `tooltip` suivie du raccourci de `command` entre parenthèses, s'il en a un et qu'elle ne le
    donne pas déjà."""
    shortcut = command_shortcut(command) if command else ""
    if shortcut and f"({shortcut})" not in tooltip:
        return f"{tooltip} ({shortcut})"
    return tooltip


def zoom_direction(event):
    """+1 pour Ctrl++ (ou Ctrl+=), -1 pour Ctrl+-, sur la rangée du haut ou le pavé numérique ; 0 sinon."""
    if event.matches(QKeySequence.StandardKey.ZoomIn):
        return 1
    if event.matches(QKeySequence.StandardKey.ZoomOut):
        return -1
    if _control(event):
        if event.key() in ZOOM_IN_KEYS:
            return 1
        if event.key() in ZOOM_OUT_KEYS:
            return -1
    return 0


def arrow_nudge(event):
    """Flèche : (dx, dy, Maj enfoncée, Alt enfoncée) du déplacement fin, ou None pour une autre touche."""
    direction = ARROWS.get(event.key())
    if direction is None:
        return None
    modifiers = event.modifiers()
    return (*direction, bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
            bool(modifiers & Qt.KeyboardModifier.AltModifier))
