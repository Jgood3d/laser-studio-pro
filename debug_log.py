"""Journal de débogage de la gravure : file d'attente, envoi du G-Code et port série.

Activé par la variable d'environnement LASER_STUDIO_DEBUG=1 :
- console (stderr) : niveau INFO (étapes, erreurs, blocages) ;
- fichier gravure_debug.log du dossier de données (voir get_autosave_dir) : niveau DEBUG,
  avec en plus chaque ligne envoyée (TX) et chaque réponse de GRBL (RX).
Sans la variable, le journal est muet (aucun handler, niveau WARNING ignoré).
"""
import logging
import os
import re

from app_utils import get_autosave_dir

LOGGER_NAME = "laser_studio.gravure"
LOG_FILENAME = "gravure_debug.log"

# Ligne de G-Code plausible : commande G/M/S/F/T/X/Y/Z…, réglage $, ou caractère temps réel.
_GCODE_LINE_RE = re.compile(r'^(?:[GMSFTXYZIJKPNR][-+\d.]|\$|[?!~])', re.IGNORECASE)


def get_logger():
    return logging.getLogger(LOGGER_NAME)


def setup_debug_logging():
    """Configure le journal si LASER_STUDIO_DEBUG est défini. Renvoie le chemin du fichier
    de log, ou None si le débogage est désactivé."""
    logger = get_logger()
    if os.environ.get("LASER_STUDIO_DEBUG", "") in ("", "0"):
        logger.addHandler(logging.NullHandler())
        return None
    if any(not isinstance(h, logging.NullHandler) for h in logger.handlers):
        return getattr(logger, "_debug_log_path", None)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s.%(msecs)03d [%(threadName)s] %(levelname)s %(message)s",
                            "%H:%M:%S")
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)
    path = os.path.join(get_autosave_dir(), LOG_FILENAME)
    try:
        file_handler = logging.FileHandler(path, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
        logger._debug_log_path = path
    except OSError as e:
        logger.warning("Impossible d'écrire le journal %s : %s", path, e)
        path = None
    logger.info("Débogage gravure actif, journal détaillé : %s", path)
    return path


def describe_gcode(text, sample=5):
    """Résumé d'un G-Code pour le journal : nombre de lignes envoyées, premières lignes, et
    lignes qui ne ressemblent pas à du G-Code (ex. messages de la console copiés avec)."""
    lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith(";")]
    suspects = [(i + 1, l) for i, l in enumerate(lines) if not _GCODE_LINE_RE.match(l)]
    return {
        "lines": len(lines),
        "chars": len(text),
        "first": lines[:sample],
        "suspects": suspects[:20],
        "suspect_count": len(suspects),
    }


def log_gcode_summary(logger, label, text):
    info = describe_gcode(text)
    logger.info("%s : %d lignes à envoyer (%d caractères)", label, info["lines"], info["chars"])
    logger.debug("%s : premières lignes %r", label, info["first"])
    if info["suspect_count"]:
        logger.warning("%s : %d ligne(s) qui ne ressemblent pas à du G-Code, envoyées telles quelles "
                       "à GRBL (n° de ligne, texte) : %r", label, info["suspect_count"], info["suspects"])
