"""Ports série proposés pour se connecter au graveur, et dernier port utilisé.

Sous Linux, pyserial liste aussi les ports série « virtuels » de la carte mère
(/dev/ttyS0 à ttyS31), sans matériel derrière : leur description vaut « n/a ».
Ils sont masqués, sinon l'un d'eux arrive en tête de liste et on s'y connecte
sans le savoir : le port s'ouvre, mais personne ne répond.

    labels = port_labels(serial.tools.list_ports.comports())
    # ["/dev/ttyUSB0 - USB Serial", "/dev/ttyACM0 - ...", "COM3 - ..."]
"""

import re

from PyQt6.QtCore import QSettings

LAST_PORT_KEY = "last_port"


def _settings():
    return QSettings("LaserStudioPro", "UIConfig")


def is_usable(port):
    """Faux pour un port sans matériel derrière (description « n/a »)."""
    return (port.description or "").strip().lower() != "n/a"


def is_usb(port):
    """Vrai pour un port USB (identifiant fabricant connu, ou nom ttyUSB /
    ttyACM / cu.usb*) : c'est là que se branche un graveur."""
    if getattr(port, "vid", None) is not None:
        return True
    return bool(re.search(r"ttyUSB|ttyACM|usb", port.device, re.IGNORECASE))


def _natural_key(device):
    """« ttyUSB10 » après « ttyUSB2 »."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", device)]


def port_labels(ports):
    """Libellés « port - description » des ports utilisables, les ports USB
    en tête, puis les autres ; chaque groupe dans l'ordre naturel des noms."""
    usable = [p for p in ports if is_usable(p)]
    usable.sort(key=lambda p: (not is_usb(p), _natural_key(p.device)))
    return [f"{p.device} - {p.description}" for p in usable]


def preferred_index(labels, wanted):
    """Indice du libellé dont le port est `wanted`, sinon 0 (premier port,
    un port USB s'il y en a un)."""
    if wanted:
        for index, label in enumerate(labels):
            if port_of(label) == wanted:
                return index
    return 0


def port_of(label):
    """« /dev/ttyUSB0 - USB Serial » -> « /dev/ttyUSB0 »."""
    return label.split(" - ")[0]


def load_last_port():
    """Dernier port auquel on s'est connecté avec succès ("" si aucun)."""
    return str(_settings().value(LAST_PORT_KEY, "") or "")


def save_last_port(port):
    _settings().setValue(LAST_PORT_KEY, port)
