# Instructions pour Claude (CLI / Code) - Laser Studio Pro

## Contexte du Projet
Application PyQt6 open-source en Python dédiée à la gravure laser, la découpe et la vectorisation d'images.

## Architecture des Modules
- `laser_studio_pro.py` : Point d'entrée principal de l'application graphique.
- `dxf_import.py` & `ui/widgets/zoomable_graphics_view.py` : Gestion de l'affichage vectoriel et des formats CAO.
- `box_generator.py` & `ui/dialogs/box_generator/` : Génération automatisée de boîtes et boîtiers de montage.
- `controllers/image.py` & `image/dithering.py` (tramage sans Qt), `image/filters.py` : Traitement de l'image à graver ; `image/vectorize.py` : vectorisation PNG/SVG.
- `controllers/engraver.py` & `grbl/commands.py` (communication) ; `gcode/` (génération sans Qt) & `controllers/job.py` : Communication et génération de G-code.

## Bonnes pratiques
- Avant toute modification, suivre le skill `contribuer` (`.claude/skills/contribuer/SKILL.md`) : dépôt mis à jour (git pull), code dans `src/`, découpage modèle / vue / contrôleur (pas de nouveau mixin), PEP 8, documentation à jour, vérifications avant le commit.
- Assurer la portabilité multi-plateforme (Linux Mint / Windows).

## Processus de Build & Déploiement
- **Scripts Batch (`packaging/windows/build.bat`) :** Utilisés pour packager l'application PyQt6 avec PyInstaller en s'assurant que toutes les dépendances binaires (OpenCV, PyQt6) et les fichiers de traduction (`en`, `fr`, `de`, `es`) sont inclus.
- **Installateurs :** Utilisation d'Inno Setup pour les packages Windows.
- **Optimisation Linux :** Création d'archives ou de paquets portables pour un démarrage rapide sous Linux Mint.

## Stratégie de Versioning
- Suivi strict des versions de Laser Studio Pro (ex: version actuelle autour de v2.5.0).
- Documentation des modifications majeures dans les commits et les releases GitHub (nouvelles fonctionnalités de découpe, modes stencils, etc.).