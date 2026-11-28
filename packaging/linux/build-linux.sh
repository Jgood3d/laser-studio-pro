#!/usr/bin/env bash
# Compile Laser Studio Pro pour Linux avec PyInstaller.
#
# Utilisation, depuis n'importe quel dossier :
#   packaging/linux/build-linux.sh [--onedir]
#
# Résultat : dist/LaserStudioPro, un exécutable unique (--onefile).
# Options :
#   --onedir   dossier dist/LaserStudioPro/ (démarrage plus rapide, base de
#              l'AppImage : voir build-appimage.sh)
#
# Les réglages de compilation (fichiers embarqués, modules, filtre des
# fichiers inutiles) sont dans packaging/pyinstaller/LaserStudioPro.spec,
# partagé avec Windows.
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
export LSP_ONEFILE=1
if [ "${1:-}" = "--onedir" ]; then
    MODE="--onedir"
    export LSP_ONEFILE=0
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
python3 -m PyInstaller --noconfirm packaging/pyinstaller/LaserStudioPro.spec

echo "=========================================="
if [ "$MODE" = "--onefile" ]; then
    echo "Terminé ! L'exécutable dist/LaserStudioPro est prêt."
else
    echo "Terminé ! Le dossier dist/LaserStudioPro/ est prêt."
fi
echo "=========================================="
