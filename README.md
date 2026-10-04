# Laser Studio Pro

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jb3dlaser)

Laser Studio Pro est un logiciel de pilotage GRBL pour graveur et découpeuse laser, avec :
- gravure d’images (tramage, niveaux de gris, résolution liée à la taille du spot),
- sélecteur de matière (fond noir / fond clair) pour graver en négatif ou en positif,
- séparation couleur / verre (calque noir à graver, calque couleur à imprimer, simulation du rétro-éclairage, PDF à l’échelle 1:1),
- découpe/gravure vectorielle et conversion PNG/JPEG → SVG,
- gestion de calques, avec leurs réglages mémorisés par machine,
- génération et aperçu 2D du G-Code, file d’attente de jobs,
- profils machine (dimensions, focale, réglages GRBL, matériaux),
- export/import de projets, sauvegarde automatique,
- support multilingue (Français, English, Deutsch, Español).

L’historique détaillé des versions est dans [`CHANGELOG.md`](CHANGELOG.md).

## Installation

Python 3 est requis. Installez les dépendances selon votre système :

```bash
pip install -r requirements-windows.txt    # Windows
pip install -r requirements-linux.txt      # Linux
```

`numba` est optionnel : il accélère le tramage, l’application fonctionne sans.
Sous Linux, l’utilisateur doit appartenir au groupe `dialout` pour accéder au port série.

## Lancer l’application

Lancez `main.py` depuis le dossier du projet.

```bash
python main.py
```

## Structure du projet

### Point d’entrée
- `main.py` — lance l’application
- `app_utils.py` — version de l’application, chemins de ressources, écriture atomique des fichiers de données

### Composants autonomes
- `graphics_view.py` — `ZoomableGraphicsView`
- `vector_font.py` — `VectorFont`
- `vector_layers.py` — calques et objets vectoriels, canevas de l’éditeur
- `usb_controller.py` — `LaserUSBController`
- `workers.py` — threads et fonctions de traitement image / G-Code
- `widgets_extra.py` — petits widgets réutilisables (historique de commandes, libellé à masquage automatique)
- `separation_engine.py` — calculs de séparation couleur / verre (sans Qt)
- `png2svg_widget.py` — widget de conversion PNG/JPEG → SVG (utilise le module `converter`)
- `i18n.py` — système de traduction multilingue

### Fenêtre principale découpée en mixins
- `main_window.py` — assemblage de la fenêtre principale
- `ui_setup_mixin.py` — interface utilisateur, menus, onglets, dialogues
- `machine_profiles_mixin.py` — profils machine / matériaux / réglages de calques par machine
- `image_processing_mixin.py` — chargement et traitement d’image, matière
- `vector_editing_mixin.py` — éditeur vectoriel et SVG
- `gcode_generation_mixin.py` — génération, aperçu et export G-Code
- `laser_control_mixin.py` — USB / GRBL / commandes temps réel
- `project_io_mixin.py` — sauvegarde et ouverture de projet, sauvegarde automatique
- `job_queue_mixin.py` — file d’attente de jobs
- `png2svg_mixin.py` — onglet PNG/JPEG → SVG
- `separation_mixin.py` — onglet Séparation Couleur / Verre

### Qualité
- `tests/` — tests automatiques (G-Code, écriture atomique, reset/référencement, calques par machine, traductions)
- `tools/check_translations.py` — rapport sur les traductions (clés inutilisées, textes en dur, registre tu/vous)

## Captures d’écran

<img width="1907" height="1005" alt="Tramage" src="https://github.com/user-attachments/assets/42ae3b7c-7740-4c4c-a704-d3b78d4d36ab" />

<img width="1919" height="1035" alt="Apercu tramages" src="https://github.com/user-attachments/assets/320160f2-a7c1-47b1-9626-cc1c96f9ae1d" />

<img width="3258" height="1830" alt="655698064-05eeca85-b211-4a80-817a-aea536a2c92c" src="https://github.com/user-attachments/assets/e6796d7b-6238-44d2-b888-1afc7ba696b0" />

Conversion PNG → SVG :

<img width="1511" height="641" alt="Test svg" src="https://github.com/user-attachments/assets/0a68799f-e198-4044-b051-a263d4755464" />

Déplacement d’un SVG sur le plan de travail :

<img width="340" height="357" alt="Déplacement" src="https://github.com/user-attachments/assets/01d1e7df-ed98-4724-8aee-4857904e19cc" />

Interface en anglais et en allemand :

<img width="1918" height="1010" alt="English" src="https://github.com/user-attachments/assets/eaa4c939-b36d-4588-8538-12aa54dc01ea" />

<img width="1910" height="1008" alt="Allemand" src="https://github.com/user-attachments/assets/20f4c90a-8f35-44aa-b372-c88be354859c" />

## Nouveautés de la version 2.2.0

- **Sélecteur « Matière »** (Image / Filtres) : fond noir ou fond clair, qui coche ou décoche « Inverser Couleurs » ; la matière est rappelée dans l’alerte avant gravure et enregistrée dans le projet.
- **Réglages des calques mémorisés par machine** : vitesse, puissance, passes… retrouvés à la réouverture, propres à chaque profil machine.
- **Séparation Couleur / Verre** : calque noir, calque couleur, simulation et PDF d’impression à l’échelle 1:1.
- **Correction importante de la gravure d’image** : le G-Code appliquait la puissance au mauvais segment ; régénérez les G-Codes d’image créés avec une version antérieure.
- **Reset / arrêt d’urgence** : le statut « référencé » est retiré si la machine n’était pas à l’arrêt, un nouveau homing est demandé.
- **Sauvegardes atomiques** (autosave, file d’attente, projet) : plus de fichier tronqué en cas de plantage.

Voir [`CHANGELOG.md`](CHANGELOG.md) pour le détail et les versions précédentes.

## Compilation (PyInstaller)

Les ressources suivantes sont cherchées à côté de l’exécutable puis dans le bundle PyInstaller : `laser_studio_pro.ico` (ou `laser_studio_pro_256.png` / `laser_studio_pro_512.png`), `laser_studio_pro_banner.png` et `buy_me_a_coffee.png`. Pour les embarquer, ajoutez `--add-data "fichier;."` (Windows) ou `--add-data "fichier:."` (Linux) à la commande PyInstaller. Supprimez `build/`, `dist/` et `LaserStudioPro.spec` avant de recompiler pour que les nouvelles ressources soient prises en compte.

## Développement / validation

Vérifier la syntaxe Python :

```bash
py -m py_compile i18n.py ui_setup_mixin.py main_window.py
```

Lancer les tests automatiques (bibliothèque standard uniquement, aucune dépendance supplémentaire) :

```bash
python -m unittest discover tests -v
```

Contrôler les traductions (rapport détaillé) :

```bash
python tools/check_translations.py
```

## Remerciements

Merci à toutes les personnes qui contribuent au projet, testent les fonctionnalités et signalent les bugs.

## Licence

Voir le fichier `LICENSE` associé au dépôt si présent.
