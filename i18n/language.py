"""Langue de l'interface (mémorisée entre deux sessions) et traduction."""

from PyQt6.QtCore import QSettings

from i18n.translations import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TRANSLATIONS

_current_lang = None


def get_current_language():
    """Langue actuellement sélectionnée (mémorisée entre sessions)."""
    global _current_lang
    if _current_lang is None:
        settings = QSettings("LaserStudioPro", "UIConfig")
        stored = settings.value("language", DEFAULT_LANGUAGE)
        _current_lang = stored if stored in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return _current_lang


def set_language(lang_code):
    """Change la langue mémorisée. Prend effet au prochain lancement."""
    global _current_lang
    if lang_code not in SUPPORTED_LANGUAGES:
        return
    _current_lang = lang_code
    settings = QSettings("LaserStudioPro", "UIConfig")
    settings.setValue("language", lang_code)


def tr(key):
    """Renvoie le texte traduit pour la clé donnée, dans la langue
    actuellement sélectionnée."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    lang = get_current_language()
    return entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
