# Laser Studio Pro & Stencil Studio - Instructions pour Gemini CLI

## Vue d'ensemble du projet
Laser Studio Pro (LSP) est une application bureau open-source développée en Python (PyQt6 et OpenCV) pour le pilotage, la découpe et la gravure laser. Elle intègre des modules de vectorisation (PNG vers SVG), de génération de boîtes paramétriques (`box_generator.py`) et Stencil Studio.

## Stack Technique
- **Langage :** Python 3.12+
- **Interface Graphique :** PyQt6 (`ui/widgets/zoomable_graphics_view.py`, `ui/dialogs/box_generator/`)
- **Traitement d'image :** OpenCV (`image_processing_mixin.py`, `image_filters.py`)
- **Contrôle Laser / G-code :** `laser_control_mixin.py`, `gcode_generation_mixin.py`
- **Build / Packaging :** PyInstaller, scripts batch (`packaging/windows/build.bat`)

## Commandes clés
- Lancer l'application : `python laser_studio_pro.py`
- Compiler l'exécutable : `packaging/windows/build.bat`

## Scripts de Build et Packaging
- **Compilation Windows (PyInstaller) :** `packaging/windows/build.bat` automatise la création de l'exécutable standalone et l'intégration des assets graphiques.
- **Gestion Linux / AppImage :** Scripts shell (`.sh`) et configuration AppImage pour optimiser le lancement sous Linux Mint.
- **Inno Setup :** Utilisation de scripts de setup pour générer les installateurs Windows automatisés.

## Gestion des Versions et du Code
- **Versioning :** Respect du versionnement sémantique (ex: v2.5.0 pour l'intégration des modes de découpe et de la light box).
- **Dépôt Git :** Synchronisation régulière avec GitHub, gestion des branches et résolution des conflits de dépendances Python/OpenCV.