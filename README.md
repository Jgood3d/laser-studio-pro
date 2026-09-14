Laser Studio Pro est un logiciel de pilotage pour graveuse/découpeuse laser GRBL, développé par un maker qui aime tester et bidouiller toutes sortes de projets. Il permet la gravure d'images (avec plusieurs algorithmes de tramage), la découpe et gravure de tracés vectoriels par calques, ainsi que la génération de matrices de test pour calibrer précisément puissance et vitesse selon le matériau.
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jb3dlaser)
# Laser Studio Pro — code découpé en modules

Ce dossier remplace `app.py` (3424 lignes) par 14 fichiers organisés par thème.
Fonctionnalité strictement identique — seul le découpage a changé (aucune
logique modifiée, uniquement déplacée).

## Comment lancer l'appli
Lancer **`main.py`** (au lieu de `app.py`). `vector_layers.py` reste inchangé
et doit rester dans le même dossier.

## Structure

**Point d'entrée**
- `main.py` — lance l'application (anciennement le bloc `if __name__ == "__main__"`)
- `app_utils.py` — `get_app_dir()` et `APP_VERSION`

**Classes autonomes**
- `graphics_view.py` — `ZoomableGraphicsView`
- `vector_font.py` — `VectorFont`
- `usb_controller.py` — `LaserUSBController`
- `workers.py` — tous les threads (`ImageProcessingWorker`, `GCodeStreamerThread`,
  `AdvancedGCodeWorker`, `CommandThread`, `TestMatrixWorker`) + fonctions de tramage

**Fenêtre principale, découpée en mixins** (tous partagent le même `self`,
donc le comportement est identique à avant — seul l'emplacement du code change) :
- `main_window.py` — classe `FullLaserStudio` : `__init__` + assemblage des mixins
- `ui_setup_mixin.py` — construction de l'UI, menu, boîtes de dialogue
- `machine_profiles_mixin.py` — profils machine / matériaux
- `image_processing_mixin.py` — chargement et traitement d'image
- `vector_editing_mixin.py` — édition des objets vectoriels (texte, formes, SVG)
- `gcode_generation_mixin.py` — génération, aperçu, estimation, export G-Code
- `laser_control_mixin.py` — USB/GRBL, streaming, commandes temps réel
- `project_io_mixin.py` — sauvegarde / chargement de projet (.json)

## Ce qui n'a pas changé
- Aucune ligne de logique métier n'a été réécrite : chaque méthode a été
  déplacée telle quelle (extraction automatisée par analyse du code, pas de
  retype manuel, pour éviter toute erreur de copie).
- Les imports ont été recalculés fichier par fichier (chaque module n'importe
  que ce dont il a besoin).
- Tous les fichiers ont été vérifiés avec `py_compile` (syntaxe correcte) et
  un script maison de détection de noms non définis, pour repérer les imports
  manquants — un cas réel a été trouvé et corrigé (`build_vector_layers_gcode`
  manquant dans `workers.py`).

## Pour bien tester
1. Vérifie que l'appli se lance et s'affiche normalement (`python main.py`).
2. Passe en revue chaque onglet/fonctionnalité une fois : image, calques
   vectoriels, génération G-Code, connexion USB, sauvegarde/chargement de
   projet — pour confirmer qu'aucun comportement n'a changé.
3. Comme `PyQt6`, `pyserial`, `pyqtgraph` et `svg.path` ne sont pas installés
   dans mon environnement, je n'ai pas pu lancer l'app moi-même ni tester le
   runtime — seule la syntaxe a été vérifiée de mon côté.
