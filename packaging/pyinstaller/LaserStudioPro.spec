# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller — Laser Studio Pro pour Windows et Linux.

Utilisé par packaging/windows/build.bat et packaging/linux/build-linux.sh
(macOS a le sien : packaging/macos/LaserStudioPro.spec). Depuis la racine
du dépôt :

    pyinstaller --noconfirm packaging/pyinstaller/LaserStudioPro.spec

Dossier dist/LaserStudioPro/ par défaut (démarrage rapide, base de
l'installeur Windows et de l'AppImage). LSP_ONEFILE=1 : un seul
exécutable dist/LaserStudioPro.

Les fichiers que l'application n'utilise pas (modules Qt QML, traductions
d'autres langues…) sont retirés par bundle_filter.prune.
"""
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

REPO_ROOT = os.path.dirname(os.path.dirname(SPECPATH))  # SPECPATH = packaging/pyinstaller/
sys.path.insert(0, SPECPATH)
from bundle_filter import prune  # noqa: E402

ONEFILE = os.environ.get("LSP_ONEFILE") == "1"
NAME = "LaserStudioPro"
ICON = os.path.join(REPO_ROOT, "src", "laser_studio", "resources", "laser_studio_pro.ico")


def windows_version_info():
    """Nom du produit et version dans les propriétés de l'exe Windows (onglet Détails), d'après APP_VERSION :
    la signature du code (SignPath) demande le même nom et la même version à chaque compilation. None hors
    Windows."""
    if sys.platform != "win32":
        return None
    import re
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                     VarFileInfo, VarStruct, VSVersionInfo)
    with open(os.path.join(REPO_ROOT, "src", "laser_studio", "core", "version.py"), encoding="utf-8") as f:
        version = re.search(r'^APP_VERSION = "([\d.]+)"', f.read(), re.M).group(1)
    numbers = tuple(int(n) for n in (version.split(".") + ["0"] * 4)[:4])
    strings = [StringStruct("CompanyName", "Laser Studio Pro"),
               StringStruct("FileDescription", "Laser Studio Pro"),
               StringStruct("ProductName", "Laser Studio Pro"),
               StringStruct("ProductVersion", version),
               StringStruct("FileVersion", version),
               StringStruct("InternalName", NAME),
               StringStruct("OriginalFilename", NAME + ".exe"),
               StringStruct("LegalCopyright", "GPL-3.0-or-later")]
    return VSVersionInfo(ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
                         kids=[StringFileInfo([StringTable("040C04B0", strings)]),
                               VarFileInfo([VarStruct("Translation", [0x040C, 1200])])])


VERSION_INFO = windows_version_info()

# Images, logo, icônes Breeze : tout src/laser_studio/resources/ (cherché par
# find_resource). Stencil Studio : le dossier est copié en données
# (ui/studio.html, locales, resources/ : police et modèle d'IA) ET ses modules sont déclarés en
# hiddenimports, pour que PyInstaller embarque aussi cv2 / numpy / scipy /
# Pillow qu'ils utilisent.
datas = [
    (os.path.join(REPO_ROOT, "src", "laser_studio", "resources"), "resources"),
    (os.path.join(REPO_ROOT, "src", "stencil_studio"), "stencil_studio"),
]
hiddenimports = [
    "serial",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "stencil_studio.controllers.studio",
    "stencil_studio.controllers.api",
    "stencil_studio.server",
    "stencil_studio.ui.dialog",
    "stencil_studio.ui.window",
    "stencil_studio.models.session",
    "stencil_studio.models.presets",
    "stencil_studio.core",
    "stencil_studio.engrave",
    "stencil_studio.lightbox",
    "stencil_studio.subject_ai",
    "stencil_studio.i18n",
    "scipy.spatial",
    "scipy.ndimage",
] + collect_submodules("serial")

a = Analysis(
    [os.path.join(REPO_ROOT, "main.py")],
    pathex=[os.path.join(REPO_ROOT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
a.binaries = prune(a.binaries)
a.datas = prune(a.datas)

pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=NAME,
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon=ICON,
        version=VERSION_INFO,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=NAME,
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon=ICON,
        version=VERSION_INFO,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name=NAME,
    )
