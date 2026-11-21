# Laser Studio Pro — Architecture & cartographie du code

> Document mis à jour pour faciliter la prise en main et la modification du projet.  
> Branche de référence : **Dev** — dépôt : https://github.com/Jgood3d/laser-studio-pro  
> Version applicative : **2.5.0** (voir `core/version.py`)

Ce fichier regroupe :
1. L’arborescence complète
2. Le rôle de chaque module / fichier
3. Les liens de dépendance (qui utilise qui)
4. Les flux principaux
5. Les évolutions récentes (thèmes, générateurs, boîte 3D, Stencil Studio, icônes, caméra, avertissement de démarrage)

---

## 1. Vue d’ensemble du flux de démarrage

```
main.py
  │
  ├─► (option) --stencil-studio → stencil_studio.studio_window
  │
  ├─► install_qt_message_filters / setup_debug_logging
  ├─► QApplication
  ├─► StartupSplash                 # affiché le plus tôt possible
  ├─► install_breeze_icon_theme()   # pack d'icônes embarqué : breeze, ou jarvis si ce thème est choisi
  ├─► apply_saved_theme()           # ui/app/theme.py : 7 thèmes, relu dans QSettings("app_theme")
  ├─► StartupSafetyPolicy           # controllers/startup_safety.py : avertissement laser
  │     └─ confirm_startup_safety() # ui/dialogs/startup_safety/ ; « Annuler » quitte avant la fenêtre
  │
  └─► main_window.py  (classe FullLaserStudio : construit la fenêtre, init_ui)
        │
        │  Hérite des mixins :
        │
        ├─ WindowControllerMixin (ui/app/window_controller.py) signaux du menu, thème, résultats du job (console, aperçu 2D), affichage du graveur (position, suivi d'envoi)
        ├─ ImageProcessingMixin  (image_processing_mixin.py)
        ├─ VectorEditingMixin    (vector_editing_mixin.py)
        └─ SeparationMixin       (separation_mixin.py)  interface de la séparation (logique : controllers/separation.py, vue : ui/tabs/separation/)
        │
        │  Et crée les contrôleurs (controllers/), des objets ordinaires
        │  qui reçoivent ce dont ils ont besoin :
        │
        ├─ connection    = MachineConnection      port série, threads, état « référencé »
        ├─ engraver      = EngraverController     pilotage du graveur : ports, connexion, jog, envoi des jobs, configuration $$
        ├─ job           = JobController          paramètres, génération du G-Code, estimation, export, matrice de test
        ├─ project       = ProjectController      fichier du projet, récents, sauvegarde automatique
        ├─ machines      = MachineProfilesController profils machine (champs : ProfileFields)
        ├─ matrix_image  = MatrixImageController  matrice de test à partir d'une image
        ├─ materials     = MaterialsController    profils matériaux (modèle MaterialsModel)
        ├─ png2svg       = Png2SvgController      envoi du SVG vers l'éditeur vectoriel
        ├─ job_queue     = JobQueueController     file d'attente (graveur : interface Engraver)
        ├─ separation    = SeparationController   créé par SeparationMixin (séparation couleur)
        └─ camera        = CameraController       créé à la demande par WindowControllerMixin : capture, calibration optique, alignement plateau
```

Le code vit dans `src/laser_studio/` : le `main.py` de la racine n'ajoute que `src/` au `sys.path` et appelle `laser_studio.main.main()` (`python -m laser_studio` fonctionne aussi une fois installé, voir `pyproject.toml`). La fenêtre principale s'affiche une fois `SPLASH_SCREEN_DURATION` écoulé, et le thème est réappliqué après la construction de l'interface.

`FullLaserStudio` est le **cœur** : il assemble les mixins et possède les objets partagés (`usb`, `layer_manager`, images, file d’attente…).

---

## 2. Arborescence complète

```
laser-studio-pro/
├── main.py                           # lance l'application depuis le dépôt (ajoute src/ au chemin) et point d'entrée PyInstaller
├── pyproject.toml                    # disposition src/ : paquets laser_studio et laser_common ; version lue dans core/version.py
├── requirements-linux.txt / requirements-windows.txt   # dépendances par plateforme
├── requirements_principal.txt        # versions exactes figées pour les builds
├── .github/workflows/                # tests.yml (unittest hors écran), release.yml (tag vX.Y.Z → Linux AppImage, Windows, macOS, release en brouillon), macos-build.yml
├── docs/                             # page de présentation (index.html), captures (screenshots/, shot-*.png, result-*.jpg, gravure-test-*.jpg), bannière, architecture/ (signaux.svg / .png)
├── packaging/                        # compilation
│   ├── windows/                      # build.bat, setup.iss (Inno Setup)
│   ├── linux/                        # build-linux.sh, build-appimage.sh
│   ├── macos/                        # LaserStudioPro.spec, build_macos.sh, run_macos.sh, requirements-macos.txt, laser_studio_pro.icns, README.md
│   └── pyinstaller/                  # LaserStudioPro.spec (commun Windows / Linux), bundle_filter.py (filtre des fichiers inutiles)
├── src/
│   ├── laser_common/                 # partagé par Laser Studio et Stencil Studio
│   │   └── files.py                  # écriture sûre (atomique, en arrière-plan)
│   └── laser_studio/                 # l'application
│       ├── main.py / __main__.py     # démarrage (python -m laser_studio)
│       ├── main_window.py            # FullLaserStudio : assemble les mixins, construit la fenêtre (init_ui, _build_*)
│       ├── image_processing_mixin.py # image, filtres, matière, undo image
│       ├── vector_editing_mixin.py   # import, dessin, alignement, nesting, duplication en série, générateurs
│       ├── separation_mixin.py       # séparation couleur côté interface
│       ├── vector_layers.py          # calques (LayerManagerWidget) + canevas (VectorCanvasView) + objets + nœuds / explode
│       ├── workers.py                # threads (QThread) : traitement d'image, envoi du G-Code, sondage d'état ; la génération y appelle gcode/
│       ├── gcode/                    # génération du G-Code sans Qt : job (assemblage), raster (image), svg_cut, vector (calques), test_matrix, calibration (aller/retour), preview (modèle de l'aperçu 2D), common
│       ├── core/                     # socle sans interface : version, paths (chemins, ressources), constants, debug_log
│       ├── models/                   # modèles de données (QObject à signaux) : layers (LayersModel), layer_modes (codes des modes, sans Qt), machine (MachineConfig), grbl (GrblConfig), materials (MaterialsModel), image_settings (ImageSettings, ImageSettingsHistory), separation (SeparationSettings), settings (base SettingsModel), change_log (journal)
│       ├── i18n/                     # traductions : translations.py (textes FR / EN / DE / ES), language.py (langue, tr)
│       ├── grbl/                     # dialogue avec le graveur, sans Qt : commands (commandes GRBL, lecture de $$), connection, simulator, ports (ports série proposés + dernier port utilisé)
│       ├── image/                    # traitement d'image sans Qt : filters, size, resolution, matrix, separation, vectorize
│       ├── vector/                   # géométrie vectorielle sans Qt (sauf ornament_region)
│       │   ├── importers.py / dxf.py                  # import SVG / DXF, conversion des résultats des générateurs en objets
│       │   ├── order.py / nudge.py / font.py          # ordre de coupe, déplacement clavier, polices
│       │   ├── text_on_path.py / text_on_arc.py       # texte le long d'un tracé / sur un cercle
│       │   ├── box_generator.py / box_3d.py / box_presets.py
│       │   ├── puzzle_generator.py
│       │   ├── ornament_generator.py / ornament_motifs.py / ornament_region.py
│       │   ├── keychain_generator.py
│       │   ├── nesting.py / nesting_apply.py
│       │   ├── serial_duplicate.py / serial_apply.py
│       │   └── jig.py
│       ├── camera/                   # module caméra sans Qt : capture, lens_calibration (objectif), workspace_alignment (homographie du plateau), storage
│       ├── controllers/              # contrôleurs : job, png2svg, matrix_image, job_queue, project, materials, layer_memory, machine_profiles, machine_connection, separation, camera, startup_safety (remplacent des mixins)
│       ├── resources/                # images : icône (.ico, 512 px), bannière, « Buy me a coffee »
│       │   └── icons/                # thèmes d’icônes FreeDesktop embarqués
│       │       ├── breeze/           # pack par défaut (LGPL-3) : 16x16, 22x22, 32x32
│       │       └── jarvis/           # pack cyan « HUD », activé avec le thème jarvis
│       └── ui/                       # interface PyQt6
│           ├── binding.py            # liaison champ ↔ modèle
│           ├── utils.py              # icônes dessinées, images haute résolution
│           ├── about/ / support/ / buy_me_a_coffee/   # boîtes du menu Aide, bouton ko-fi
│           ├── splashscreen/         # écran de démarrage (StartupSplash)
│           ├── statusbar/            # barre d'état (StatusBar : messages, progression)
│           ├── app/                  # coque de la fenêtre
│           │   ├── menu/             # AppActions, AppMenuBar, AppToolBar ; un fichier par menu (file, settings, view, tools, help)
│           │   ├── window_controller.py   # WindowControllerMixin
│           │   ├── qt_messages.py    # filtre des avertissements Qt
│           │   └── theme.py          # 7 thèmes UI ; packs d'icônes Breeze et Jarvis
│           ├── widgets/              # ZoomableGraphicsView, HistoryLineEdit, AutoHideLabel, TabToolBar, FloatingToolBar, TabCloseButton, FullscreenWindow, SliderWithButtons
│           ├── machine/              # panneau machine (panel.py : MachinePanel)
│           │   ├── connection/       # ConnectionPanel (port, connecter, état GRBL, console directe) ; help_dialog : aide « Port introuvable ? »
│           │   ├── status/           # MachineStateView (état GRBL), AxisPositionRow (X / Y / Z)
│           │   ├── controls/         # JogControlPanel, RealtimeCommands
│           │   ├── job_actions/      # JobActionsPanel
│           │   ├── job_position/     # JobPositionBox (à droite de l'aperçu 2D)
│           │   ├── console/          # DirectConsolePanel (dans Connexion)
│           │   └── sent_gcode/       # SentGcodeLog (à gauche du panneau machine)
│           ├── tabs/                 # un dossier par onglet
│           │   ├── layers/           # LayersTab (onglet Calques)
│           │   ├── image/            # ImageTab, ImageSettingsPanel, MaterialComboBox, EngraveLayerComboBox, ResolutionBox
│           │   ├── separation/       # SeparationTab (séparation couleur / verre)
│           │   ├── png2svg/          # Png2SvgTab, PngToSvgWidget, ZoomableSvgView
│           │   ├── preview_2d/       # Preview2DTab (dessin de l'aperçu, tête, suivi de la gravure ; modèle : gcode/preview.py), JobStatsPanel
│           │   ├── console/          # ConsoleTab (Console / G-Code)
│           │   └── job_queue/        # JobQueueTab (file d'attente)
│           ├── settings/             # window.py (SettingsWindow) et pages : machine_params/, grbl_config/, test_matrix/ (TestMatrixPage, ImageTestGroup, TilePicker)
│           └── dialogs/              # fenêtres des outils
│               ├── library/          # LibraryDialog (grille, catégories, recherche), LibraryItemDialog (fiche, variantes)
│               ├── box_generator/    # BoxGeneratorDialog + preview.py (BoxPreview) + preview_3d.py (Box3DView)
│               ├── ornament/         # OrnamentGeneratorDialog
│               ├── puzzle/           # PuzzleGeneratorDialog
│               ├── keychain/         # KeychainGeneratorDialog + KeychainPreview
│               ├── camera/           # dialog.py, lens_wizard.py, align_wizard.py
│               ├── nesting/          # NestingDialog
│               ├── jig/              # JigDialog (gabarit de placement)
│               ├── serial_duplicate/ # SerialDuplicateDialog
│               ├── dither_comparison/# DitherComparisonDialog
│               └── startup_safety/   # avertissement de sécurité laser (confirm_startup_safety)
├── stencil_studio/                   # sous-application Stencil Studio (hors src/)
│   ├── LISEZMOI.md
│   ├── core.py / engrave.py / lightbox.py / subject_ai.py / lasercut_stencil.py
│   ├── lsp_bridge.py                 # import SVG/DXF vers l’éditeur LSP
│   ├── studio.py / studio.html / studio_window.py / studio_dialog.py
│   ├── selftest.py                   # autotest : mêmes résultats OpenCV / numpy / scipy que les valeurs attendues
│   ├── i18n.py + locales/ (fr / en / de / es .json) + fr.json / de.json / es.json
│   ├── fonts/ / models/ (u2netp.onnx) / exemple/
│   ├── requirements*.txt             # dépendances propres (+ requirements-lsp-ajouts.txt)
│   └── lancer_studio.bat / .sh
├── tests/                            # 82 fichiers de test, ~850 tests (unittest, sans écran) ; gcode_reader.py et ui_source.py : outils de test
├── tools/
│   ├── check_translations.py
│   ├── check_ui_attributes.py
│   ├── project_files.py              # liste des fichiers Python de l'application (src/laser_studio)
│   ├── signal_map.py                 # carte des signaux → docs/architecture/signaux.svg / .png
│   ├── screenshots.py                # captures de l'interface → docs/screenshots/
│   └── menu_tools_puzzle.md          # mémo : brancher un outil dans le menu Outils
├── BUILD.md
├── MACOS_AUDIT.md / RELEASE_NOTES_2.x.0.md
├── claude.md / gemini.md             # consignes pour les assistants de code
└── ARCHITECTURE.md / CHANGELOG.md / README.md / LICENSE
```

---

## 3. Rôles détaillés par fichier

### 3.1 Point d’entrée & infrastructure

| Fichier | Rôle | Liens principaux |
|---------|------|------------------|
| **main.py** (racine) / **src/laser_studio/main.py** | La racine ajoute `src/` au chemin et appelle `laser_studio.main.main()`. Celui-ci lance l’app (ou Stencil Studio si `--stencil-studio`), puis : splash, icônes Breeze / Jarvis, thème enregistré, icône fenêtre, avertissement de sécurité, fenêtre principale. | → `ui/app/theme`, `controllers/startup_safety`, `main_window.FullLaserStudio`, `core`, `ui.splashscreen` |
| **ui/app/theme.py** | Définition des 7 thèmes **dark / light / dusk / warm / neon / retro80 / jarvis** (palette Qt + stylesheet généré). `apply_app_theme()`, `apply_saved_theme()` (relit et normalise `QSettings("app_theme")`), `normalize_theme_name()` (alias FR/EN), `available_themes()`, `apply_icon_theme_for_ui()` (pack Jarvis pour le thème jarvis, sinon Breeze ; un thème système n'est pas écrasé), `install_breeze_icon_theme()`. | `main.py`, `ui/app/window_controller.change_theme`, `stencil_studio/studio_dialog` |
| **controllers/startup_safety.py** | `StartupSafetyPolicy` : quand afficher l'avertissement laser du démarrage. Case « Ne plus afficher » : l'avertissement ne revient qu'en rappel tous les `REMINDER_EVERY` démarrages ; la variable d'environnement `NOWARNING` le désactive (tests). Prend tout objet de type `QSettings` | `main.py`, `ui/dialogs/startup_safety` |
| **grbl/ports.py** | Ports série proposés (`port_labels`, `is_usable`, `is_usb`, `port_of`) : masque les ports virtuels `/dev/ttyS*` sans matériel (description « n/a ») ; mémorise le dernier port (`load_last_port` / `save_last_port`). Sans Qt | `controllers/engraver`, `ui/machine/connection` |
| **core/version.py** | Version (`APP_VERSION`), lue aussi par le build macOS | `ui/about`, `ui/app/menu` |
| **core/paths.py** | Dossier de l'exécutable et du bundle, dossier des données (autosave), ressources (`find_resource`) | Utilisé largement |
| **laser_common/files.py** | Écriture atomique (`atomic_write_json`), écrivain en arrière-plan (`get_background_writer`) | `controllers/project`, `controllers/job_queue`, `main_window` |
| **core/constants.py** | Valeurs fixes (lien ko-fi, splash, JOG, barre d'état) | `ui/` |
| **models/settings.py**, **machine.py**, **grbl.py** | `SettingsModel` : réglages nommés (`FIELDS` : type et défaut), lus comme des attributs, modifiés par `update()` qui convertit, n'émet `changed({nom: valeur})` que pour ce qui change et écrit l'ancienne et la nouvelle valeur dans le journal. `MachineConfig` (`machine`) : plateau, spot, vitesse et accélération max (`to_profile` / `apply_profile` pour les profils machine). `GrblConfig` (`grbl`) : commande laser (`M4` / `M3`), S-Max, homing, surbalayage, décalage aller/retour, ordre de découpe sûr, G-Code de début et de fin, réglages `$$` ; `profile_values` / `apply_profile` / `mechanical_values` pour les profils machine. Les pages Paramètres du graveur et Configuration GRBL ne sont plus que des vues liées à ces modèles | Créés par `main_window` ; lus par la génération, l'éditeur vectoriel, le traitement d'image, Stencil Studio (`lsp_bridge`) |
| **models/layer_modes.py** | Codes des modes de calque (`engrave_fill`, `cut`, `mark`), indépendants de la langue, enregistrés dans les projets, les profils et les commentaires du G-Code ; seul leur affichage est traduit (`LAYER_MODE_TR_KEYS`, `models.layers.layer_label`). `normalize_mode()` convertit les anciens libellés français (« Gravure Remplie », « Découpe », « Marquage (Contour) ») à la lecture. Aussi `layer_laser_cmd` / `layer_overscan_enabled` (commande laser et surbalayage effectifs d'un calque, objet ou dictionnaire). Sans Qt | `models/layers`, `vector/order`, `gcode/`, Stencil Studio |
| **models/image_settings.py** | `ImageSettings` (`SettingsModel`) : réglages de tramage de « Graver une image » (luminosité, contraste, gamma, netteté, négatif, matière, miroirs, algorithme), liés aux champs de l'onglet et aux miroirs de la barre d'outils (`ImageProcessingMixin._bind_image_settings`) ; `choose_material()` coche ou décoche le négatif, `to_project()` / `load_project()` pour les projets, `processing_params()` pour le traitement. `ImageSettingsHistory` : annuler / refaire, changements rapprochés regroupés en une étape | `main_window`, `image_processing_mixin`, `separation_mixin`, génération |
| **image/resolution.py** | Lignes/mm, DPI, focale, et classement de l'écart entre les lignes par rapport au spot (`resolution_quality`). Sans Qt | `image_processing_mixin` |
| **models/change_log.py** | Journal des changements des modèles : une ligne par changement, sauf pour les textes saisis au clavier (G-Code de début et de fin, `$$`, nom d'un calque), écrits une seule fois à la fin de la saisie | `models/` |
| **models/materials.py** | `MaterialsModel` : les matériaux (nom -> réglages des calques) et le matériau choisi ; `store()` n'émet que si quelque chose change. Le matériau choisi suit chaque changement de calque (plus de bouton « Enregistrer »), sauf pendant le chargement d'un profil machine, d'un projet ou d'un matériau (`main_window._material_autosave_paused`) | `controllers/materials` (liste déroulante tenue à jour par ses signaux) |
| **ui/binding.py** | `bind(champ, modèle, réglage)` : lie un champ (spinbox, case, liste, texte) à un réglage d'un modèle, dans les deux sens, sans boucle | Pages Paramètres du graveur et Configuration GRBL |
| **core/debug_log.py** | Logging debug / résumés G-Code | `controllers/engraver`, `controllers/job_queue`, `grbl`, `workers`, `models/` |
| **models/layers.py** | `LayersModel` (`QObject`) : la liste des calques (`LaserLayer`), seule source de leurs réglages. Toute modification passe par `update()`, `add_layer()`, `remove_layer()`, `move_layer()` ou `load_list()`, qui émettent `layer_changed`, `layer_added`, `layer_removed`, `layers_reordered` ou `layers_reset`, puis `changed`, et écrivent l'ancienne et la nouvelle valeur dans le journal de débogage (`laser_studio.gravure.modeles`). `engrave_layer()` : calque de la gravure des images (celui choisi dans l'onglet image, `select_engrave_layer()` → signal `engrave_layer_selected`, sinon le premier calque de gravure), dont la vitesse et la puissance sont lues à chaque usage (`engrave_speed` / `engrave_power`). Chaque calque a aussi `overscan` (surbalayage, vrai par défaut) et `laser_cmd` (`""` = commande de Configuration GRBL, `M4` dynamique ou `M3` constante, voir `LAYER_LASER_CMDS`) ; `layer_overscan_enabled()` et `layer_laser_cmd()` donnent la valeur effective d'un calque (objet ou `to_dict`) en la combinant avec le réglage global, qui reste maître pour le surbalayage (mode et distance). Un ancien projet sans ces champs garde les valeurs par défaut | `main_window`, `LayerManagerWidget`, `controllers/materials`, `controllers/layer_memory`, génération |
| **ui/app/qt_messages.py** | Filtre warnings Qt (Wayland…) | `main.py` |
| **i18n/** | Traductions FR / EN / DE / ES : `translations.py` (dictionnaire `TRANSLATIONS`, y compris thèmes, nœuds, explode, outils dessin, caméra), `language.py` (langue mémorisée, `tr()`). `from i18n import tr` | Toute l’UI |
| **grbl/connection.py** | `LaserUSBController` : connexion série au graveur (ou au graveur simulé), envoi des commandes, lecture du rapport d'état | `main_window`, `workers` |
| **grbl/simulator.py** | `SimulatedGrblSerial` : graveur GRBL 1.1 simulé (`LASER_STUDIO_SIMULATION`), imite la partie de pyserial utilisée | `grbl.connection`, `controllers/engraver` (port « SIMULATION ») |
| **camera/capture.py** | Détection des périphériques vidéo, capture d'images et gestion du flux vidéo brut via OpenCV, sans Qt. | `controllers/camera`, `ui/dialogs/camera/` |
| **camera/lens_calibration.py** | Calibration optique de l'objectif (mire d'étalonnage, matrice intrinsèque, coefficients de distorsion) et redressement des images (`undistort`), sans Qt. | `controllers/camera`, `ui/dialogs/camera/lens_wizard.py` |
| **camera/workspace_alignment.py** | Calcul de la matrice d'homographie entre les pixels redressés de la caméra et les coordonnées millimétrées du plateau laser ; redressement perspectif de l'espace de travail complet (`warp_workspace`), sans Qt. | `controllers/camera`, `ui/dialogs/camera/align_wizard.py` |
| **camera/storage.py** | Persistance et chargement des profils de calibration optique et d'alignement plateau liés à la machine (`QSettings` / fichiers JSON), sans Qt. | `controllers/camera`, `camera/` |

### 3.2 Fenêtre principale = assemblage de mixins

| Mixin / fichier | Rôle | Dépend de / appelle |
|-----------------|------|---------------------|
| **main_window.py** | `FullLaserStudio` : mixins + USB + `LayersModel` + timers. Construit la fenêtre (`init_ui` appelle les `_build_*`), crée `MachinePanel` et l'abonne à la logique (`_build_machine_panel`), fermeture, drag&drop, affichage du panneau machine et tailles du séparateur, plein écran d'un onglet, fenêtres de réglages, onglet « Éditeur vectoriel » (`_build_vector_editor_tab`, partira dans `ui/tabs/`) | Tous les mixins, `ui/machine`, `ui/statusbar`, `ui/settings/window` |
| **ui/app/menu/** | `AppActions` crée toutes les actions (icône, libellé, raccourci, état) et émet les signaux (`save_project_requested`, `mirror_changed`, `camera_requested`, `keychain_generator_requested`…) ; les outils de l'éditeur vectoriel (`vector_tool_actions` : import, boîte, puzzle, boules de Noël, porte-clés) ouvrent d'abord son onglet. `AppMenuBar` et un fichier par `QMenu` (Fichier, Paramètres, Affichage, Outils, Aide), `AppToolBar` (mêmes actions + « Générer » et, à droite, le bouton ko-fi) ne font que les ranger | `ui/buy_me_a_coffee` |
| **ui/app/window_controller.py** | Contrôleur de la fenêtre : abonne la fenêtre aux signaux de `AppActions`, `change_theme`, langue, `update_connection_widgets`, actions de la barre d'outils sur l'image de l'onglet courant, ouverture Stencil Studio, ouverture de la fenêtre Caméra ; affiche les résultats de `JobController` (console, statistiques, barre de progression, `plot_gcode_preview` vers l'aperçu 2D) | `app_theme`, `ui/app/menu`, `stencil_studio.studio_dialog`, `controllers/camera` |
| **ui/widgets/floating_toolbar.py**, **tab_close_button.py** | `FloatingToolBar` : petite barre d'outils posée par-dessus un aperçu, un canevas ou une table (aperçus d'image, séparation, PNG→SVG, aperçu 2D, onglet Calques) ; `TabCloseButton` : croix de fermeture sur un seul onglet (onglets ouverts depuis le menu Outils) | `main_window`, `ui/tabs/*` |
| **ui/tabs/image/** | `ImageTab` : onglet « Graver une image », réglages à gauche (`ImageSettingsPanel` : taille + offset, réglages photo, matière, tramage, résolution, **calque de gravure** — `EngraveLayerComboBox`, calques en mode gravure seulement, signal `engrave_layer_changed(id)` sur choix de l'utilisateur ; la fenêtre le transmet à `LayersModel.select_engrave_layer` et remplit la liste via `_refresh_engrave_layer_combo`, `vector_editing_mixin`), aperçus originale / tramé côte à côte. Émet `compare_requested`, `fullscreen_requested` ; le panneau émet `processing_changed`, `size_changed`, `material_changed`, `resolution_mode_changed`… | Construit et abonné dans `main_window._build_image_tab`, qui garde les anciens noms des champs (`spin_w`, `slider_bright`, `combo_algo`, `spin_lmm`…) |
| **ui/machine/job_position/** | `JobPositionBox` : cadre « Position du job » (origine du repère, lue par code : `origin()` / `set_origin()`) | Construit dans `main_window._build_image_tab`, placé en haut de la colonne de droite de `Preview2DTab` |
| **ui/machine/sent_gcode/** | `SentGcodeLog` : suivi du G-Code envoyé (`clear_lines`, `append_lines`, `mark_end`) | Placé à gauche par `MachinePanel` ; alimenté par `JobQueueController` (`sent_log`) et l'envoi direct (`EngraverController`, affichage par `WindowControllerMixin`) |
| **ui/machine/** | `MachinePanel` : assemble sous les onglets la rangée G-Code envoyé / connexion / pilotage / actions de job, et la barre de progression du job. Pas de signaux à lui : la fenêtre s'abonne à ceux de ses sous-panneaux ; `set_connected()` verrouille les commandes, `set_status()` répartit l'état GRBL (Connexion) et la position (sous le pilotage) | Construit et abonné dans `main_window._build_machine_panel` |
| **ui/machine/controls/** | `JogControlPanel` : jog, homing, pas, vitesse, commandes temps réel, envoi du job. Émet des signaux (`jog_requested`…), sans logique machine | Abonné : `EngraverController` (via `main_window._build_machine_panel`) |
| **ui/machine/job_actions/** | `JobActionsPanel` : cadrage, zéro, aller au zéro, répétition. Émet des signaux, construit depuis une liste d'actions (futures macros) | Abonné : `EngraverController` (via `main_window._build_machine_panel`) |
| **ui/machine/status/** | `MachineStateView` : état GRBL coloré, « Déverrouiller » visible seulement en alarme (émet `unlock_requested`), dans `ConnectionPanel`. `AxisPositionRow` : X / Y / Z à parts égales, en bas de `JogControlPanel` | Alimentés par `WindowControllerMixin._update_dro_display` → `MachinePanel.set_status` |
| **ui/machine/console/** | `DirectConsolePanel` (sans cadre, dans `ConnectionPanel`) : champ de commande GRBL avec historique (flèches) et bouton « Envoyer ». Émet `command_submitted(commande)` | Abonné : `EngraverController.send_console_command` |
| **ui/settings/machine_params/** | `MachineParamsPage` (QScrollArea) : profils machine, dimensions du lit, spot, limites. Émet `profile_selected`, `new/update/delete_profile_requested`, `bed_size_changed(l, p)`, `focal_changed(mm)`, `max_speed_changed` | Construite et abonnée dans `main_window._build_machine_params_page` ; ses champs sont liés au modèle `MachineConfig` (`ui/binding.py`), que lit la logique (`self.machine.bed_w`…) ; les anciens noms (`spin_machine_w`…) restent pour l'interface |
| **ui/settings/test_matrix/** | `TestMatrixPage` : réglages de la matrice (puissances, passes, vitesses, cases), affichage selon le mode gravure / découpe, test à partir d'une image (aperçu `TilePicker`). Émet `generate_requested`, `choose_image_requested`, `use_loaded_image_requested`, `image_test_toggled` ; fournit `matrix_params()`, `tile_settings()` ; reçoit `set_lines_mm()`, `set_source_image()` | Construite et abonnée dans `main_window._build_test_matrix_page` ; lue par `JobController.generate_test_matrix` (via `main_window._generate_test_matrix_and_show`) |
| **ui/settings/grbl_config/** | `GrblConfigPage` : commande laser, S-Max, homing, surbalayage (la page affiche la distance ou le pourcentage selon le mode), ordre de découpe sûr, décalage aller/retour, G-Code de début et de fin, réglages GRBL complets ($$). Émet `bidir_test_requested`, `scan_offset_changed`, `read_settings_requested`, `send_settings_requested`, `export_settings_requested`, `import_settings_requested`, `link_settings_to_profile_requested` | Construite et abonnée dans `main_window._build_grbl_config_page`, qui garde les anciens noms des champs (`combo_laser_cmd`, `chk_overscan`, `txt_grbl_settings`…) lus par la génération, les profils, les projets et la connexion |
| **controllers/** | Contrôleurs : objets Python ordinaires, construits par la fenêtre avec ce dont ils ont besoin, sur lesquels elle branche les signaux de l'interface. `JobController` (`controllers/job.py` : paramètres du job, contrôles avant génération, génération dans un thread, estimation rapide, export / import du G-Code, motif aller/retour, matrice de test et clic sur une case, réglages de gravure et de l'ancienne découpe SVG ; questions par `UserDialogs`, résultats par signaux `started`, `progress`, `generated`, `failed`, `imported`, `log`, `status`), `Png2SvgController` (SVG de l'onglet PNG→SVG → objets de l'éditeur vectoriel), `MatrixImageController` (matrice à partir d'une image : fichier ou image de « Graver une image », zone gravée de chaque case), `JobQueueController` (liste des jobs, sauvegarde, enchaînement des envois par l'interface `Engraver`), `ProjectController` (fichier du projet : format JSON et image en base64, boîtes Enregistrer / Ouvrir, projets récents, sauvegarde automatique et récupération ; l'état est fourni et réappliqué par `main_window._capture_project` / `_restore_project`), `layer_memory.py` (fonctions, pas une classe : `apply_saved_layers`, `settings_from` ; réglages des calques mémorisés par profil machine et réappliqués à `LayersModel`), `CameraController` (`controllers/camera.py` : orchestre la capture vidéo, applique les calibrations, projette l'image du plateau sur le canevas vectoriel et gère les assistants) | Construits dans `main_window` (`_build_png2svg_tab`, `_build_test_matrix_page`, `_build_job_queue_tab`, etc.) ; testés seuls (`tests/test_controllers.py`) |
| **ui/dialogs/camera/** | Interface et assistants de la caméra : `dialog.py` (`CameraDialog` : sélection caméra, aperçu en direct, capture de fond de plateau, lancement des assistants), `lens_wizard.py` (`LensCalibrationWizard` : étalonnage de la distorsion de lentille), `align_wizard.py` (`WorkspaceAlignmentWizard` : mire 4 points / gravure de repères pour calibrer le repère machine) | Pilotés par `controllers/camera.py` ; ouverts depuis le menu Outils / barre d'outils |
| **ui/tabs/layers/** | `LayersTab` : page de l'onglet « Calques ». Barre des profils matériaux (`material_combo`, `material_selected` sur un choix de l'utilisateur seulement, actions enregistrer / nouveau / supprimer / exporter / importer). Enveloppe `LayerManagerWidget` (encore dans `vector_layers.py`, vue abonnée à `LayersModel`), relaie `layers_changed` (= `LayersModel.changed`), `refresh()`, `link_all_to_focal()`… | Construit et abonné dans `main_window._build_layers_tab` ; lu par Stencil Studio (`lsp_bridge`) |
| **ui/tabs/preview_2d/** | `Preview2DTab` : onglet « Visualisation 2D G-Code ». Options d'affichage (inverser, négatif, déplacements rapides, optimiser le chemin), graphique pyqtgraph (`plot_widget`). `show_gcode(gcode, couleurs des calques, matrice en gravure)` dessine l'aperçu à partir du modèle `gcode/preview.py` : traits ou image reconstituée par groupe, fond de matière (à l'intérieur des découpes), légende ; `set_head_position` / `clear_head_position` : point de la tête ; `set_lines_acked`, `update_burn`, `reset_burn`, `finish_burn` : traits déjà gravés en rouge pendant un job (`BurnTracker`). À droite, séparateur réglable (position mémorisée) : colonne étroite avec `JobPositionBox` puis `JobStatsPanel` (`set_stats`). Émet `display_options_changed`, `plot_clicked(x_mm, y_mm)`, `log(texte)`, `fullscreen_requested` | Construit et abonné dans `main_window._build_2d_preview_tab` ; `WindowControllerMixin.plot_gcode_preview` lui passe le G-Code ; l'affichage du graveur (`WindowControllerMixin._on_status_updated`, `_on_stream_starting`) pilote la tête et le suivi |
| **ui/tabs/console/** | `ConsoleTab` : onglet « Console / G-Code », masqué au démarrage (menu Affichage). Console `console_edit` ; les statistiques (`JobStatsPanel` : lignes, puissance moyenne, temps estimé, fichier `job_stats_panel.py` de `ui/tabs/preview_2d/`) sont à droite de l'aperçu 2D, l'export dans « Fichier > Enregistrer le G-Code » | Construit dans `main_window._build_console_tab`, qui garde le nom `txt_console` utilisé partout |
| **ui/tabs/job_queue/** | `JobQueueTab` : onglet « File d'attente ». Liste réordonnable, boutons (le G-Code envoyé est suivi dans le panneau machine). Émet `add_current_requested`, `remove_selected_requested`, `clear_requested`, `run_requested`, `reordered` | Construit dans `main_window._build_job_queue_tab`, piloté par `JobQueueController` ; le suivi du G-Code envoyé (`SentGcodeLog`, panneau machine) sert aussi à l'envoi direct (`EngraverController.start_stream`) |
| **image_processing_mixin.py** | Image, filtres, matière, undo image | `workers`, `image.filters`, `image.size` |
| **vector_editing_mixin.py** | Import SVG/DXF, outils dessin (`set_vector_draw_tool`), alignement, nesting, duplication en série, boîtes | `vector_layers`, `vector/importers`, `vector/dxf`, `vector/nesting*`, `vector/serial_*` |
| **ui/user_dialogs.py** | `UserDialogs` : messages, confirmations (Oui / Annuler, Oui / Non) et choix de fichier, passés aux contrôleurs pour qu'ils n'ouvrent pas de `QMessageBox` / `QFileDialog` eux-mêmes ; remplacé par un faux dans les tests (`tests/job_fakes.py`) | `controllers/job` |
| **gcode/** | Génération du G-Code, fonctions pures sans Qt (aucun import de PyQt6, vérifié par `tests/test_gcode_package.py`) : `build_job_gcode` (en-tête, image, découpe SVG, calques vectoriels, fin ; résultat `GcodeResult`), `raster_image_gcode` et `image_origin` (gravure d'image, surbalayage, décalage des lignes retour), `svg_cut_gcode`, `build_vector_layers_gcode` (gravure remplie, découpe, marquage ; commande et surbalayage de chaque calque), `build_test_matrix_gcode`, `bidir_test_gcode` ; `preview` : modèle de l'aperçu 2D (`parse_preview`, `is_raster_group`, `cut_contours`, `material_background_rect`, `raster_image`, `BurnTracker`, presets matière) | `workers` (`AdvancedGCodeWorker`, `TestMatrixWorker` : simples enveloppes de thread), `controllers/job`, `controllers/engraver` (cadrage : `image_origin`) |
| **controllers/engraver.py** | `EngraverController` : ports et connexion (vérification de `$22` et `$32` après connexion), pilotage (jog, homing, zéro, cadrage, pause, reset, console directe), envoi d'un job (« Envoyer au laser » avec ses confirmations, répétition, fin de job, reconnexion), configuration GRBL (`$$` : lire, envoyer, exporter, importer). Questions par `UserDialogs`, résultats par signaux (`ports_changed`, `stream_starting`, `stream_ended`, `direct_job_started`…) ; `start_stream` / `end_stream` servent aussi à la file d'attente | `controllers/machine_connection`, `grbl/commands`, `main_window`, `window_controller` |
| **grbl/commands.py** | Commandes GRBL sans Qt : `HOME`, `UNLOCK`, `SET_WORK_ZERO`, `GO_TO_WORK_ZERO`, `jog_command`, `frame_commands`, `parse_grbl_settings`, `setting_lines`, `homing_support` (base des futures macros) | `controllers/engraver`, `controllers/machine_connection` |
| **controllers/machine_connection.py** | `MachineConnection` (`QObject`, sans boîte de dialogue) : port série, threads (sondage de l'état, envoi du job, commandes, reconnexion après coupure), état « référencé » (`homed`), dernier job envoyé, `read_settings()` ($$). Signaux : `connection_changed`, `status_updated`, `log`, `position_lost`, `stream_progress` / `stream_lines_sent` / `stream_lines_acked`, `reconnecting` / `reconnected` | `grbl.connection`, `workers` |
| **separation_mixin.py** | Séparation couleur côté interface : boîtes de dialogue, aperçus affichés, test du gain ; abonné aux signaux de `SeparationController` | `controllers/separation`, `workers` |
| **controllers/separation.py** | `SeparationController` (`QObject`, sans boîte de dialogue) : image source, tonalité cadrée sur la plaque envoyée à « Graver une image » (`tone_ready`), aperçus (original, gravure, impression, simulation) avec cache du calque couleur, export (PNG et PDF 1:1), réglages du verre appliqués à `ImageSettings` puis rendus (`apply_glass_settings` / `release_glass_settings`) | `image.separation`, `models/separation`, `models/image_settings` |
| **models/separation.py** | `SeparationSettings` (`SettingsModel`) : plaque, résolution d'impression, gain de point, saturation, clarté, miroir d'impression, diffusion, intensité ; liés aux champs de `SeparationTab` (le cadrage reste lu par `SeparationTab.frame_args`) | `controllers/separation` |

### 3.3 Vectoriel (cœur édition)

| Fichier | Rôle | Utilisé par |
|---------|------|-------------|
| **vector_layers.py** | Tableau des calques (`LayerManagerWidget`, vue de `LayersModel` ; `LayerManager` reste un alias de `LayersModel` ; colonnes Couleur, Nom, Mode, Puissance, Vitesse, Passes, Pas, Surbalayage — grisée hors gravure remplie —, Laser — Auto / M4 / M3 —, Actif), `extract_vector_layer_data` (objets → polygones en mm pour `gcode/vector`), objets (`TextObject`, `ShapeObject`, `SvgPathObject`), **`VectorCanvasView`** (supporte aussi l'affichage de l'image de fond du plateau issue de la caméra) | Éditeur, G-Code, profils, caméra |
| **vector/importers.py** / **vector/dxf.py** | Import SVG/DXF (groupé par défaut) | `vector_editing_mixin` |
| **vector/svg_import.py** | Import SVG selon la convention des modèles (`resources/library/README.md`) : seuls les calques `Cut`, `Engrave` (noir gravé, blanc creusé) et `Mark` sont importés ; options = sous-calques d'un groupe, un seul visible (`find_variant_groups`) ; textes en objets texte modifiables (`TextObject`, calés sur le rendu SVG) et remplaçables (`find_texts`) ; aperçu tel qu'importé (`svg_preview`) ; unités et transformations cumulées. Utilisé par la bibliothèque ; à valider pour remplacer `extract_svg_objects` | `controllers/library`, `ui/dialogs/library` |
| **library/catalog.py** | Catalogue de la bibliothèque, sans Qt : catégories et modèles des dossiers `resources/library/` (à côté de l'exécutable et dans le bundle), `_category.json`, `info.json`, aperçu, readme | `controllers/library` |
| **controllers/library.py** | `LibraryController` : ouvre la bibliothèque (taille des aperçus mémorisée), importe le modèle choisi avec ses variantes, chaque rôle sur le calque de base de même rôle | `main_window`, `window_controller` |
| **vector/order.py** / **vector/nudge.py** / **vector/font.py** | Ordre de coupe, nudge clavier, polices | Éditeur |
| **vector/text_on_path.py** | Texte le long d'un tracé quelconque, sans Qt : `path_placements(advances, points, center_fraction, spacing, reverse, gap)` donne `(x, y, rotation)` de chaque lettre (direction = corde sous la largeur de la lettre ; prolongement droit au-delà d'un tracé ouvert, bouclage sur un tracé fermé). `orient_path` (fermé : sens horaire ; ouvert : de gauche à droite), `default_center_fraction`, `is_closed`, `relative_points`, `scaled_points`. Testé dans `tests/test_text_on_path.py` | `vector_layers.TextObject._follow_path` |
| **vector/text_on_arc.py** | Texte sur un cercle, sans Qt : `arc_placements(advances, rayon, centre, intérieur, espacement)` donne `(x, y, rotation)` de chaque lettre (repère mathématique, Y vers le haut, centre du cercle en (0, 0) ; 90° = haut, 270° = bas), `arc_span_deg`, `text_length`, `default_center_deg`. Extérieur : lettres vers l'extérieur, lu dans le sens horaire ; intérieur : lettres vers le centre, lu de gauche à droite en bas. Testé dans `tests/test_text_on_arc.py` | `vector_layers.TextObject` |
| **vector/box_generator.py** / **box_3d.py** / **box_presets.py** | Boîte à encoches, modèle 3D de la boîte assemblée (aperçu), préréglages nommés | `vector_editing_mixin`, `ui/dialogs/box_generator` |
| **vector/puzzle_generator.py** / **vector/nesting.py** / **vector/nesting_apply.py** | Puzzle jigsaw, imbrication | `vector_editing_mixin`, `ui/dialogs` |
| **vector/ornament_generator.py** / **ornament_motifs.py** / **ornament_region.py** / **keychain_generator.py** | Boules de Noël (géométrie, motifs, soudure) et porte-clés prénom (voir §8.0 et §8.2) | `vector_editing_mixin`, `ui/dialogs/ornament`, `ui/dialogs/keychain` |
| **vector/serial_duplicate.py** / **vector/serial_apply.py** | Duplication en série : exemplaires, texte par exemplaire, grille (logique pure, testée sans Qt) ; passerelle vers le canevas et l'imbrication | `vector_editing_mixin`, `ui/dialogs/serial_duplicate` |
| **vector/jig.py** | Gabarit de placement : géométrie de la plaque et des poches (logique pure, testée sans Qt) ; les objets sont créés par `vector/importers.jig_to_objects` | `vector_editing_mixin`, `ui/dialogs/jig` |

#### Générateur de boîte (`vector/box_generator.py`)

| Élément | Description |
|---------|-------------|
| `BoxParams` | Dimensions, épaisseur, kerf, doigts, **`lid_type`** (`none` / `finger` / `lip` / `sliding` / `hinged` / `pinned`), **`clearance`** (jeu des assemblages libres), **`dividers_x` / `dividers_y`**, pieds (`foot_size`, `foot_layers`), motif gravé au centre du dessus (`engrave_motif`, `motif_size`, `motif_shape` : papillon / feuille / étoile / mandala), charnières (`HINGE_STYLES` : rond / papillon, `MAX_HINGES`), encoche d'ouverture (`HANDLE_LIDS`) et aimants (`MAGNET_LIDS`) |
| `build_box()` | Parois à doigts + couvercle selon le type + cloisons ; renvoie des `Panel` (contour `cut`, trous `holes`) |
| `rectilinear_loops()` | Union / différence de rectangles → contours (extérieur anti-horaire, trous horaires) ; `rectilinear_outline()` en est l'enveloppe à un seul contour |
| Couvercles | `lip` : plaque + rebord (`top`, `lip`) ; `sliding` : façade abaissée, rainure dans `left` / `right`, plaque `top` plus petite ; `hinged` : charnière vivante d'une seule pièce (paroi arrière prolongée par une zone à fentes) ; `pinned` : charnière à axe (plaques percées empilées autour d'une tige, une sur deux dans la paroi arrière) |
| Aperçu 3D | `vector/box_3d.py` (sans Qt) : faces planes, projection, tri de l'arrière vers l'avant (algorithme du peintre), ouverture du couvercle selon la charnière (`LivingHinge`). `Box3DView` (`preview_3d.py`) : rendu QPainter sans OpenGL, glisser = tourner, molette = zoom, double-clic = vue de départ |
| Préréglages | `vector/box_presets.py` : jeux de réglages nommés, JSON dans le dossier de données de l'utilisateur ; calques et décors non mémorisés |
| Cloisons | `divider_x<n>` / `divider_y<n>` ; fentes ajoutées en trous dans `front`/`back`/`left`/`right`/`bottom` ; emboîtement à mi-hauteur au croisement |
| `importers.box_to_objects` | Un objet par trou puis un par contour ; la même `Panel` peut donc apparaître plusieurs fois. `motif_to_objects` (motif gravé), `index_to_objects` (numéros de pièces gravés) et `decor_to_objects` complètent |
| Tests | `tests/test_box_generator.py` (contrôle 3D : aucune collision entre pièces, volume exact avec jeu nul), `test_box_3d.py`, `test_box_presets.py`, `test_box_dialog_smoke.py` |


#### Capacités du canevas (`VectorCanvasView`)

| Fonction | Description |
|----------|-------------|
| Import groupé | SVG/DXF arrivent en **un seul objet** (`ungroup=False` par défaut) |
| Dégrouper | Clic droit → sous-tracés indépendants (`ungroup_selected`) |
| **Exploser en segments** | Chaque arête = un objet (`explode_selected`) — supprimer une encoche / un trait |
| **Édition de nœuds** | Poignées jaunes : déplacer, double-clic = ajouter, Suppr = retirer |
| Outils dessin | `line`, `rect`, `circle`, `ellipse` (`set_draw_tool`). Rectangle : 3 points (2 clics pour la base, puis tirer la profondeur). Cercle : clic-glisser du centre vers le bord. Ellipse : clic-glisser d'un coin du cadre à l'autre. Cercle et ellipse se tracent d'un seul geste (`_draw_pressed` : relâcher après un glissé crée la forme, un simple clic attend le 2e clic) ; au clavier, le cercle prend un rayon, l'ellipse « L x H ». Aperçu : `_shape_preview_path` |
| Texte le long d'un objet | Sélectionner un texte et un autre objet (cercle, ellipse, courbe, forme importée…) puis clic droit ou bouton « Texte le long de l'objet » : `make_text_follow_object` COPIE le plus long contour du guide (`_guide_polyline`, courbes aplaties au 1/20 mm) dans `TextObject.follow_points` (mm, relatif à l'origine du texte, Y vers le haut) ; le guide n'est pas modifié. Réglages : `follow_center` (position 0 à 1, par défaut le point le plus haut d'un contour fermé), `follow_reverse`, `follow_gap_mm`, modifiables dans `TextInsertDialog` (qui permet aussi de détacher ; elle s'ouvre dès que le bouton réussit, et n'affiche alors pas les champs « sur un cercle »). Côté « intérieur » (`follow_reverse`) : la position passe au point le plus bas du contour (`default_center_fraction(points, inside=True)`), seul endroit où le texte se lit à l'endroit. Calcul pur dans `vector/text_on_path.py`. Prioritaire sur le texte sur un cercle ; copie : si le guide change, le texte ne suit pas |
| Texte sur un cercle | `TextObject.arc_radius_mm` (0 = texte droit), `arc_inside`, `arc_center_deg` (`None` = haut ou bas selon le côté) ; réglés dans `TextInsertDialog` (rayon, côté, angle). `_arc_path` place et tourne chaque lettre rigide selon `vector/text_on_arc` ; le rayon suit la mise à l'échelle. Les anciens projets sans ces champs se relisent comme texte droit (`getattr`). Pas pour le texte vertical |
| Grouper / aligner / distribuer | Sélection multiple |
| Fond caméra | Affichage calibré du plateau laser en arrière-plan pour le placement précis des pièces |
| Undo / redo | Snapshots sur le canevas |

### 3.4 Thèmes & icônes

| Élément | Rôle |
|---------|------|
| **ui/app/theme.py** | 7 thèmes : `dark`, `light`, `dusk` (gris-bleu), `warm` (gris chaud ambré), `neon`, `retro80` (synthwave), `jarvis` (HUD cyan) |
| Menu **Paramètres → Thème** | `available_themes()` + `change_theme()` ; persistance `QSettings("app_theme")` |
| **resources/icons/breeze/**, **jarvis/** | Packs embarqués (LGPL-3). `install_breeze_icon_theme()` active Breeze, ou Jarvis si le thème enregistré est jarvis ; `apply_icon_theme_for_ui()` bascule entre les deux au changement de thème. Un thème système déjà actif n'est pas écrasé. Cherchés comme les images (`resource_candidates`) |
| **packaging/ / BUILD.md** | `packaging/pyinstaller/LaserStudioPro.spec` embarque `src/laser_studio/resources/` (images et packs d'icônes) et Stencil Studio ; `bundle_filter.py` retire les fichiers Qt inutiles |

### 3.5 Stencil Studio

| Fichier | Rôle |
|---------|------|
| **studio_dialog.py** | Fenêtre QtWebEngine intégrée ; `theme_for_lsp()` mappe les 7 thèmes (`LSP_THEME_DARK`, `_LIGHT`, `_DUSK`, `_WARM`, `_NEON`, `_RETRO80`, `_JARVIS`) ; `sync_theme_from_lsp()` à chaud |
| **lsp_bridge.py** | Intercepte exports SVG/DXF → import dans l’éditeur vectoriel |
| **studio.py** | Serveur HTTP local + logique de conversion |

Thèmes Studio (`LSP_THEME_*`) alignés sur les palettes LSP. `selftest.py` vérifie que les bibliothèques d'un PC (OpenCV, numpy, scipy) donnent les mêmes résultats que les valeurs attendues.

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
        │                 ├─► open_stencil_studio ──► studio_dialog
        │                 │       (theme_for_lsp / sync_theme_from_lsp)
        │                 └─► CameraController ──► camera/ (capture, lens_calibration, workspace_alignment, storage)
        │                                      └─► ui/dialogs/camera/ (dialog, lens_wizard, align_wizard)
        ├─ VectorEditingMixin ──► VectorCanvasView (vector_layers)
        │         ├─ import SVG/DXF (groupé)
        │         ├─ set_vector_draw_tool (line/rect/ellipse)
        │         ├─ explode_selected / enter_node_edit
        │         └─ nesting / box_generator / puzzle_generator
        ├─ JobController (controllers/job) ──► workers (threads) ──► gcode/ (G-Code sans Qt)
        │         └─ signaux ──► WindowControllerMixin (console) ──► Preview2DTab ◄── gcode/preview (aperçu sans Qt)
        └─ EngraverController (controllers/engraver) ──► MachineConnection ──► grbl.connection / grbl.simulator ; grbl/commands
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
    ├─ apply_app_theme(app, name)     # palette + stylesheet + pack d'icônes (breeze / jarvis)
    └─ si Stencil Studio ouvert → sync_theme_from_lsp(name)
```

### 5.4 Stencil Studio → LSP
Export SVG/DXF dans le Studio → `lsp_bridge` / download handler → objets sur le canevas vectoriel (même règle d’import groupé).

### 5.5 Caméra & alignement plateau

```
Menu Outils → Caméra (CameraDialog)
    ├─► Assistant Calibration Optique (LensCalibrationWizard)
    │     └─► camera.lens_calibration → sauvegarde matrice intrinsèque / distorsion (camera.storage)
    ├─► Assistant Alignement Plateau (WorkspaceAlignmentWizard)
    │     └─► gravure de repères ou pointage 4 coins → camera.workspace_alignment (homographie) → camera.storage
    └─► Capture du fond de plateau
          └─► capture brute → undistort() → warp_workspace() → affichage sur VectorCanvasView
```

---

## 6. Principes d’architecture à respecter

1. **Mixins additifs** : ne pas casser les responsabilités (UI ≠ G-Code ≠ USB).
2. **Repère machine** : origine bas-gauche, Y vers le haut dans le modèle monde ; conversion écran dans `VectorGraphicsItem.refresh`.
3. **Import vectoriel groupé par défaut** ; dégroupage / explosion **explicites** (clic droit ou boutons).
4. **Thème unique source de vérité** : `ui.app.theme.THEMES` + `QSettings("app_theme")` (relu par `apply_saved_theme`) ; Stencil Studio consomme via `theme_for_lsp`.
5. **Undo canevas** : toute mutation géométrique (nœuds, explode, dessin) doit appeler `push_undo_snapshot()` avant modification.
6. **i18n** : toute nouvelle chaîne UI passe par `tr("…")`, avec sa clé dans `i18n/translations.py`.
7. **Ressources** : images dans `resources/`, chargées via `find_resource` ; pack d'icônes `resources/icons/` ; penser à `--add-data "resources;resources"` dans les builds.
8. **Logique caméra découplée de Qt** : les calculs de distorsion (`lens_calibration.py`), d'homographie (`workspace_alignment.py`) et de capture (`capture.py`) résident dans `camera/` sans dépendance PyQt6 pour rester testables unitairement.

---

## 7. Évolutions récentes (mémo)

| Domaine | Ajout |
|---------|--------|
| Thèmes | `dark`, `light`, `dusk`, `warm`, puis **`neon`**, **`retro80`**, **`jarvis`** (`ui/app/theme.py`) |
| Icônes | Packs **Breeze** et **Jarvis** embarqués (`resources/icons/`) |
| Import | Plus de dégroupage automatique SVG/DXF |
| Dessin | Outils souris ligne / rectangle / ellipse |
| Édition | **Exploser en segments** + **mode nœuds** |
| Stencil Studio | Thème lié à LSP (7 thèmes, sync à chaud), autotest `selftest.py` |
| UI claire | Stylesheet dédié (boutons ±, spinbox, etc.) |
| Sécurité | Avertissement laser au démarrage (`controllers/startup_safety`, `ui/dialogs/startup_safety`), rappel périodique, `NOWARNING` pour les tests |
| Machine | `grbl/ports.py` : ports virtuels masqués, dernier port mémorisé ; aide « Port introuvable ? ». Pilotage du graveur dans `EngraverController`, commandes dans `grbl/commands.py` ; `LaserControlMixin` supprimé |
| Boîte | Couvercles `hinged` / `pinned`, pieds, aimants, motifs gravés, aperçu 3D, préréglages |
| Générateurs | Porte-clés prénom (`keychain_generator`), motifs de boules de Noël (`ornament_motifs`) |
| Interface | `FloatingToolBar` sur les aperçus, `TabCloseButton` |
| Texte | Texte sur un cercle (médailles, tampons), voir `vector/text_on_arc.py` ; texte le long de n'importe quel objet, voir `vector/text_on_path.py` |
| Dessin | Boutons séparés cercle / ellipse, tracés d'un seul geste ; le rectangle garde ses 3 points ; icônes `draw-circle` et `text-follow-path` (Breeze et Jarvis) |
| Modes de calque | Codes indépendants de la langue (`models/layer_modes`) ; matériau choisi enregistré automatiquement |
| G-Code | Génération sortie des threads et de `vector_layers` dans le paquet `gcode/`, sans Qt et testée seule ; G-Code inchangé. Préparation du job dans `JobController` (`controllers/job.py`), boîtes de dialogue par `UserDialogs`. Aperçu 2D : modèle `gcode/preview.py`, dessin dans `Preview2DTab` ; `GcodeGenerationMixin` supprimé |
| Build | `packaging/pyinstaller/` (spec commun, filtre), AppImage, workflows `tests.yml` / `release.yml` ; numpy 2, OpenCV headless |
| Caméra | Module `camera/` (calibration objectif, alignement homographique du plateau) + assistants (`ui/dialogs/camera/`) + superposition sur le canevas vectoriel |

---

## 8. Générateur de Puzzle

| Fichier | Rôle |
|---------|------|
| **vector/puzzle_generator.py** | Géométrie jigsaw (ergot à col étroit et tête ronde qui déborde : 3 Béziers, dimensionné sur la plus petite dimension d'une pièce, hauteur plafonnée par `MAX_TAB_DEPTH` = 0,30) + grille ondulée ; validation ; `PuzzleResult` : `pieces` (aperçu seulement), **`outline`** (contour extérieur fermé, agrandi de kerf/2) et **`edges`** (arêtes internes, chacune une seule fois, tracés ouverts) |
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
**Tracés ouverts** : `build_vector_layers_gcode` ne referme plus un tracé ouvert (sinon aller-retour = double passage) ; seuls les tracés quasi fermés (`CLOSE_GAP_MM`) le sont. Tests : `tests/test_puzzle_cut_once.py` (un passage par arête) et `tests/test_puzzle_shape.py` (forme de l'ergot, aucun croisement et jeu ≥ 0,10 × la plus petite dimension d'une pièce sur toute la plage des curseurs, contour coupé en dernier).
**Jeu entre traits** : un ergot trop haut, ou un gros ergot décalé vers un coin, finit par toucher l'ergot voisin (pont de bois trop fin, trait fondu). La hauteur est donc plafonnée (`MAX_TAB_DEPTH`) et le décalage aléatoire (`pos_random`) diminue quand l'ergot est profond, jusqu'à zéro à la hauteur maximale.
`PuzzleError` → message traduit `puzzle.err.<code>`.

## 8.0 Générateur de boules de Noël

| Fichier | Rôle |
|---------|------|
| **vector/ornament_generator.py** | Géométrie pure, sans Qt : disque, anneau d'accroche (anneau ou bouchon), flocons (3 styles, un seul contour simple chacun), suspentes, guirlande, motifs droits, barre de soutien, échelle et position du prénom, réglage `motif_drop` (écart du motif à l'anneau, avec une tige qui garde le contact) (`OrnamentGeometry`, `OrnamentError`) |
| **vector/ornament_motifs.py** | Motifs, géométrie pure : étoiles, sapins, Père Noël, bonhomme de neige, cadeau, lune, houx, bougie, cloche, boule… (`MotifShape` : `solids` soudés, `cuts` découpés, `late` ajoutés après les découpes) |
| **vector/ornament_region.py** | Soudure avec les opérations booléennes de `QPainterPath` : texte (`QFont` → contour), union des formes, soustraction du vide intérieur et du trou, rognage au disque. Renvoie les contours à découper, le premier est l'extérieur |
| **ui/dialogs/ornament/** | `OrnamentGeneratorDialog` : prénom, police, accroche, motif, disposition, aperçu des contours réellement découpés (recalculé 150 ms après la dernière modification) |
| **vector/importers.ornament_to_objects** | Contours → 2 `SvgPathObject` : l'extérieur, et un objet qui regroupe tous les contours intérieurs |
| **vector_editing_mixin.open_ornament_generator** | Ouverture du dialogue et placement sur le canevas |
| **i18n/translations.py** | Clés `menu.tools.ornament`, `ui.vector_ornament_generator*`, `ornament.*`, `ornament.err.*` |

Principes : le prénom, les flocons et l'anneau sont **soudés** en une seule pièce avant d'être envoyés au laser : un contour qui traverse de la matière serait découpé à l'intérieur d'une lettre. Les lettres sont d'abord fusionnées (écritures cursives), leurs contreformes (a, e, o) restent des contours à part. Le prénom est tenu à l'anneau par une barre posée sur la ligne de base (choix « Barre », par défaut) ; sans elle il doit toucher l'anneau des deux côtés (`floating_name` avertit sinon). Un point de i ou un accent reste détaché et tombe. Tests : `tests/test_ornament_generator.py` (formes et disposition sans Qt ; soudure avec le vrai Qt, ignorée sans lui).

## 8.1 Stencil Studio → calques multiples (lsp_bridge)

Export Studio vers LSP : routage par nom de calque DXF / groupe SVG

| Nom export | Calque LSP |
|------------|------------|
| CUT / FRAME | Découpe (existant ou créé) |
| ENGRAVE / MARK | Gravure / Marquage |
| LAYER_n | Calque dédié « LAYER n » (créé si besoin), mode Découpe, réglages repris du premier calque découpe (+ focale si liée) |

Fichier : **stencil_studio/lsp_bridge.py** (`ensure_multi_layer`, `kind_for_layer_name`, `pick_layer`).

## 8.2 Porte-clés prénom (NameKey)

| Fichier | Rôle |
|---------|------|
| **vector/keychain_generator.py** | Géométrie pure, sans Qt (`build_keychain`, `KeychainParams`, `KeychainResult`, `KeychainError`) : prénom, base dilatée soudée à l'anneau. Deux ensembles de polygones fermés : `base_contours` (base + trou d'anneau → calque Découpe) et `text_contours` (texte centré sur la base → calque Gravure). Repère LSP (mm, Y vers le haut, coin bas-gauche en (0, 0)) |
| **ui/dialogs/keychain/** | `KeychainGeneratorDialog` + `KeychainPreview` : aperçu en direct découpe + gravure ; `error_text()` |
| **vector/importers.keychain_to_objects** | Contours → objets sur le calque de découpe et celui de gravure |
| **vector_editing_mixin.open_keychain_generator** | Ouverture du dialogue (réglages mémorisés dans `_keychain_settings`) et placement sur le canevas ; lancé par le bouton de l'éditeur, le menu Outils (`keychain_generator_requested`) |

## 9. Commandes utiles

```bash
# Lancer l’application
python main.py

# Lancer Stencil Studio seul
python main.py --stencil-studio

# Tests (comme le workflow tests.yml)
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests

# Qualité traductions / UI
python tools/check_translations.py
python tools/check_ui_attributes.py

# Compilation syntaxe rapide
python -m compileall -q main.py src
```

---

*Document d’architecture — à tenir à jour lors des changements structurants (nouveaux mixins, flux d’import, thèmes, pont Stencil Studio, caméra, arborescence).*