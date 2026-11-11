"""Système de traduction simple par dictionnaire, sans dépendance externe
(pas de fichiers .ts/.qm Qt Linguist à compiler). Le changement de langue
est mémorisé et appliqué au prochain lancement de l'application — pas de
rafraîchissement « à chaud » de l'interface déjà construite, ce qui évite
d'avoir à retenir et reconstruire chaque widget affiché un par un.

Utilisation : from i18n import tr
              menu_bar.addMenu(tr("menu.file"))

Les textes sont dans i18n/translations.py, la langue choisie et tr() dans
i18n/language.py.
"""

from laser_studio.i18n.language import get_current_language, set_language, tr
from laser_studio.i18n.translations import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "TRANSLATIONS",
    "get_current_language",
    "set_language",
    "tr",
]
