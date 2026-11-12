# Laser Studio Pro

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jb3dlaser)

Laser Studio Pro est un logiciel de pilotage GRBL pour graveur et découpeuse laser, avec :
- gravure d’images (tramage, niveaux de gris, résolution liée à la taille du spot),
- sélecteur de matière (fond noir / fond clair) pour graver en négatif ou en positif,
- séparation couleur / verre (calque noir à graver, calque couleur à imprimer, simulation du rétro-éclairage, PDF à l’échelle 1:1),
- découpe/gravure vectorielle, import SVG et DXF, conversion PNG/JPEG → SVG,
- générateur de boîte à encoches (dimensions X/Y/Z, décor texte ou SVG),
- gestion de calques, avec leurs réglages mémorisés par machine,
- calibrage guidé : matrice de test, décalage aller/retour et gain de point pour le verre,
- génération et aperçu 2D du G-Code, file d’attente de jobs,
- profils machine (dimensions, focale, réglages GRBL, matériaux),
- export/import de projets, sauvegarde automatique,
- support multilingue (Français, English, Deutsch, Español).

L’historique détaillé des versions est dans [`CHANGELOG.md`](CHANGELOG.md).

## Installation

Python 3.11 ou 3.12 est requis (voir [Python 3.12](#python-312) si votre distribution fournit une version plus récente). Installez les dépendances selon votre système :

```bash
pip install -r requirements-windows.txt    # Windows
pip install -r requirements-linux.txt      # Linux
```

`numba` est optionnel : il accélère le tramage, l’application fonctionne sans.
Sous Linux, l’utilisateur doit appartenir au groupe `dialout` pour accéder au port série. Ajoutez-le au groupe :

```bash
sudo usermod -aG dialout $USER
```

Fermez puis rouvrez la session pour que l’appartenance au groupe soit prise en compte (vérifiez ensuite avec `groups`).

### Python 3.12

Les dépendances imposent `numpy<2.0.0` (compatibilité PyInstaller, pyqtgraph et numba). Or numpy 1.26, dernière version de cette branche, ne fonctionne pas au-delà de Python 3.12 : avec Python 3.13 ou 3.14, l’installation de numpy échoue. Les distributions récentes (Fedora 41+, Debian 13, Ubuntu 25.04+) fournissent par défaut une version trop récente ; installez donc Python 3.12 à côté de celle du système, sans la remplacer.

Vérifiez d’abord la version disponible :

```bash
python3 --version
python3.12 --version
```

**Fedora** — Python 3.12 est disponible dans les dépôts officiels :

```bash
sudo dnf install python3.12
```

**Ubuntu** — Ubuntu 24.04 fournit Python 3.12 par défaut, il suffit d’ajouter le module `venv` :

```bash
sudo apt install python3.12 python3.12-venv
```

Sur les autres versions LTS (22.04 par exemple), passez par le PPA deadsnakes :

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

**Debian** — aucune version de Debian ne fournit Python 3.12 dans ses dépôts (3.11 pour Debian 12, 3.13 pour Debian 13). Sous Debian 12, Python 3.11 convient :

```bash
sudo apt install python3 python3-venv
```

Sous Debian 13 (ou sur toute distribution sans paquet Python 3.12), utilisez [uv](https://docs.astral.sh/uv/), qui télécharge un Python 3.12 autonome dans le dossier de l’utilisateur :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

### Installation dans un environnement virtuel (recommandé)

Un environnement virtuel isole les dépendances du projet de celles du système. Depuis le dossier du projet, créez-le avec Python 3.12, activez-le puis installez les dépendances :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-linux.txt
```

Sous Debian 12, remplacez `python3.12` par `python3` (Python 3.11). Avec uv, créez l’environnement par `uv venv --python 3.12 --seed .venv` (`--seed` y installe `pip`), puis activez-le et installez les dépendances de la même façon.

> **Note** : créez l’environnement avec `python3.12` et non `python3`. Un environnement créé avec la version du système (3.13 ou 3.14) ne pourra pas installer numpy, et un environnement mélangeant deux versions provoque l’erreur `ModuleNotFoundError: No module named 'PyQt6'` alors que PyQt6 est installé. En cas de doute, supprimez `.venv` et recréez-le.

L’environnement doit être activé (`source .venv/bin/activate`) dans chaque nouveau terminal avant de lancer l’application. Pour en sortir, utilisez `deactivate`.

## Lancer l’application

Lancez `main.py` depuis le dossier du projet.

```bash
source .venv/bin/activate
python main.py
```

## Structure du projet

Le code suit la disposition `src/` recommandée pour les projets Python (voir `pyproject.toml`) :
- `src/laser_studio/` — l’application Laser Studio ; les chemins ci-dessous lui sont relatifs ;
- `src/laser_common/` — code partagé par Laser Studio et Stencil Studio, indépendant des deux (`files.py` : écriture sûre des fichiers de données) ;
- `stencil_studio/` — Stencil Studio (rejoindra `src/` plus tard) ;
- `tests/`, `tools/`, `packaging/`, `docs/` à la racine du dépôt.

On lance l’application avec `python main.py` depuis le dépôt, ou `python -m laser_studio` après `pip install -e .`.

### Point d’entrée
- `main.py` (racine du dépôt) — lance l’application sans installation ; `main.py` dans `src/laser_studio/` contient le démarrage (`main()`)
- `core/` — socle sans interface : `version.py` (version de l’application), `paths.py` (chemins, ressources), `constants.py` (valeurs fixes : liens, tailles), `debug_log.py` (journal de débogage de la gravure)

### Composants autonomes
- `vector_layers.py` — calques et objets vectoriels, canevas de l’éditeur
- `grbl/` — dialogue avec le graveur, sans Qt : `connection.py` (`LaserUSBController`, connexion série) et `simulator.py` (`SimulatedGrblSerial`, graveur simulé de `LASER_STUDIO_SIMULATION`)
- `workers.py` — threads et fonctions de traitement image / G-Code
- `ui/widgets/` — petits widgets réutilisables : `ZoomableGraphicsView`, `HistoryLineEdit` (historique de commandes), `AutoHideLabel` (libellé à masquage automatique), `FloatingToolBar` (barre flottante en haut d’un aperçu : annuler / refaire, pivoter, miroirs), `TabCloseButton` (croix d’un onglet), `TabToolBar` (barre d’outils d’un onglet, avec le bouton « Plein écran »), `FullscreenWindow` (fenêtre « Plein écran » qui accueille un onglet), `SliderWithButtons` (curseur entre deux boutons « - » / « + », avec sa valeur)
- `ui/utils.py` — utilitaires partagés par les éléments d’interface (icônes dessinées, images nettes en haute résolution)
- `ui/splashscreen/` — `StartupSplash`, écran de démarrage (affichage réel sous Wayland, durée minimale)
- `ui/app/qt_messages.py` — filtre des avertissements de Qt sans conséquence (Wayland)
- `ui/app/theme.py` — thèmes de l’interface (sombre, clair, Dusk, Warm : palette et feuille de style), pack d’icônes Breeze embarqué
- `image/` — traitement d’image sans Qt : `filters.py` (netteté), `size.py` (taille d’origine d’après la résolution), `matrix.py` (matrice de test à partir d’une image), `separation.py` (calculs de séparation couleur / verre), `vectorize.py` (conversion PNG/JPEG → SVG)
- `vector/` — géométrie vectorielle :
  - `vector/order.py` — ordre de découpe sûr (gravure avant découpe, intérieur avant extérieur)
  - `vector/nesting.py` — imbrication automatique des pièces sur une feuille (sans Qt) ; `vector/nesting_apply.py` place le résultat sur le canevas
  - `vector/nudge.py` — pas de déplacement aux flèches du clavier (sans Qt)
  - `vector/dxf.py` — lecteur DXF texte (sans Qt, sans dépendance)
  - `vector/box_generator.py` — calcul des panneaux d’une boîte à encoches (sans Qt)
  - `vector/importers.py` — passerelle vers les objets de l’éditeur vectoriel (DXF, boîte, décor)
  - `vector/font.py` — `VectorFont`, police vectorielle des étiquettes texte
- `i18n/` — système de traduction multilingue : `translations.py` (les textes dans chaque langue), `language.py` (langue choisie, `tr()`)

### Fenêtre principale découpée en mixins
- `main_window.py` — fenêtre principale : construction (`init_ui`), branchement des signaux des panneaux, fermeture, glisser-déposer, tailles des séparateurs, onglet « Éditeur vectoriel » (partira dans `ui/tabs/`)
- `ui/statusbar/` — barre d’état (`StatusBar` : messages d’information, progression de la génération)
- `ui/app/menu/` — menu et barre d’outils : `AppActions` (toutes les actions et leurs signaux), `AppMenuBar` et un fichier par menu (Fichier, Paramètres, Affichage, Outils, Aide), `AppToolBar`
- `ui/app/window_controller.py` — contrôleur de la fenêtre : abonnement aux signaux du menu et de la barre d’outils, thème, langue, onglets annexes, état de la connexion
- `ui/about/` — boîte « À propos » (`AboutDialog`, `AboutBannerPixmap`, `AboutLabel`)
- `ui/support/` — boîte « Support » (`SupportDialog`, `SupportLabel`)
- `ui/buy_me_a_coffee/` — boîte « Buy me a coffee » (`BuyMeACoffeeDialog`, `BuyMeACoffeeLabel`) et bouton ko-fi de la barre d’outils (`BuyMeACoffeeButton`)
- `ui/machine/` — `MachinePanel`, panneau machine sous les onglets : assemble le G-Code envoyé, la connexion, le pilotage et les actions de job, puis la barre de progression ; `set_status(état, x, y, z)` répartit l’état (cadre Connexion) et la position (sous le pilotage)
- `ui/machine/connection/` — panneau « Connexion » `ConnectionPanel` : port (modèle partagé avec la page des matériaux), actualisation, connexion, état GRBL et console directe (émet `refresh_requested`, `connect_requested`, `unlock_requested`, `command_submitted`)
- `ui/machine/status/` — `MachineStateView` (état GRBL coloré, « Déverrouiller » en alarme) et `AxisPositionRow` (X / Y / Z sur une ligne, sous le pilotage)
- `ui/machine/controls/` — panneau de pilotage `JogControlPanel` : jog, homing, curseurs de pas et de vitesse, commandes temps réel, envoi du job (émet des signaux) ; les commandes temps réel et l’envoi du job sont `RealtimeCommands`
- `ui/machine/job_actions/` — panneau `JobActionsPanel` : cadrage, zéro, aller au zéro, répétition (émet des signaux ; accueillera les macros)
- `ui/machine/console/` — console directe `DirectConsolePanel` (sans cadre, dans le panneau Connexion) : commande GRBL tapée à la main, historique (émet `command_submitted`)
- `ui/settings/machine_params/` — page « Paramètres du graveur » `MachineParamsPage` : profils machine, lit, spot, limites (émet `focal_changed`, `bed_size_changed`…)
- `ui/settings/machine_profiles/` — page « Matériaux et connexion au graveur » `MachineProfilesPage` : port, connexion, matériaux (émet `connect_requested`…, reçoit `set_connected`)
- `ui/settings/grbl_config/` — page « Configuration GRBL » `GrblConfigPage` : commande laser, surbalayage, décalage aller/retour, G-Code de début et de fin, réglages GRBL complets (émet `read_settings_requested`, `scan_offset_changed`…) ; le cadre « Réglages GRBL complets » est `GrblSettingsBox`
- `ui/settings/test_matrix/` — page « Matrice de test » `TestMatrixPage` : réglages de la grille, test à partir d’une image avec l’aperçu `TilePicker` (émet `generate_requested`…, fournit `matrix_params()`) ; le cadre « Test à partir d’une image » est `ImageTestGroup`
- `ui/tabs/image/` — onglet « Graver une image » `ImageTab` : réglages `ImageSettingsPanel` (taille et décalage, réglages photo, matière `MaterialComboBox`, tramage, résolution `ResolutionBox`), aperçus originale / tramé (émet `compare_requested` ; le panneau émet `processing_changed`, `size_changed`…)
- `ui/machine/job_position/` — cadre « Position du job » `JobPositionBox` (origine du repère, `origin()` / `set_origin()`), à droite de l’aperçu 2D
- `ui/machine/sent_gcode/` — suivi du G-Code envoyé `SentGcodeLog` (file et envoi direct), à gauche du panneau machine
- `ui/tabs/png2svg/` — onglet « Vectorisation d’image » `Png2SvgTab` : widget de conversion PNG/JPEG → SVG `PngToSvgWidget` (utilise le module `converter`) et son aperçu `ZoomableSvgView` (émet `send_to_vector_requested`, `image_changed`)
- `ui/tabs/separation/` — onglet « Séparation Couleur / Verre » `SeparationTab` : plaque, recadrage, calques noir et couleur, simulation, aperçus, glisser-déposer (émet `tone_changed`, `preview_changed`, `image_dropped`…)
- `ui/tabs/preview_2d/` — onglet « Visualisation 2D G-Code » `Preview2DTab` : graphique où la génération dessine le G-Code, point de position de la tête, options d’affichage (émet `plot_clicked` en mm, `display_options_changed`), et à droite une colonne étroite : `JobPositionBox`, puis `JobStatsPanel` : lignes, puissance moyenne et temps estimé du job (`set_stats`)
- `ui/tabs/console/` — onglet « Console / G-Code » `ConsoleTab` : console du G-Code généré ou importé (les messages vont dans la barre d’état) ; affiché ou masqué par le menu Affichage ou sa croix (`TabCloseButton`), choix mémorisé
- `ui/tabs/job_queue/` — onglet « File d’attente » `JobQueueTab` (affiché ou masqué par le menu Affichage, le bouton de la barre d’outils ou sa croix, choix mémorisé) : jobs à enchaîner (émet `run_requested`, `reordered`…) ; le G-Code envoyé est suivi dans le panneau machine (`SentGcodeLog`)
- `ui/tabs/layers/` — onglet « Calques » `LayersTab` : enveloppe la liste des calques (`LayerManagerWidget`, encore dans `vector_layers.py`) et relaie `layers_changed`
- `image_processing_mixin.py` — chargement et traitement d’image, matière
- `vector_editing_mixin.py` — éditeur vectoriel et SVG
- `gcode_generation_mixin.py` — génération, aperçu et export G-Code
- `laser_control_mixin.py` — USB / GRBL / commandes temps réel
- `controllers/` — contrôleurs, objets Python ordinaires qui remplacent peu à peu les mixins : `png2svg.py` (`Png2SvgController` : SVG de l’onglet PNG→SVG vers l’éditeur vectoriel), `matrix_image.py` (`MatrixImageController` : matrice de test à partir d’une image), `job_queue.py` (`JobQueueController` : file d’attente de jobs, et `Engraver`, ce que la file demande au graveur), `machine_profiles.py` (`MachineProfilesController` : profils machine, leurs actions et la mémoire continue des calques ; chaque page fournit ses champs par `profile_values()` / `apply_profile_values()`), `layer_memory.py` (mémoire des calques par machine : réglages des calques enregistrés dans chaque profil et réappliqués, sans Qt), `materials.py` (`MaterialsController` : profils matériaux, et la liste par défaut `DEFAULT_MATERIALS_DB`), `project.py` (`ProjectController` : enregistrement et ouverture de projet, projets récents, sauvegarde automatique ; l’état du projet est lu et réappliqué par la fenêtre, `_capture_project` / `_restore_project`)
- `separation_mixin.py` — logique de l’onglet Séparation Couleur / Verre : tonalité envoyée à « Graver une image », calque couleur, aperçus, export, test du gain
- `ui/dialogs/box_generator/` — fenêtre du générateur de boîte `BoxGeneratorDialog`
- `nesting_apply.py`, `ui/dialogs/nesting/` — imbrication dans l’éditeur vectoriel (passerelle, et fenêtre de réglage `NestingDialog`)
- `ui/dialogs/dither_comparison/` — fenêtre de comparaison des algorithmes de tramage `DitherComparisonDialog` (vignettes calculées par `ImageProcessingMixin.compare_dither_algorithms`)
- `ui/settings/window.py` — `SettingsWindow`, fenêtres « Paramètres du graveur », « Matériaux et connexion au graveur » et « Configuration GRBL » ouvertes depuis le menu Paramètres

### Signaux des pages et des panneaux

Les pages, onglets et panneaux de `ui/` ne contiennent pas de logique : ils émettent des signaux (ce que l’utilisateur demande, avec des valeurs métier : mm, mm/min, %), et reçoivent leur état par des méthodes `set_…`. La fenêtre (`main_window.py`) les construit et abonne la logique à leurs signaux.

Nommage : un signal de demande `x_requested` appelle la fonction `x()` (`save_project_requested` → `save_project`, `emergency_stop_requested` → `emergency_stop`) ; un signal d’état `y_changed` ou `y_selected` appelle `_on_y_changed()` ou une fonction qui dit ce qu’elle fait (`profile_selected` → `_on_machine_profile_selected`). La carte `docs/architecture/signaux.png` (`tools/signal_map.py`) montre toutes les paires.

**Pages de réglages** (menu Paramètres, `ui/settings/`) :

| Page | Signaux émis | État reçu / lu |
| --- | --- | --- |
| `MachineParamsPage` — Paramètres du graveur | `profile_selected(int)`, `new_profile_requested`, `update_profile_requested`, `delete_profile_requested`, `bed_size_changed(largeur_mm, profondeur_mm)`, `focal_changed(spot_mm)`, `max_speed_changed(mm_min)` | champs `profile_combo`, `bed_width_spin`, `bed_height_spin`, `focal_spin`, `max_speed_spin`, `accel_spin` |
| `MachineProfilesPage` — Matériaux et connexion au graveur | `port_selected(int)`, `refresh_ports_requested`, `connect_requested`, `material_selected(int)`, `save_material_requested`, `new_material_requested`, `delete_material_requested`, `export_materials_requested`, `import_materials_requested` | `set_connected(bool)`, `set_port_index(int)` |
| `TestMatrixPage` — Matrice de test | `generate_requested`, `choose_image_requested`, `use_loaded_image_requested`, `image_test_toggled(bool)` | `set_lines_mm()`, `set_source_image()`, `set_image_test_checked()` ; fournit `matrix_params()`, `tile_settings()`, `is_engraving()`, `image_test_enabled()` |
| `GrblConfigPage` — Configuration GRBL | `bidir_test_requested`, `scan_offset_changed(mm)`, `read_settings_requested`, `send_settings_requested`, `export_settings_requested`, `import_settings_requested`, `link_settings_to_profile_requested` | champs `laser_cmd_combo`, `smax_spin`, `homing_check`, `overscan_check`, `overscan_mode_combo`, `scan_offset_spin`, `grbl_settings_edit`… |

**Onglets** (`ui/tabs/`, et la barre d’outils commune `TabToolBar`) :

| Onglet | Signaux émis | État reçu / lu |
| --- | --- | --- |
| `TabToolBar` — barre d’outils d’un onglet | `fullscreen_requested` | `fullscreen_action` (bouton masqué en plein écran) |
| `ImageTab` — Graver une image | `compare_requested`, `fullscreen_requested` | `settings` (le panneau ci-dessous), `source_view`, `dither_view`, `fit_settings_width()` |
| `ImageSettingsPanel` — réglages de « Graver une image » | `load_requested`, `processing_changed`, `material_changed("dark" / "light")`, `size_changed(axe, mm)`, `resolution_mode_changed(int)`, `lines_per_mm_changed(float)`, `dpi_changed(float)`, `configure_focal_requested`, `save_as_focal_requested`, `undo_requested`, `redo_requested` | champs `width_spin`, `height_spin`, `brightness_slider`, `algorithm_combo`, `lines_per_mm_spin`, `resolution_stack`… |
| `Png2SvgTab` — Vectorisation d’image | `send_to_vector_requested(svg)`, `image_changed`, `fullscreen_requested` | `converter` (widget de conversion : `image_path`, `rotate_image()`, `clear_image()`) |
| `LayersTab` — Calques | `layers_changed` | `refresh()`, `refresh_focal_quality()`, `link_all_to_focal()` |
| `Preview2DTab` — Visualisation 2D G-Code | `display_options_changed`, `plot_clicked(x_mm, y_mm)`, `fullscreen_requested` | `plot_widget` (la génération y dessine), `position_marker`, cases `flip_check`, `negative_check`, `hide_rapid_check`, `optimize_path_check` |
| `ConsoleTab` — Console / G-Code | `export_requested(extension)`, `fullscreen_requested` | `set_stats(lignes, puissance, temps)`, `console_edit` |
| `JobQueueTab` — File d’attente | `add_current_requested`, `remove_selected_requested`, `clear_requested`, `run_requested`, `reordered` | `add_job()`, `set_jobs()`, `job_names()`, `set_status()`, `set_run_enabled()` |

**Panneau machine** (sous les onglets, `ui/machine/`) :

| Panneau | Signaux émis | État reçu |
| --- | --- | --- |
| `JogControlPanel` — pilotage, position X / Y / Z en bas | `jog_requested(dx_mm, dy_mm, vitesse_mm_min)`, `home_requested`, `pause_requested`, `resume_requested`, `reset_requested`, `emergency_stop_requested`, `send_job_requested` | `set_connected(bool)`, `set_send_enabled(bool)`, `set_max_speed(mm_min)`, `set_position(x, y, z)` |
| `JobActionsPanel` — actions de job | `frame_requested`, `set_work_zero_requested`, `go_to_work_zero_requested`, `repeat_job_requested` | `set_connected(bool)`, `set_repeat_enabled(bool)` |
| `ConnectionPanel` — connexion, état GRBL, console directe | `refresh_requested`, `connect_requested`, `unlock_requested`, `command_submitted(commande)` | `set_connected(bool)`, `set_state(état)`, `ports_combo` |
| `DirectConsolePanel` — console directe (dans Connexion) | `command_submitted(commande)` | `set_connected(bool)` |
| `JobPositionBox` — position du job (à droite de l’aperçu 2D) | (aucun : l’origine est lue à la génération) | `origin()`, `set_origin(code)` |
| `SentGcodeLog` — G-Code envoyé | (aucun) | `clear_lines()`, `append_lines(lignes)`, `mark_end(terminé)` |
| `MachinePanel` — assemble les panneaux ci-dessus | (ceux de ses panneaux) | `set_connected(bool)`, `set_status(état, x, y, z)` |

**Boîtes et fenêtres** (`ui/dialogs/`, `ui/widgets/`) :

| Fenêtre | Signaux émis | État reçu |
| --- | --- | --- |
| `DitherComparisonDialog` — comparaison des algorithmes de tramage | `algorithm_chosen(nom)` | vignettes tramées, à la construction |
| `FullscreenWindow` — plein écran d’un onglet | `content_released` (le contenu retourne dans les onglets) | le contenu, à la construction ; `show_maximized()` |

Le menu et la barre d’outils de la fenêtre passent par `AppActions` (`ui/app/menu/actions.py`), qui émet un signal par action : `save_project_requested`, `settings_window_requested(page)`, `theme_selected(code)`, `generate_requested`, `gcode_export_requested(extension)`, `gcode_console_toggled(bool)`, `puzzle_generator_requested`…

### Qualité
- `tests/` — tests automatiques (G-Code, fin de job, calibrage, séparation couleur/verre, sauvegardes, reset/référencement, calques par machine, traductions)
- `tools/check_translations.py` — rapport sur les traductions (clés inutilisées, textes en dur, registre tu/vous)
- `tools/check_ui_attributes.py` — détecte les widgets utilisés mais jamais construits (fichier resté à l’ancienne version)
- `tools/signal_map.py` — carte des signaux (qui émet quoi, qui branche, quelle fonction s’exécute), dans `docs/architecture/signaux.svg` et `.png`
- `tools/screenshots.py` — captures d’écran de tous les onglets, pages de réglages et boîtes de dialogue, dans `docs/screenshots/`

## Captures d’écran

<img width="1907" height="1005" alt="Tramage" src="https://github.com/user-attachments/assets/42ae3b7c-7740-4c4c-a704-d3b78d4d36ab" />

<img width="1919" height="1035" alt="Apercu tramages" src="https://github.com/user-attachments/assets/320160f2-a7c1-47b1-9626-cc1c96f9ae1d" />

<img width="2000" height="1562" alt="gravure-test-4" src="https://github.com/user-attachments/assets/077c3e41-736d-414b-bb28-54e01048cbe3" />

Conversion PNG → SVG :

<img width="1511" height="641" alt="Test svg" src="https://github.com/user-attachments/assets/0a68799f-e198-4044-b051-a263d4755464" />

Déplacement d’un SVG sur le plan de travail :

<img width="340" height="357" alt="Déplacement" src="https://github.com/user-attachments/assets/01d1e7df-ed98-4724-8aee-4857904e19cc" />

Interface en anglais et en allemand :

<img width="1918" height="1010" alt="English" src="https://github.com/user-attachments/assets/eaa4c939-b36d-4588-8538-12aa54dc01ea" />

<img width="1910" height="1008" alt="Allemand" src="https://github.com/user-attachments/assets/20f4c90a-8f35-44aa-b372-c88be354859c" />

## Nouveautés de la version 2.4.0

- **Imbrication automatique** : range les pièces sur une feuille pour gaspiller le moins de matière possible (rotations, écart, marge, emboîtement dans les creux ; les trous et détails suivent leur pièce).
- **Ordre de découpe sûr** : graver avant de découper, et couper l’intérieur avant l’extérieur, pour qu’une pièce ne bouge pas avant que ses détails soient faits.
- **Netteté** dans les réglages photo : accentue les contours avant le tramage.
- **Menus de réglages** (Paramètres Machine, Machine & Profils, Configuration GRBL, Matrice de test), **image insérée à sa taille d’origine**, **flèches du clavier** dans l’éditeur vectoriel et homing automatique activé par défaut.
- **Remplissage vectoriel corrigé** : plus de vides aux croisements de traits, et le décalage aller/retour s’applique aussi aux remplissages (contours moins en escalier).

Précédemment, dans la version 2.3.0 :

- **Import DXF** dans l’éditeur vectoriel (lignes, polylignes, cercles, arcs, ellipses, splines, blocs), avec réunion automatique des segments en contours.
- **Générateur de boîte à encoches** : panneaux prêts à découper, avec décor texte ou SVG gravé sur les faces.
- **Décalage aller/retour** : corrige le flou des contours verticaux de la gravure d’image, avec un motif de test pour trouver la bonne valeur (mémorisée par machine).
- **Assistant de calibrage du gain de point** pour la gravure sur verre : une grille à graver pour régler le curseur au bon endroit.
- **Fin de job fiable** : l’application attend que la machine soit réellement à l’arrêt (état Idle), et un Reset n’est plus annoncé comme une fin normale.
- **Sauvegardes en arrière-plan** : l’autosave et la file d’attente ne figent plus l’interface.
- **Boîtes de dialogue de l’éditeur vectoriel traduites**, et tutoiement harmonisé dans toutes les langues.

Précédemment, dans la version 2.2.0 :

- **Sélecteur « Matière »** (Image / Filtres) : fond noir ou fond clair, qui coche ou décoche « Inverser Couleurs » ; la matière est rappelée dans l’alerte avant gravure et enregistrée dans le projet.
- **Réglages des calques mémorisés par machine** : vitesse, puissance, passes… retrouvés à la réouverture, propres à chaque profil machine.
- **Séparation Couleur / Verre** : calque noir, calque couleur, simulation et PDF d’impression à l’échelle 1:1.
- **Correction importante de la gravure d’image** : le G-Code appliquait la puissance au mauvais segment ; régénérez les G-Codes d’image créés avec une version antérieure.
- **Reset / arrêt d’urgence** : le statut « référencé » est retiré si la machine n’était pas à l’arrêt, un nouveau homing est demandé.
- **Sauvegardes atomiques** (autosave, file d’attente, projet) : plus de fichier tronqué en cas de plantage.

Voir [`CHANGELOG.md`](CHANGELOG.md) pour le détail et les versions précédentes.

## Compilation (PyInstaller)

Les scripts de compilation sont dans `packaging/` : `windows/build.bat` (et `windows/setup.iss` pour l’installateur), `linux/build-linux.sh` et `macos/build_macos.sh`. Le détail est dans [`BUILD.md`](BUILD.md).

Les images de l’application sont dans le dossier `resources/` : `laser_studio_pro.ico` (ou `laser_studio_pro_256.png` / `laser_studio_pro_512.png`), `laser_studio_pro_banner.png` et `buy_me_a_coffee.png`, ainsi que le pack d’icônes Breeze (`icons/breeze/`, utilisé quand le système n’a pas de thème d’icônes). Elles sont cherchées dans `resources/` à côté de l’exécutable (ou directement à côté, ancien emplacement), puis dans le bundle PyInstaller. Pour les embarquer, ajoutez `--add-data "resources;resources"` (Windows) ou `--add-data "resources:resources"` (Linux) à la commande PyInstaller. Supprimez `build/`, `dist/` et `LaserStudioPro.spec` avant de recompiler pour que les nouvelles ressources soient prises en compte.

## Développement / validation

Vérifier la syntaxe Python :

```bash
py -m py_compile src/laser_studio/i18n/translations.py src/laser_studio/main_window.py
```

Lancer les tests automatiques (bibliothèque standard uniquement, aucune dépendance supplémentaire) :

```bash
python -m unittest discover tests -v
```

Vérifier qu’aucun widget n’est utilisé sans être construit (utile après avoir remplacé plusieurs fichiers) :

```bash
python tools/check_ui_attributes.py
```

Contrôler les traductions (rapport détaillé) :

```bash
python tools/check_translations.py
```

Régénérer la carte des signaux après un changement de l’interface (`--list` pour la version texte) :

```bash
python tools/signal_map.py
```

Refaire les captures d’écran (les fenêtres s’ouvrent quelques secondes ; `--offscreen` pour capturer sans écran, sans emojis ni icônes du système) :

```bash
python tools/screenshots.py
```

### Variables d’environnement

| Variable | Effet |
| --- | --- |
| `LASER_STUDIO_SIMULATION` | Simule un graveur GRBL 1.1, pour tester l’application sans machine. La valeur est le facteur de vitesse : `1` en temps réel, `20` vingt fois plus vite. |
| `LASER_STUDIO_DEBUG` | Journalise la gravure (file d’attente, envoi du G-Code, port série) : étapes et erreurs dans le terminal, détail ligne par ligne dans `gravure_debug.log`. |

Les deux variables sont désactivées si elles sont absentes, vides ou à `0`.

**Simulation.** Lancez l’application avec la variable :

```bash
LASER_STUDIO_SIMULATION=20 python main.py
```

Un port « SIMULATION - Graveur simulé » apparaît en tête de la liste des ports. Connectez-vous dessus comme à une vraie machine : le graveur simulé répond aux réglages (`$$`, modifiables avec `$N=valeur`), au homing (`$H`), au déverrouillage (`$X`) et au jog, exécute le G-Code en respectant les vitesses, et réagit à la pause (`!`), à la reprise (`~`) et au reset (Ctrl+X, avec `ALARM:3` si la machine bougeait). Pour simuler une machine sans homing, envoyez `$22=0` depuis la console.

**Journal de débogage.** Lancez l’application avec la variable :

```bash
LASER_STUDIO_DEBUG=1 python main.py
```

Le fichier `gravure_debug.log` est réécrit à chaque lancement, dans le dossier de données de l’application : `~/.local/share/LaserStudioPro/` sous Linux, `%APPDATA%\LaserStudioPro\` sous Windows, `~/Library/Application Support/LaserStudioPro/` sous macOS.

Les deux variables se combinent, par exemple pour suivre en détail un job envoyé au graveur simulé :

```bash
LASER_STUDIO_SIMULATION=20 LASER_STUDIO_DEBUG=1 python main.py
```

## Remerciements

Merci à toutes les personnes qui contribuent au projet, testent les fonctionnalités et signalent les bugs.

## Licence

Laser Studio Pro est un logiciel libre : il peut être redistribué et modifié selon les termes de la [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.html) publiée par la Free Software Foundation, version 3 de la licence ou (au choix) toute version ultérieure (GPL-3.0-or-later).

Il est distribué dans l’espoir d’être utile, mais SANS AUCUNE GARANTIE, sans même la garantie implicite de QUALITÉ MARCHANDE ou d’ADÉQUATION À UN USAGE PARTICULIER. Le texte complet de la licence se trouve dans le fichier [`LICENSE`](LICENSE).

## Captures de chaque onglet et page

Images produites par `tools/screenshots.py` (avec une image d’exemple chargée et son G-Code généré).

### Onglets

**Graver une image :**

![Graver une image](docs/screenshots/01-onglet-graver-une-image.png)

**Vectorisation d’image :**

![Vectorisation d'image](docs/screenshots/02-onglet-vectorisation-d-image.png)

**Séparation Couleur / Verre :**

![Séparation Couleur / Verre](docs/screenshots/03-onglet-separation-couleur-verre.png)

**Graver une image vectorielle :**

![Graver une image vectorielle](docs/screenshots/04-onglet-graver-une-image-vectorielle.png)

**Calques (Layers) :**

![Calques (Layers)](docs/screenshots/05-onglet-calques-layers.png)

**Visualisation 2D G-Code :**

![Visualisation 2D G-Code](docs/screenshots/06-onglet-visualisation-2d-g-code.png)

**Console / G-Code :**

![Console / G-Code](docs/screenshots/07-onglet-console-g-code.png)

**File d’attente :**

![File d'attente](docs/screenshots/08-onglet-file-d-attente.png)

### Pages de réglages (menu Paramètres)

**Paramètres du graveur :**

![Paramètres du graveur](docs/screenshots/10-page-parametres-du-graveur.png)

**Matériaux et connexion au graveur :**

![Matériaux et connexion au graveur](docs/screenshots/11-page-materiaux-et-connexion-au-graveur.png)

**Configuration GRBL :**

![Configuration GRBL](docs/screenshots/12-page-configuration-grbl.png)

**Matrice de test :**

![Matrice de test](docs/screenshots/13-page-matrice-de-test.png)
