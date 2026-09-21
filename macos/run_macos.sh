#!/bin/bash
# Lance Laser Studio Pro depuis les sources sur macOS.
# Crée le venv et installe les dépendances si besoin, puis démarre l'appli.
# Ce script vit dans macos/ mais s'exécute depuis la racine du dépôt (où
# se trouve main.py), pour ne rien changer à l'arborescence Windows/Linux.
set -e

MACOS_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$MACOS_DIR")"
cd "$REPO_ROOT"

# Préfère Python 3.12 (version cible du projet) s'il est disponible
# (ex. via Homebrew), sinon retombe sur le python3 par défaut du système.
PYTHON_BIN="python3"
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
fi

if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel (${PYTHON_BIN})..."
    "$PYTHON_BIN" -m venv venv
fi

source venv/bin/activate

if [ ! -f "venv/.deps_installed" ] || [ "${MACOS_DIR}/requirements-macos.txt" -nt venv/.deps_installed ]; then
    echo "Installation des dépendances..."
    pip install --upgrade pip
    pip install -r "${MACOS_DIR}/requirements-macos.txt"
    touch venv/.deps_installed
fi

echo "Lancement de Laser Studio Pro..."
python main.py
