# Instructions pour Claude (CLI / Code) - Laser Studio Pro

## Contexte du Projet
Application PyQt6 open-source en Python dédiée à la gravure laser, la découpe et la vectorisation d'images.

## Architecture des Modules
- `laser_studio_pro.py` : Point d'entrée principal de l'application graphique.
- `dxf_import.py` & `graphics_view.py` : Gestion de l'affichage vectoriel et des formats CAO.
- `box_generator.py` & `box_dialog.py` : Génération automatisée de boîtes et boîtiers de montage.
- `image_processing_mixin.py` & `image_filters.py` : Traitement d'image et vectorisation PNG/SVG.
- `laser_control_mixin.py` & `gcode_generation_mixin.py` : Communication et génération de G-code.

## Bonnes pratiques
- Maintenir une structure modulaire via des mixins Python.
- Assurer la portabilité multi-plateforme (Linux Mint / Windows).

## Processus de Build & Déploiement
- **Scripts Batch (`build.bat`) :** Utilisés pour packager l'application PyQt6 avec PyInstaller en s'assurant que toutes les dépendances binaires (OpenCV, PyQt6) et les fichiers de traduction (`en`, `fr`, `de`, `es`) sont inclus.
- **Installateurs :** Utilisation d'Inno Setup pour les packages Windows.
- **Optimisation Linux :** Création d'archives ou de paquets portables pour un démarrage rapide sous Linux Mint.

## Stratégie de Versioning
- Suivi strict des versions de Laser Studio Pro (ex: version actuelle autour de v2.5.0).
- Documentation des modifications majeures dans les commits et les releases GitHub (nouvelles fonctionnalités de découpe, modes stencils, etc.).