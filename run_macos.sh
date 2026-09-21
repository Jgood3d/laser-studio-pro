#!/bin/bash
# Lance Laser Studio Pro depuis les sources sur macOS.
# Crée le venv et installe les dépendances si besoin, puis démarre l'appli.
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f "venv/.deps_installed" ] || [ requirements-macos.txt -nt venv/.deps_installed ]; then
    echo "Installation des dépendances..."
    pip install --upgrade pip
    pip install -r requirements-macos.txt
    touch venv/.deps_installed
fi

echo "Lancement de Laser Studio Pro..."
python main.py
