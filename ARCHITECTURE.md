# Laser Studio Pro — Architecture & cartographie du code

> Document mis à jour pour faciliter la prise en main et la modification du projet.  
> Branche de référence : **Dev** — dépôt : https://github.com/Jgood3d/laser-studio-pro  
> Version applicative : **2.5.0** (voir `core/version.py`)

Ce fichier regroupe :
1. L’arborescence complète
2. Le rôle de chaque module / fichier
3. Les liens de dépendance (qui utilise qui)
4. Les flux principaux
5. Les évolutions récentes (thèmes, édition vectorielle, Stencil Studio, icônes)

---

## 1. Vue d’ensemble du flux de démarrage

```
main.py
  │
  ├─► (option) --stencil-studio → stencil_studio.studio_window
  │
  ├─► install_qt_message_filters / setup_debug_logging
  ├─► QApplication
  ├─► install_breeze_icon_theme()   # resources/icons/breeze (surtout Windows)
  ├─► apply_app_theme()            # ui/app/theme.py (dark / light / dusk / warm)
  ├─► StartupSplash
  │
  └─► main_window.py  (classe FullLaserStudio : construit la fenêtre, init_ui)
        │
        │  Hérite des mixins :
        │
        ├─ WindowControllerMixin (ui/app/window_controller.py) signaux du menu, thème, connexion
        ├─ ImageProcessingMixin  (image_processing_mixin.py)
        ├─ VectorEditingMixin    (vector_editing_mixin.py)
        ├─ GcodeGenerationMixin  (gcode_generation_mixin.py)
        ├─ LaserControlMixin     (laser_control_mixin.py)
        └─ SeparationMixin       (separation_mixin.py)  logique de la séparation (vue : ui/tabs/separation/)
        │
        │  Et crée les contrôleurs (controllers/), des objets ordinaires
        │  qui reçoivent ce dont ils ont besoin :
        │
        ├─ png2svg       = Png2SvgController      envoi du SVG vers l'éditeur vectoriel
        ├─ matrix_image  = MatrixImageController  matrice de test à partir d'une image
        ├─ job_queue     = JobQueueController     file d'attente (graveur : interface Engraver)
        ├─ project       = ProjectController      fichier du projet, récents, sauvegarde automatique
        ├─ materials     = MaterialsController    profils matériaux (modèle MaterialsModel)
        └─ machines      = MachineProfilesController profils machine (champs : ProfileFields)
```

`FullLaserStudio` est le **cœur** : il assemble les mixins et possède les objets partagés (`usb`, `layer_manager`, images, file d’attente…).

---

## 2. Arborescence complète

```
laser-studio-pro/
├── pyproject.toml                    # disposition src/ : paquets laser_studio et laser_common
├── main.py                           # lance l'application depuis le dépôt (et point d'entrée PyInstaller)
├── .github/workflows/macos-build.yml
├── docs/                             # captures, page de présentation
├── packaging/                        # compilation : windows/ (build.bat, setup.iss), linux/ (build-linux.sh), macos/ (spec, scripts, icns)
├── src/laser_common/                 # partagé par Laser Studio et Stencil Studio : files (écriture sûre)
├── src/laser_studio/                 # l'application : resources/, ui/, core/, models/, vector/, image/, grbl/, i18n/, controllers/, main_window.py, mixins (détail ci-dessous, sauf stencil_studio/, tests/, tools/)
├── resources/                        # images : icône, bannière, logo, « Buy me a coffee »
│   └── icons/breeze/                 # thème d’icônes FreeDesktop embarqué
│       ├── index.theme
│       ├── COPYING.LGPL-3
│       ├── 16x16/actions/…
│       └── 22x22/{actions,devices,apps,categories,preferences}/…
├── stencil_studio/                   # sous-application Stencil Studio
│   ├── LISEZMOI.md
│   ├── core.py / engrave.py / lightbox.py / subject_ai.py
│   ├── lasercut_stencil.py
│   ├── lsp_bridge.py                 # import SVG/DXF vers l’éditeur LSP
│   ├── studio.py / studio_window.py / studio_dialog.py
│   ├── i18n.py + locales / json
│   ├── fonts/ / models/ / exemple/
│   └── lancer_studio.bat / .sh
├── tests/
├── tools/
│   ├── check_translations.py
│   ├── check_ui_attributes.py
│   ├── signal_map.py                 # carte des signaux → docs/architecture/signaux.svg / .png
│   └── screenshots.py                # captures de l'interface → docs/screenshots/
├── main.py                           # point d’entrée (+ Breeze + thème)
├── main_window.py
├── core/                             # socle sans interface : version, paths (chemins, ressources), constants, debug_log
├── models/                           # modèles de données (QObject à signaux) : layers (LayersModel), layer_modes (codes des modes, sans Qt), machine (MachineConfig), grbl (GrblConfig), materials (MaterialsModel), settings (base), change_log (journal)
├── i18n/                             # traductions : translations.py (textes), language.py (langue, tr)
├── grbl/                             # dialogue avec le graveur, sans Qt (connection, simulator)
├── workers.py
├── controllers/                      # contrôleurs : png2svg, matrix_image, job_queue, project, materials, layer_memory, machine_profiles (remplacent des mixins)
├── ui/about/ / ui/support/ / ui/buy_me_a_coffee/   # boîtes du menu Aide (classes), bouton ko-fi
├── ui/splashscreen/                  # écran de démarrage (StartupSplash)
├── ui/statusbar/                     # barre d'état (StatusBar : messages, progression)
├── ui/app/menu/                      # menu et barre d'outils (AppActions, AppMenuBar, AppToolBar)
├── ui/app/window_controller.py       # contrôleur de la fenêtre (WindowControllerMixin)
├── ui/app/qt_messages.py             # filtre des avertissements Qt
├── ui/app/theme.py                   # thèmes UI : dark / light / dusk / warm, pack d'icônes Breeze
├── ui/widgets/                       # petits widgets (ZoomableGraphicsView, HistoryLineEdit, AutoHideLabel, TabToolBar, FullscreenWindow, SliderWithButtons)
├── ui/utils.py                       # icônes dessinées, images haute résolution
├── ui/machine/connection/            # connexion (ConnectionPanel : port, connecter, état GRBL, console directe)
├── ui/machine/status/                # état GRBL (MachineStateView) et position X / Y / Z (AxisPositionRow)
├── ui/machine/controls/              # panneau de pilotage (JogControlPanel, commandes RealtimeCommands)
├── ui/machine/job_actions/           # actions de job (JobActionsPanel, signaux)
├── ui/machine/console/               # console directe, dans Connexion (DirectConsolePanel : command_submitted)
├── ui/tabs/layers/                   # onglet Calques (LayersTab : profils matériaux, layers_changed)
├── ui/tabs/image/                    # onglet Graver une image (ImageTab, ImageSettingsPanel, MaterialComboBox, ResolutionBox)
├── ui/machine/job_position/          # cadre Position du job (JobPositionBox), à droite de l'aperçu 2D
├── ui/machine/sent_gcode/            # suivi du G-Code envoyé (SentGcodeLog), à gauche du panneau machine
├── ui/tabs/separation/               # onglet Séparation Couleur / Verre (SeparationTab)
├── ui/tabs/png2svg/                  # onglet Vectorisation d'image (Png2SvgTab, PngToSvgWidget, ZoomableSvgView)
├── ui/tabs/preview_2d/               # onglet Visualisation 2D (Preview2DTab ; à droite JobPositionBox puis JobStatsPanel)
├── ui/tabs/console/                  # onglet Console / G-Code (ConsoleTab : export_requested, set_stats)
├── ui/tabs/job_queue/                # onglet File d'attente (JobQueueTab)
├── ui/settings/machine_params/       # page Paramètres du graveur (MachineParamsPage)
├── ui/settings/test_matrix/          # page Matrice de test (TestMatrixPage, cadre ImageTestGroup, aperçu TilePicker)
├── ui/settings/grbl_config/          # page Configuration GRBL (GrblConfigPage, cadre GrblSettingsBox)
├── ui/dialogs/box_generator/          # fenêtre du générateur de boîte (BoxGeneratorDialog) + aperçu live (preview.py : BoxPreview)
├── ui/dialogs/nesting/               # fenêtre de l'imbrication (NestingDialog)
├── ui/dialogs/serial_duplicate/      # fenêtre « Dupliquer en série » (SerialDuplicateDialog)
├── ui/dialogs/dither_comparison/     # comparaison des algorithmes de tramage (DitherComparisonDialog)
├── ui/settings/window.py              # fenêtre des pages de réglages (SettingsWindow)
├── image_processing_mixin.py
├── image/                            # traitement d'image sans Qt : filters, size, matrix, separation, vectorize
├── vector_editing_mixin.py
├── vector_layers.py                  # calques + canevas + nœuds / explode
├── vector/                           # géométrie vectorielle : order, nudge, font, dxf, box_generator, puzzle_generator, nesting, nesting_apply, serial_duplicate, serial_apply, importers
├── gcode_generation_mixin.py / laser_control_mixin.py
├── separation_mixin.py
├── requirements-linux.txt / requirements-windows.txt
├── BUILD.md
└── ARCHITECTURE.md / CHANGELOG.md / README.md / LICENSE
```

---

## 3. Rôles détaillés par fichier

### 3.1 Point d’entrée & infrastructure

| Fichier | Rôle | Liens principaux |
|---------|------|------------------|
| **main.py** | Lance l’app (ou Stencil Studio si `--stencil-studio`). Installe Breeze, applique le thème, splash, icône fenêtre. | → `ui/app/theme`, `main_window.FullLaserStudio`, `core`, `ui.splashscreen` |
| **ui/app/theme.py** | Définition des thèmes **dark / light / dusk / warm** (palette Qt + stylesheet généré). `apply_app_theme()`, `available_themes()`. | `main.py`, `ui/app/window_controller.change_theme` |
| **core/version.py** | Version (`APP_VERSION`), lue aussi par le build macOS | `ui/about`, `ui/app/menu` |
| **core/paths.py** | Dossier de l'exécutable et du bundle, dossier des données (autosave), ressources (`find_resource`) | Utilisé largement |
| **laser_common/files.py** | Écriture atomique (`atomic_write_json`), écrivain en arrière-plan (`get_background_writer`) | `controllers/project`, `controllers/job_queue`, `main_window` |
| **core/constants.py** | Valeurs fixes (lien ko-fi, splash, JOG, barre d'état) | `ui/` |
| **models/settings.py**, **machine.py**, **grbl.py** | `SettingsModel` : réglages nommés (`FIELDS` : type et défaut), lus comme des attributs, modifiés par `update()` qui convertit, n'émet `changed({nom: valeur})` que pour ce qui change et écrit l'ancienne et la nouvelle valeur dans le journal. `MachineConfig` (`machine`) : plateau, spot, vitesse et accélération max (`to_profile` / `apply_profile` pour les profils machine). `GrblConfig` (`grbl`) : commande laser (`M4` / `M3`), S-Max, homing, surbalayage, décalage aller/retour, ordre de découpe sûr, G-Code de début et de fin, réglages `$$` ; `profile_values` / `apply_profile` / `mechanical_values` pour les profils machine. Les pages Paramètres du graveur et Configuration GRBL ne sont plus que des vues liées à ces modèles | Créés par `main_window` ; lus par la génération, l'éditeur vectoriel, le traitement d'image, Stencil Studio (`lsp_bridge`) |
| **models/layer_modes.py** | Codes des modes de calque (`engrave_fill`, `cut`, `mark`), indépendants de la langue, enregistrés dans les projets, les profils et les commentaires du G-Code ; seul leur affichage est traduit (`LAYER_MODE_TR_KEYS`, `models.layers.layer_label`). `normalize_mode()` convertit les anciens libellés français (« Gravure Remplie », « Découpe », « Marquage (Contour) ») à la lecture. Sans Qt | `models/layers`, `vector/order`, génération, Stencil Studio |
| **models/change_log.py** | Journal des changements des modèles : une ligne par changement, sauf pour les textes saisis au clavier (G-Code de début et de fin, `$$`, nom d'un calque), écrits une seule fois à la fin de la saisie | `models/` |
| **models/materials.py** | `MaterialsModel` : les matériaux (nom -> réglages des calques) et le matériau choisi ; `store()` n'émet que si quelque chose change. Le matériau choisi suit chaque changement de calque (plus de bouton « Enregistrer »), sauf pendant le chargement d'un profil machine, d'un projet ou d'un matériau (`main_window._material_autosave_paused`) | `controllers/materials` (liste déroulante tenue à jour par ses signaux) |
| **ui/binding.py** | `bind(champ, modèle, réglage)` : lie un champ (spinbox, case, liste, texte) à un réglage d'un modèle, dans les deux sens, sans boucle | Pages Paramètres du graveur et Configuration GRBL |
| **core/debug_log.py** | Logging debug / résumés G-Code | `laser_control_mixin`, `controllers/job_queue`, `grbl`, `workers`, `models/` |
| **models/layers.py** | `LayersModel` (`QObject`) : la liste des calques (`LaserLayer`), seule source de leurs réglages. Toute modification passe par `update()`, `add_layer()`, `remove_layer()`, `move_layer()` ou `load_list()`, qui émettent `layer_changed`, `layer_added`, `layer_removed`, `layers_reordered` ou `layers_reset`, puis `changed`, et écrivent l'ancienne et la nouvelle valeur dans le journal de débogage (`laser_studio.gravure.modeles`). `engrave_layer()` : calque de la gravure des images (celui choisi dans l'onglet image, `select_engrave_layer()` → signal `engrave_layer_selected`, sinon le premier calque de gravure), dont la vitesse et la puissance sont lues à chaque usage (`engrave_speed` / `engrave_power`). Chaque calque a aussi `overscan` (surbalayage, vrai par défaut) et `laser_cmd` (`""` = commande de Configuration GRBL, `M4` dynamique ou `M3` constante, voir `LAYER_LASER_CMDS`) ; `layer_overscan_enabled()` et `layer_laser_cmd()` donnent la valeur effective d'un calque (objet ou `to_dict`) en la combinant avec le réglage global, qui reste maître pour le surbalayage (mode et distance). Un ancien projet sans ces champs garde les valeurs par défaut | `main_window`, `LayerManagerWidget`, `controllers/materials`, `controllers/layer_memory`, génération |
| **ui/app/qt_messages.py** | Filtre warnings Qt (Wayland…) | `main.py` |
| **i18n/** | Traductions FR / EN / DE / ES : `translations.py` (dictionnaire `TRANSLATIONS`, y compris thèmes, nœuds, explode, outils dessin), `language.py` (langue mémorisée, `tr()`). `from i18n import tr` | Toute l’UI |
| **grbl/connection.py** | `LaserUSBController` : connexion série au graveur (ou au graveur simulé), envoi des commandes, lecture du rapport d'état | `main_window`, `workers` |
| **grbl/simulator.py** | `SimulatedGrblSerial` : graveur GRBL 1.1 simulé (`LASER_STUDIO_SIMULATION`), imite la partie de pyserial utilisée | `grbl.connection`, `laser_control_mixin` |

### 3.2 Fenêtre principale = assemblage de mixins

| Mixin / fichier | Rôle | Dépend de / appelle |
|-----------------|------|---------------------|
| **main_window.py** | `FullLaserStudio` : mixins + USB + `LayersModel` + timers. Construit la fenêtre (`init_ui` appelle les `_build_*`), crée `MachinePanel` et l'abonne à la logique (`_build_machine_panel`), fermeture, drag&drop, affichage du panneau machine et tailles du séparateur, plein écran d'un onglet, fenêtres de réglages, onglet « Éditeur vectoriel » (`_build_vector_editor_tab`, partira dans `ui/tabs/`) | Tous les mixins, `ui/machine`, `ui/statusbar`, `ui/settings/window` |
| **ui/app/menu/** | `AppActions` crée toutes les actions (icône, libellé, raccourci, état) et émet les signaux (`save_project_requested`, `mirror_changed`…). `AppMenuBar` et un fichier par `QMenu` (Fichier, Paramètres, Affichage, Outils, Aide), `AppToolBar` (mêmes actions + « Générer » et, à droite, le bouton ko-fi) ne font que les ranger | `ui/buy_me_a_coffee` |
| **ui/app/window_controller.py** | Contrôleur de la fenêtre : abonne la fenêtre aux signaux de `AppActions`, `change_theme`, langue, `update_connection_widgets`, actions de la barre d'outils sur l'image de l'onglet courant, ouverture Stencil Studio | `app_theme`, `ui/app/menu`, `stencil_studio.studio_dialog` |
| **ui/tabs/image/** | `ImageTab` : onglet « Graver une image », réglages à gauche (`ImageSettingsPanel` : taille + offset, réglages photo, matière, tramage, résolution, **calque de gravure** — `EngraveLayerComboBox`, calques en mode gravure seulement, signal `engrave_layer_changed(id)` sur choix de l'utilisateur ; la fenêtre le transmet à `LayersModel.select_engrave_layer` et remplit la liste via `_refresh_engrave_layer_combo`, `vector_editing_mixin`), aperçus originale / tramé côte à côte. Émet `compare_requested`, `fullscreen_requested` ; le panneau émet `processing_changed`, `size_changed`, `material_changed`, `resolution_mode_changed`… | Construit et abonné dans `main_window._build_image_tab`, qui garde les anciens noms des champs (`spin_w`, `slider_bright`, `combo_algo`, `spin_lmm`…) |
| **ui/machine/job_position/** | `JobPositionBox` : cadre « Position du job » (origine du repère, lue par code : `origin()` / `set_origin()`) | Construit dans `main_window._build_image_tab`, placé en haut de la colonne de droite de `Preview2DTab` |
| **ui/machine/sent_gcode/** | `SentGcodeLog` : suivi du G-Code envoyé (`clear_lines`, `append_lines`, `mark_end`) | Placé à gauche par `MachinePanel` ; alimenté par `JobQueueController` (`sent_log`) et l'envoi direct (`LaserControlMixin`) |
| **ui/machine/** | `MachinePanel` : assemble sous les onglets la rangée G-Code envoyé / connexion / pilotage / actions de job, et la barre de progression du job. Pas de signaux à lui : la fenêtre s'abonne à ceux de ses sous-panneaux ; `set_connected()` verrouille les commandes, `set_status()` répartit l'état GRBL (Connexion) et la position (sous le pilotage) | Construit et abonné dans `main_window._build_machine_panel` |
| **ui/machine/controls/** | `JogControlPanel` : jog, homing, pas, vitesse, commandes temps réel, envoi du job. Émet des signaux (`jog_requested`…), sans logique machine | Abonné : `LaserControlMixin` (via `main_window._build_machine_panel`) |
| **ui/machine/job_actions/** | `JobActionsPanel` : cadrage, zéro, aller au zéro, répétition. Émet des signaux, construit depuis une liste d'actions (futures macros) | Abonné : `LaserControlMixin` (via `main_window._build_machine_panel`) |
| **ui/machine/status/** | `MachineStateView` : état GRBL coloré, « Déverrouiller » visible seulement en alarme (émet `unlock_requested`), dans `ConnectionPanel`. `AxisPositionRow` : X / Y / Z à parts égales, en bas de `JogControlPanel` | Alimentés par `LaserControlMixin._update_dro_display` → `MachinePanel.set_status` |
| **ui/machine/console/** | `DirectConsolePanel` (sans cadre, dans `ConnectionPanel`) : champ de commande GRBL avec historique (flèches) et bouton « Envoyer ». Émet `command_submitted(commande)` | Abonné : `LaserControlMixin.send_console_command` |
| **ui/settings/machine_params/** | `MachineParamsPage` (QScrollArea) : profils machine, dimensions du lit, spot, limites. Émet `profile_selected`, `new/update/delete_profile_requested`, `bed_size_changed(l, p)`, `focal_changed(mm)`, `max_speed_changed` | Construite et abonnée dans `main_window._build_machine_params_page` ; ses champs sont liés au modèle `MachineConfig` (`ui/binding.py`), que lit la logique (`self.machine.bed_w`…) ; les anciens noms (`spin_machine_w`…) restent pour l'interface |
| **ui/settings/test_matrix/** | `TestMatrixPage` : réglages de la matrice (puissances, passes, vitesses, cases), affichage selon le mode gravure / découpe, test à partir d'une image (aperçu `TilePicker`). Émet `generate_requested`, `choose_image_requested`, `use_loaded_image_requested`, `image_test_toggled` ; fournit `matrix_params()`, `tile_settings()` ; reçoit `set_lines_mm()`, `set_source_image()` | Construite et abonnée dans `main_window._build_test_matrix_page` ; lue par `GcodeGenerationMixin.generate_test_matrix` |
| **ui/settings/grbl_config/** | `GrblConfigPage` : commande laser, S-Max, homing, surbalayage (la page affiche la distance ou le pourcentage selon le mode), ordre de découpe sûr, décalage aller/retour, G-Code de début et de fin, réglages GRBL complets ($$). Émet `bidir_test_requested`, `scan_offset_changed`, `read_settings_requested`, `send_settings_requested`, `export_settings_requested`, `import_settings_requested`, `link_settings_to_profile_requested` | Construite et abonnée dans `main_window._build_grbl_config_page`, qui garde les anciens noms des champs (`combo_laser_cmd`, `chk_overscan`, `txt_grbl_settings`…) lus par la génération, les profils, les projets et la connexion |
| **controllers/** | Contrôleurs : objets Python ordinaires, construits par la fenêtre avec ce dont ils ont besoin, sur lesquels elle branche les signaux de l'interface. `Png2SvgController` (SVG de l'onglet PNG→SVG → objets de l'éditeur vectoriel), `MatrixImageController` (matrice à partir d'une image : fichier ou image de « Graver une image », zone gravée de chaque case), `JobQueueController` (liste des jobs, sauvegarde, enchaînement des envois par l'interface `Engraver`), `ProjectController` (fichier du projet : format JSON et image en base64, boîtes Enregistrer / Ouvrir, projets récents, sauvegarde automatique et récupération ; l'état est fourni et réappliqué par `main_window._capture_project` / `_restore_project`) | Construits dans `main_window` (`_build_png2svg_tab`, `_build_test_matrix_page`, `_build_job_queue_tab`) ; testés seuls (`tests/test_controllers.py`) |
| **ui/tabs/layers/** | `LayersTab` : page de l'onglet « Calques ». Barre des profils matériaux (`material_combo`, `material_selected` sur un choix de l'utilisateur seulement, actions enregistrer / nouveau / supprimer / exporter / importer). Enveloppe `LayerManagerWidget` (encore dans `vector_layers.py`, vue abonnée à `LayersModel`), relaie `layers_changed` (= `LayersModel.changed`), `refresh()`, `link_all_to_focal()`… | Construit et abonné dans `main_window._build_layers_tab` ; lu par Stencil Studio (`lsp_bridge`) |
| **ui/tabs/preview_2d/** | `Preview2DTab` : onglet « Visualisation 2D G-Code ». Options d'affichage (inverser, négatif, déplacements rapides, optimiser le chemin), graphique pyqtgraph (`plot_widget`), point de la tête (`position_marker`). À droite, séparateur réglable (position mémorisée) : colonne étroite avec `JobPositionBox` puis `JobStatsPanel` (`set_stats`). Émet `display_options_changed`, `plot_clicked(x_mm, y_mm)`, `fullscreen_requested` | Construit et abonné dans `main_window._build_2d_preview_tab` ; la génération (`GcodeGenerationMixin`) dessine dans `plot_widget` |
| **ui/tabs/console/** | `ConsoleTab` : onglet « Console / G-Code », masqué au démarrage (menu Affichage). Console `console_edit` ; les statistiques sont dans `JobStatsPanel` (à droite de l'aperçu 2D), l'export dans « Fichier > Enregistrer le G-Code » | Construit dans `main_window._build_console_tab`, qui garde le nom `txt_console` utilisé partout |
| **ui/tabs/job_queue/** | `JobQueueTab` : onglet « File d'attente ». Liste réordonnable, boutons (le G-Code envoyé est suivi dans le panneau machine). Émet `add_current_requested`, `remove_selected_requested`, `clear_requested`, `run_requested`, `reordered` | Construit dans `main_window._build_job_queue_tab`, piloté par `JobQueueController` ; le suivi du G-Code envoyé (`SentGcodeLog`, panneau machine) sert aussi à l'envoi direct (`LaserControlMixin._start_stream`) |
| **image_processing_mixin.py** | Image, filtres, matière, undo image | `workers`, `image.filters`, `image.size` |
| **vector_editing_mixin.py** | Import SVG/DXF, outils dessin (`set_vector_draw_tool`), alignement, nesting, duplication en série, boîtes | `vector_layers`, `vector/importers`, `vector/dxf`, `vector/nesting*`, `vector/serial_*` |
| **gcode_generation_mixin.py** | Génération G-Code image + vectoriel, aperçu 2D | `workers`, `vector_layers` |
| **laser_control_mixin.py** | USB/série, stream, status, homing, urgences | `grbl.connection`, `workers` |
| **separation_mixin.py** | Logique de la séparation couleur (vue : `ui/tabs/separation/`, `SeparationTab`) | `image.separation`, `workers` |

### 3.3 Vectoriel (cœur édition)

| Fichier | Rôle | Utilisé par |
|---------|------|-------------|
| **vector_layers.py** | Tableau des calques (`LayerManagerWidget`, vue de `LayersModel` ; `LayerManager` reste un alias de `LayersModel` ; colonnes Couleur, Nom, Mode, Puissance, Vitesse, Passes, Pas, Surbalayage — grisée hors gravure remplie —, Laser — Auto / M4 / M3 —, Actif), `build_vector_layers_gcode` (commande et surbalayage de chaque calque), objets (`TextObject`, `ShapeObject`, `SvgPathObject`), **`VectorCanvasView`** | Éditeur, G-Code, profils |
| **vector/importers.py** / **vector/dxf.py** | Import SVG/DXF (groupé par défaut) | `vector_editing_mixin` |
| **vector/order.py** / **vector/nudge.py** / **vector/font.py** | Ordre de coupe, nudge clavier, polices | Éditeur |
| **vector/box_generator.py** / **vector/puzzle_generator.py** / **vector/nesting.py** / **vector/nesting_apply.py** | Boîte à encoches, puzzle jigsaw, imbrication | `vector_editing_mixin`, `ui/dialogs` |
| **vector/serial_duplicate.py** / **vector/serial_apply.py** | Duplication en série : exemplaires, texte par exemplaire, grille (logique pure, testée sans Qt) ; passerelle vers le canevas et l'imbrication | `vector_editing_mixin`, `ui/dialogs/serial_duplicate` |

#### Générateur de boîte (`vector/box_generator.py`)

| Élément | Description |
|---------|-------------|
| `BoxParams` | Dimensions, épaisseur, kerf, doigts, **`lid_type`** (`none` / `finger` / `lip` / `sliding`), **`clearance`** (jeu des assemblages libres), **`dividers_x` / `dividers_y`** |
| `build_box()` | Parois à doigts + couvercle selon le type + cloisons ; renvoie des `Panel` (contour `cut`, trous `holes`) |
| `rectilinear_loops()` | Union / différence de rectangles → contours (extérieur anti-horaire, trous horaires) ; `rectilinear_outline()` en est l'enveloppe à un seul contour |
| Couvercles | `lip` : plaque + rebord (`top`, `lip`) ; `sliding` : façade abaissée, rainure dans `left` / `right`, plaque `top` plus petite |
| Cloisons | `divider_x<n>` / `divider_y<n>` ; fentes ajoutées en trous dans `front`/`back`/`left`/`right`/`bottom` ; emboîtement à mi-hauteur au croisement |
| `importers.box_to_objects` | Un objet par trou puis un par contour ; la même `Panel` peut donc apparaître plusieurs fois |
| `tests/test_box_generator.py` | Contrôle 3D : aucune collision entre pièces, volume exact avec jeu nul |


#### Capacités du canevas (`VectorCanvasView`)

| Fonction | Description |
|----------|-------------|
| Import groupé | SVG/DXF arrivent en **un seul objet** (`ungroup=False` par défaut) |
| Dégrouper | Clic droit → sous-tracés indépendants (`ungroup_selected`) |
| **Exploser en segments** | Chaque arête = un objet (`explode_selected`) — supprimer une encoche / un trait |
| **Édition de nœuds** | Poignées jaunes : déplacer, double-clic = ajouter, Suppr = retirer |
| Outils dessin | `line` / `rect` / `ellipse` en clic-glisser (`set_draw_tool`) |
| Grouper / aligner / distribuer | Sélection multiple |
| Undo / redo | Snapshots sur le canevas |

### 3.4 Thèmes & icônes

| Élément | Rôle |
|---------|------|
| **ui/app/theme.py** | 4 thèmes : `dark`, `light`, `dusk` (gris-bleu), `warm` (gris chaud ambré) |
| Menu **Paramètres → Thème** | `available_themes()` + `change_theme()` ; persistance `QSettings("app_theme")` |
| **resources/icons/breeze/** | Pack minimal Breeze (LGPL-3) ; activé par `install_breeze_icon_theme()` si pas de thème système, cherché comme les images (`resource_candidates`) |
| **packaging/ / BUILD.md** | `--add-data "resources;resources"` embarque les images et le pack d'icônes |

### 3.5 Stencil Studio

| Fichier | Rôle |
|---------|------|
| **studio_dialog.py** | Fenêtre QtWebEngine intégrée ; `theme_for_lsp()` mappe dark/light/dusk/warm ; `sync_theme_from_lsp()` à chaud |
| **lsp_bridge.py** | Intercepte exports SVG/DXF → import dans l’éditeur vectoriel |
| **studio.py** | Serveur HTTP local + logique de conversion |

Thèmes Studio (`LSP_THEME_*`) alignés sur les palettes LSP.

### 3.6 Image, machine, build

Inchangé dans l’esprit : `workers.py` (threads), `grbl/`, `ui/settings/window.py`, scripts `build.bat` / `macos/` / `setup.iss`. Voir CHANGELOG pour le détail des versions.

---

## 4. Schéma des dépendances principales

```
main.py
  ├─ ui.app.theme.apply_app_theme
  ├─ resources/icons/breeze  (QIcon theme)
  └─ FullLaserStudio
        ├─ WindowControllerMixin ──► menu thème ──► change_theme ──► ui.app.theme
        │                 └─► open_stencil_studio ──► studio_dialog
        │                        (theme_for_lsp / sync_theme_from_lsp)
        ├─ VectorEditingMixin ──► VectorCanvasView (vector_layers)
        │         ├─ import SVG/DXF (groupé)
        │         ├─ set_vector_draw_tool (line/rect/ellipse)
        │         ├─ explode_selected / enter_node_edit
        │         └─ nesting / box_generator / puzzle_generator
        ├─ GcodeGenerationMixin ──► workers + vector_layers G-Code
        └─ LaserControlMixin ──► grbl.connection / grbl.simulator
```

---

## 5. Flux fonctionnels typiques

### 5.1 Gravure image
Chargement → filtres (`ImageProcessingMixin`) → génération G-Code → stream machine.

### 5.2 Vectoriel (édition d’un SVG/DXF)

```
Import SVG/DXF  ──(groupé)──► 1 SvgPathObject
       │
       ├─► Clic droit « Dégrouper »     → sous-tracés
       ├─► « Exploser en segments »     → 1 objet par arête
       ├─► « Éditer les nœuds »         → déplacer / ajouter / supprimer sommets
       ├─► Outils Ligne / Rectangle / Ellipse (souris)
       └─► Générer G-Code (calques Découpe / Gravure / Marquage)
```

### 5.3 Changement de thème

```
Menu Thème → change_theme(name)
    ├─ QSettings app_theme
    ├─ apply_app_theme(app, name)     # palette + stylesheet
    └─ si Stencil Studio ouvert → sync_theme_from_lsp(name)
```

### 5.4 Stencil Studio → LSP
Export SVG/DXF dans le Studio → `lsp_bridge` / download handler → objets sur le canevas vectoriel (même règle d’import groupé).

---

## 6. Principes d’architecture à respecter

1. **Mixins additifs** : ne pas casser les responsabilités (UI ≠ G-Code ≠ USB).
2. **Repère machine** : origine bas-gauche, Y vers le haut dans le modèle monde ; conversion écran dans `VectorGraphicsItem.refresh`.
3. **Import vectoriel groupé par défaut** ; dégroupage / explosion **explicites** (clic droit ou boutons).
4. **Thème unique source de vérité** : `ui.app.theme.THEMES` + `QSettings("app_theme")` ; Stencil Studio consomme via `theme_for_lsp`.
5. **Undo canevas** : toute mutation géométrique (nœuds, explode, dessin) doit appeler `push_undo_snapshot()` avant modification.
6. **i18n** : toute nouvelle chaîne UI passe par `tr("…")`, avec sa clé dans `i18n/translations.py`.
7. **Ressources** : images dans `resources/`, chargées via `find_resource` ; pack d'icônes `resources/icons/` ; penser à `--add-data "resources;resources"` dans les builds.

---

## 7. Évolutions récentes (mémo)

| Domaine | Ajout |
|---------|--------|
| Thèmes | `dark`, `light`, **`dusk`**, **`warm`** (`ui/app/theme.py`) |
| Icônes | Pack **Breeze** embarqué (`resources/icons/breeze`) |
| Import | Plus de dégroupage automatique SVG/DXF |
| Dessin | Outils souris ligne / rectangle / ellipse |
| Édition | **Exploser en segments** + **mode nœuds** |
| Stencil Studio | Thème lié à LSP (4 thèmes, sync à chaud) |
| UI claire | Stylesheet dédié (boutons ±, spinbox, etc.) |

---

## 8. Générateur de Puzzle

| Fichier | Rôle |
|---------|------|
| **vector/puzzle_generator.py** | Géométrie jigsaw (tenons/mortaises) + grille ondulée ; validation ; `PuzzleResult` : `pieces` (aperçu seulement), **`outline`** (contour extérieur fermé, agrandi de kerf/2) et **`edges`** (arêtes internes, chacune une seule fois, tracés ouverts) |
| **ui/dialogs/puzzle/** | `PuzzleGeneratorDialog` (aperçu live, réglages forme, calque de découpe) |
| **vector/importers.puzzle_to_objects** | `outline` + `edges` → 2 `SvgPathObject` (contour fermé ; arêtes internes regroupées en un objet) |
| **vector_editing_mixin.open_puzzle_generator** | Ouverture dialogue + placement sur canevas |
| **main_window._build_vector_editor_tab** | Bouton toolbar « 🧩 Puzzle » |
| **i18n/translations.py** | Clés `menu.tools.puzzle`, `ui.vector_puzzle_*`, `puzzle.*`, `puzzle.err.*` |

Flux :

```
Bouton éditeur / menu Outils
  → open_puzzle_generator()
      → PuzzleGeneratorDialog
      → vector.puzzle_generator.build_puzzle(params)   # validate + kerf
      → vector.importers.puzzle_to_objects(...)
      → vector_canvas.add_object(...) + push_undo_snapshot()
```

Principes : mêmes conventions que la boîte (mm, Y vers le haut, calque de découpe, undo canevas).
**Une arête = un passage de laser** : deux pièces voisines partagent leur frontière, donc on ne génère jamais un contour fermé par pièce pour la découpe (chaque arête interne serait coupée deux fois). `PuzzleResult.pieces` ne sert qu'à l'aperçu. Le kerf n'est pas compensé sur les arêtes internes (le trait enlève kerf/2 à chaque pièce voisine) ; seul le contour extérieur est agrandi de kerf/2.
**Tracés ouverts** : `build_vector_layers_gcode` ne referme plus un tracé ouvert (sinon aller-retour = double passage) ; seuls les tracés quasi fermés (`CLOSE_GAP_MM`) le sont. Test : `tests/test_puzzle_cut_once.py`.
`PuzzleError` → message traduit `puzzle.err.<code>`.

## 8.1 Stencil Studio → calques multiples (lsp_bridge)

Export Studio vers LSP : routage par nom de calque DXF / groupe SVG

| Nom export | Calque LSP |
|------------|------------|
| CUT / FRAME | Découpe (existant ou créé) |
| ENGRAVE / MARK | Gravure / Marquage |
| LAYER_n | Calque dédié « LAYER n » (créé si besoin), mode Découpe, réglages repris du premier calque découpe (+ focale si liée) |

Fichier : **stencil_studio/lsp_bridge.py** (`ensure_multi_layer`, `kind_for_layer_name`, `pick_layer`).

## 9. Commandes utiles

```bash
# Lancer l’application
python main.py

# Lancer Stencil Studio seul
python main.py --stencil-studio

# Tests
python -m pytest tests/

# Qualité traductions / UI
python tools/check_translations.py
python tools/check_ui_attributes.py

# Compilation syntaxe rapide
python -m compileall -q main.py src


---

*Document d’architecture — à tenir à jour lors des changements structurants (nouveaux mixins, flux d’import, thèmes, pont Stencil Studio).*
