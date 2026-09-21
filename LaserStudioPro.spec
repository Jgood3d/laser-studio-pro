# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller — Laser Studio Pro pour macOS.

Cible l'architecture de la machine de compilation (target_arch=None) :
pas de build universal2, car numba/opencv n'ont pas toujours de wheels
universal2 disponibles. Compiler séparément sur Apple Silicon et sur
Intel si les deux cibles sont nécessaires (voir build_macos.sh).

Utilisation :
    pyinstaller LaserStudioPro.spec
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Ressources embarquées à côté de l'exécutable dans le bundle (retrouvées au
# runtime par app_utils.find_resource() / get_bundle_dir()).
datas = [
    ('laser_studio_pro.ico', '.'),
    ('laser_studio_pro_512.png', '.'),
    ('laser_studio_pro_banner.png', '.'),
]
datas += collect_data_files('pyqtgraph')
datas += collect_data_files('skimage')

hiddenimports = [
    # Import différé dans converter.py (skimage.morphology.skeletonize),
    # non détecté automatiquement par l'analyse statique de PyInstaller.
    'skimage.morphology',
    'skimage.filters',
    'skimage.measure',
]
hiddenimports += collect_submodules('skimage.morphology')
hiddenimports += collect_submodules('pyqtgraph')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LaserStudioPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Cible l'architecture native de la machine de build (arm64 ou x86_64).
    # Ne pas mettre 'universal2' : numba/opencv-python n'ont pas toujours de
    # wheels universal2 à jour.
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='laser_studio_pro.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LaserStudioPro',
)

app = BUNDLE(
    coll,
    name='LaserStudioPro.app',
    icon='laser_studio_pro.icns',
    bundle_identifier='com.jb3dlaser.laserstudiopro',
    info_plist={
        'CFBundleName': 'Laser Studio Pro',
        'CFBundleDisplayName': 'Laser Studio Pro',
        'CFBundleShortVersionString': '1.6.0',
        'CFBundleVersion': '1.6.0',
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': 'Laser Studio Pro',
        # Justification affichée par macOS si l'app demande l'accès à un
        # port série/accessoire USB (carte GRBL).
        'NSUSBAccessSerialNumbersUsageDescription': (
            "Laser Studio Pro communique avec la carte de contrôle GRBL "
            "via un port série USB."
        ),
    },
)
