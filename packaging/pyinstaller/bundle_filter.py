"""Ce que PyInstaller embarque sans que Laser Studio Pro s'en serve.

Utilisé par les fichiers .spec (packaging/pyinstaller/LaserStudioPro.spec
pour Windows et Linux, packaging/macos/LaserStudioPro.spec pour macOS) :

    from bundle_filter import prune
    a.binaries = prune(a.binaries)
    a.datas = prune(a.datas)

Mesuré sur la compilation Linux du 2026-11-15 (1,1 Go décompressé) :

- modules Qt jamais chargés (~67 Mo) : l'application n'utilise que des
  widgets, pas de QML. Liste obtenue par `ldd` sur les modules PyQt6 et
  les plugins Qt embarqués : aucune autre bibliothèque n'en dépend ;
- les modules QML de Qt (dossier qml/, ~15 Mo), pour la même raison ;
- les outils de développement de Chromium (~12 Mo) ;
- les traductions de Qt et de QtWebEngine autres que nos 4 langues
  (~50 Mo).

Les noms sont comparés sans préfixe ni extension, pour que la même liste
serve sous Linux (libQt6Quick3D.so.6), Windows (Qt6Quick3D.dll) et macOS
(QtQuick3D.framework).
"""

import re

# Modules Qt (nom sans « Qt6 » ni « Qt ») dont aucune bibliothèque utilisée
# ne dépend. QtQuick, QtQml, QtQuickWidgets, QtOpenGL, QtPositioning et
# QtWebChannel restent : QtWebEngine (Stencil Studio) en a besoin.
UNUSED_QT_MODULES = (
    "Multimedia",
    "MultimediaQuick",
    "PositioningQuick",
    "QmlCore",
    "Quick3D",
    "QuickControls2",
    "QuickDialogs2",
    "QuickEffects",
    "QuickLayouts",
    "QuickParticles",
    "QuickShapes",
    "QuickTemplates2",
    "QuickTest",
    "QuickTimeline",
    "QuickVectorImage",
    "RemoteObjects",
    "Sensors",
    "ShaderTools",
    "SpatialAudio",
    "StateMachine",
    "TextToSpeech",
    "WebChannelQuick",
    "WebEngineQuick",
    "WebSockets",
)

# Langues de l'application (en : anglais, langue par défaut de Qt).
KEPT_LANGUAGES = ("fr", "en", "de", "es")

# « Quick3D » couvre aussi Quick3DPhysics, Quick3DXr… ; « QuickControls2 »
# tous les styles QML.
_QT_MODULE = re.compile(
    r"(?:^|/)(?:lib)?Qt6?(" + "|".join(UNUSED_QT_MODULES) + r")[A-Za-z0-9]*(?:\.|$)"
)
# Traductions de Qt : qtbase_fr.qm, qt_help_de.qm, qtwebengine_es.qm…
_QT_TRANSLATION = re.compile(r"/translations/[a-z_]+?_([a-z]{2})(?:_[A-Z]{2})?\.qm$")
# Traductions de Chromium : qtwebengine_locales/fr.pak, en-US.pak…
_WEBENGINE_LOCALE = re.compile(r"/qtwebengine_locales/([a-z]{2,3})(?:-[A-Za-z0-9]+)?\.pak$")


def is_unused(dest):
    """Vrai si le fichier (chemin de destination dans le bundle) ne sert pas."""
    path = dest.replace("\\", "/")
    if "/Qt6/qml/" in path or path.startswith("PyQt6/Qt6/qml/"):
        return True
    if path.endswith("qtwebengine_devtools_resources.pak"):
        return True
    if _QT_MODULE.search(path):
        return True
    for pattern in (_QT_TRANSLATION, _WEBENGINE_LOCALE):
        match = pattern.search(path)
        if match and match.group(1) not in KEPT_LANGUAGES:
            return True
    return False


def prune(toc):
    """Liste PyInstaller (a.binaries, a.datas) sans les fichiers inutiles."""
    return [entry for entry in toc if not is_unused(entry[0])]
