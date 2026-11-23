"""Textes de l'interface, dans chaque langue (dictionnaire TRANSLATIONS).

Les textes sont rangés par zone dans i18n/texts/ (un dictionnaire TEXTS par
module : app, vector, box, ornament, generators, camera, image, machine,
materials). Pour ajouter un texte : une clé dans le module de sa zone, et sa
traduction dans chaque langue de SUPPORTED_LANGUAGES (le français au minimum).
Une clé définie dans deux modules arrête le chargement (ImportError).

Note sur la qualité des traductions : le français et l'anglais sont
soigneusement relus. L'allemand et l'espagnol sont une première passe
raisonnable mais n'ont pas été relus par une personne native — une
relecture est bienvenue avant de les considérer définitifs.
"""
from laser_studio.i18n.texts import app
from laser_studio.i18n.texts import box
from laser_studio.i18n.texts import camera
from laser_studio.i18n.texts import generators
from laser_studio.i18n.texts import image
from laser_studio.i18n.texts import machine
from laser_studio.i18n.texts import materials
from laser_studio.i18n.texts import ornament
from laser_studio.i18n.texts import vector

SUPPORTED_LANGUAGES = {"fr": "Français", "en": "English", "de": "Deutsch", "es": "Español"}
DEFAULT_LANGUAGE = "fr"

TEXT_MODULES = (app, box, camera, generators, image, machine, materials, ornament, vector)


def _merge(modules):
    merged = {}
    for module in modules:
        for key, value in module.TEXTS.items():
            if key in merged:
                raise ImportError(f"clé de traduction définie deux fois : {key} ({module.__name__})")
            merged[key] = value
    return merged


# Clé -> { code_langue: texte }. Une clé absente ou une langue manquante
# retombe automatiquement sur le français, puis sur la clé elle-même :
# jamais de plantage ni de texte vide à cause d'une traduction manquante.
TRANSLATIONS = _merge(TEXT_MODULES)
