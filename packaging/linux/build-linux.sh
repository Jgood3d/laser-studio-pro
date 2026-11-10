#!/usr/bin/env bash
# Compile Laser Studio Pro pour Linux avec PyInstaller.
#
# Utilisation, depuis n'importe quel dossier :
#   packaging/linux/build-linux.sh [--onedir]
#
# Résultat : dist/LaserStudioPro, un exécutable unique (--onefile).
# Options :
#   --onedir   dossier dist/LaserStudioPro/ (démarrage plus rapide)
#
# Le script utilise l'environnement virtuel du projet (.venv/ ou venv/)
# s'il existe, sinon le python3 du système. PyInstaller doit y être
# installé (pip install pyinstaller), ainsi que les dépendances
# (pip install -r requirements-linux.txt). Voir BUILD.md.
set -euo pipefail

# Ce script vit dans packaging/linux/ mais s'exécute depuis la racine du
# dépôt (là où se trouve main.py), quel que soit le dossier d'où il est
# lancé.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

MODE="--onefile"
if [ "${1:-}" = "--onedir" ]; then
    MODE="--onedir"
fi

echo "=========================================="
echo "Environnement Python..."
echo "=========================================="
for venv in .venv venv; do
    if [ -f "$venv/bin/activate" ]; then
        # shellcheck disable=SC1090
        source "$venv/bin/activate"
        echo "Environnement virtuel : $venv"
        break
    fi
done
if ! python3 -m PyInstaller --version >/dev/null 2>&1; then
    echo "PyInstaller est introuvable. Installe-le : pip install pyinstaller" >&2
    exit 1
fi
echo "Python $(python3 --version | cut -d' ' -f2), PyInstaller $(python3 -m PyInstaller --version)"

echo "=========================================="
echo "Nettoyage des anciens dossiers..."
echo "=========================================="
rm -rf build dist

echo "=========================================="
echo "Compilation de Laser Studio Pro ($MODE)..."
echo "=========================================="
# Stencil Studio : le dossier est copié en données (studio.html, locales,
# polices...) ET ses modules sont déclarés en hidden-import, pour que
# PyInstaller embarque aussi cv2 / numpy / scipy / Pillow qu'ils utilisent.
# QtWebEngine est embarqué automatiquement (main.py l'importe en tête).
# Le .spec généré va dans build/ : la racine du dépôt reste propre.
python3 -m PyInstaller --noconfirm "$MODE" --windowed --name LaserStudioPro \
    --icon "$REPO_ROOT/resources/laser_studio_pro.ico" \
    --specpath build \
    --add-data "$REPO_ROOT/resources:resources" \
    --add-data "$REPO_ROOT/icons:icons" \
    --add-data "$REPO_ROOT/stencil_studio:stencil_studio" \
    --collect-submodules serial --hidden-import serial \
    --hidden-import PyQt6.QtWebEngineWidgets --hidden-import PyQt6.QtWebEngineCore \
    --hidden-import stencil_studio.studio_dialog --hidden-import stencil_studio.studio_window \
    --hidden-import stencil_studio.studio --hidden-import stencil_studio.core \
    --hidden-import stencil_studio.engrave --hidden-import stencil_studio.lightbox \
    --hidden-import stencil_studio.lsp_bridge --hidden-import stencil_studio.subject_ai \
    --hidden-import stencil_studio.i18n \
    --hidden-import scipy.spatial --hidden-import scipy.ndimage \
    main.py

echo "=========================================="
if [ "$MODE" = "--onefile" ]; then
    echo "Terminé ! L'exécutable dist/LaserStudioPro est prêt."
else
    echo "Terminé ! Le dossier dist/LaserStudioPro/ est prêt."
fi
echo "=========================================="
