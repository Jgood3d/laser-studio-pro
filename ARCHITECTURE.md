# Laser Studio Pro — Architecture & cartographie du code

> Document mis à jour pour faciliter la prise en main et la modification du projet.  
> Branche de référence : **Dev** — dépôt : https://github.com/Jgood3d/laser-studio-pro  
> Version applicative : **3.0.0** (voir `core/version.py`)

Ce fichier regroupe :
0. Le glossaire : chaque objet du code, en une phrase
1. L’arborescence complète
2. Le rôle de chaque module / fichier
3. Les liens de dépendance (qui utilise qui)
4. Les flux principaux
5. Les évolutions récentes (thèmes, générateurs, boîte 3D, Stencil Studio, icônes, caméra, avertissement de démarrage)

---

## 0. Glossaire

Les objets dont on parle tout le temps, en une phrase, et où les trouver (chemins sous `src/laser_studio/`). Le
détail de chaque fichier est plus bas, section 2.

**Le dessin (éditeur vectoriel)**

| Objet | En clair | Fichier |
|---|---|---|
| `VectorDocument` | le dessin : la liste des objets dans l'ordre d'empilement, annuler / refaire, presse-papiers | `models/vector_document.py` |
| `VectorObject` | un objet du dessin, en mm : position, rotation, miroirs, calque | `models/vector_objects.py` |
| `TextObject`, `ShapeObject`, `SvgPathObject` | un texte, une forme simple (rectangle, ellipse, ligne, polygone), un tracé importé ou dessiné | `models/vector_objects.py` |
| `GroupObject` | un groupe : ses objets restent entiers ; avec une opération (union, différence…), ils forment un seul tracé | `models/vector_objects.py` |
| `WorkArea` | le plateau : sa taille, l'échelle de l'écran, le passage mm ↔ écran, la grille graduée (sans Qt) | `vector/work_area.py` |
| `VectorCanvasView` | le canevas : la vue du dessin, qui passe la souris et le clavier aux outils | `ui/vector_editor/canvas.py` |
| `VectorGraphicsItem` | un objet du dessin tel qu'affiché sur le canevas | `ui/vector_editor/item.py` |
| `DocumentItems` | la correspondance objets du dessin ↔ éléments affichés, et la sélection | `ui/vector_editor/document_items.py` |
| `WorkAreaLayer`, `CameraLayer` | le plateau gradué, et l'image de la caméra posée dessous | `ui/vector_editor/scene_layers.py` |
| `ViewNavigator` | le zoom et le cadrage du canevas | `ui/vector_editor/navigation.py` |
| `DrawingTool`, `MeasureTool`, `NodeEditor`, `MoveTool`, `EndpointSnap`, `FollowHandle` | les outils de la souris : dessiner, mesurer, modifier les sommets, déplacer, s'accrocher aux extrémités, glisser un texte le long de son contour | `ui/vector_editor/tools/` |
| `VectorEditorController` | les actions de l'éditeur : insérer, modifier, transformer la sélection, placer un dessin importé | `controllers/vector_editor.py` |
| `VectorImporter` | l'import d'un SVG, d'un DXF ou d'un export de Stencil Studio | `controllers/vector_import.py` |
| `GroupingActions` | grouper, combiner, dégrouper, éclater en segments | `controllers/grouping_actions.py` |
| `TextFollowActions` | le texte qui suit un contour, le texte de médaille | `controllers/text_follow_actions.py` |
| `ObjectListActions` | les actions de la liste des objets : ordre, nom, œil, ignorer, poubelle | `controllers/object_list_actions.py` |
| `GeneratorsController`, `LayoutController` | les générateurs (boîte, puzzle, boule, porte-clés…) ; l'imbrication et la duplication en série | `controllers/generators.py`, `controllers/layout.py` |

**Les réglages (modèles)**

| Objet | En clair | Fichier |
|---|---|---|
| `SettingsModel` | la base des réglages nommés : chaque changement est signalé et noté dans le journal | `models/settings.py` |
| `LaserLayer`, `LayersModel` | un calque (mode, puissance, vitesse, passes, ponts, kerf, air…) et la liste des calques | `models/layers.py` |
| `MachineConfig` | le graveur : taille du plateau, taille du spot, vitesse et accélération maximales | `models/machine.py` |
| `GrblConfig` | la configuration GRBL : commande laser, S-Max, homing, surbalayage, puissance du cadrage, G-Code de début et de fin | `models/grbl.py` |
| `JobPlacement` | où se place le travail sur le plateau : taille, décalage, origine, lignes/mm | `models/job_placement.py` |
| `ImageSettings` | les réglages de tramage de l'image : luminosité, contraste, négatif, algorithme… | `models/image_settings.py` |
| `MaterialsModel` | les matériaux (réglages de tous les calques pour une matière) et le matériau choisi | `models/materials.py` |
| `MacrosModel`, `JobHistory` | les macros de l'utilisateur ; l'historique des gravures | `models/macros.py`, `models/job_history.py` |
| `machine_state` | l'état du graveur (prêt, alarme, homing, gravure…) et la seule table de ce qui est permis dans chaque état | `models/machine_state.py` |

**Le G-Code et le graveur**

| Objet | En clair | Fichier |
|---|---|---|
| `JobParams` | tous les réglages d'un travail, figés au moment de générer | `gcode/params.py` |
| `GcodeResult` | le résultat d'une génération : le G-Code, son nombre de lignes, la puissance moyenne, la durée estimée | `gcode/common.py` |
| `LaserMoves` | l'écriture des mouvements du laser (G0 / G1, puissance), sans répétition inutile | `gcode/common.py` |
| `PreviewData`, `BurnTracker` | le G-Code lu pour l'aperçu 2D ; le suivi des traits déjà gravés pendant un travail | `gcode/preview.py` |
| `JobController` | la préparation et la génération du travail | `controllers/job.py` |
| `MachineConnection` | le dialogue avec le graveur : port, envoi, état | `controllers/machine_connection.py` |
| `CharacterCountingStream` | l'envoi ligne à ligne en remplissant au mieux la mémoire de GRBL | `grbl/streaming.py` |
| `EngraverController` | le pilotage : connexion, déplacements, cadrage, envoi, reprise d'un travail interrompu | `controllers/engraver.py` |
| `JobQueueController` | la file d'attente des travaux | `controllers/job_queue.py` |

**La fenêtre**

| Objet | En clair | Fichier |
|---|---|---|
| `FullLaserStudio` | la fenêtre principale : elle crée les modèles et les contrôleurs et les relie | `ui/app/main_window.py` |
| `WindowState` | ce que la fenêtre enregistre et restaure : réglages du démarrage, profils machine, projet | `ui/app/window_state.py` |
| `WindowController` | les actions transversales : fenêtres de réglages, caméra, Stencil Studio, langue, thème | `controllers/window.py` |
| `ProjectController` | le fichier projet : enregistrer, ouvrir, projets récents, sauvegarde automatique | `controllers/project.py` |
| `AppActions` | toutes les actions des menus et de la barre d'outils, et leurs raccourcis | `ui/app/menu/actions.py` |
| `UserDialogs` | les questions et les messages à l'utilisateur, pour que les contrôleurs n'ouvrent pas de fenêtre eux-mêmes | `ui/user_dialogs.py` |

---

## 1. Vue d’ensemble du flux de démarrage

```
main.py
  │
  ├─► (option) --stencil-studio → stencil_studio.ui.window (Studio dans son propre processus)
  │
  ├─► install_qt_message_filters / setup_debug_logging
  ├─► QApplication
  ├─► StartupSplash                 # affiché le plus tôt possible
  ├─► install_breeze_icon_theme()   # pack d'icônes embarqué : breeze, ou jarvis si ce thème est choisi
  ├─► apply_saved_theme()           # ui/app/theme.py : 7 thèmes, relu dans QSettings("app_theme")
  ├─► StartupSafetyPolicy           # controllers/startup_safety.py : avertissement laser
  │     └─ confirm_startup_safety() # ui/dialogs/startup_safety/ ; « Annuler » quitte avant la fenêtre
  ├─► open_first_steps()            # ui/dialogs/first_steps/ : Premiers pas, tant que la case reste cochée
  │
  └─► ui/app/main_window.py  (classe FullLaserStudio : assemble la fenêtre, init_ui)
        │
        │  N'hérite d'aucun mixin. Ce qui agit sur la fenêtre est dans ui/app/ :
        │
        ├─ window_controller = WindowController   menus, thème, langue, aide, caméra, fenêtres de réglages, matrice de test, résolution et focale de « Graver une image », comparaison des tramages, outils de dessin
        ├─ state             = WindowState        ce qui s'enregistre et se restaure : réglages machine, profil machine, projet, matériau choisi
        ├─ tabs              = MainTabs           onglets, croix des onglets du menu Outils, plein écran, séparateurs
        ├─ job_display       = JobDisplay         résultats du job (console, statistiques, aperçu 2D), état du graveur (position, suivi d'envoi)
        └─ image_actions     = ImageToolbarActions pivoter / supprimer / miroirs sur l'image de l'onglet affiché
        │
        │  Et crée les contrôleurs (controllers/), des objets ordinaires
        │  qui reçoivent ce dont ils ont besoin :
        │
        ├─ connection    = MachineConnection      port série, threads, état « référencé »
        ├─ engraver      = EngraverController     pilotage du graveur : ports, connexion, jog, envoi des jobs, configuration $$
        ├─ job           = JobController          paramètres, génération du G-Code, estimation, export, matrice de test
        ├─ vector_editor = VectorEditorController éditeur vectoriel : import, insertion, alignement, générateurs, imbrication, série
        ├─ project       = ProjectController      fichier du projet, récents, sauvegarde automatique
        ├─ machines      = MachineProfilesController profils machine (champs : ProfileFields)
        ├─ matrix_image  = MatrixImageController  matrice de test à partir d'une image
        ├─ materials     = MaterialsController    profils matériaux (modèle MaterialsModel)
        ├─ png2svg       = Png2SvgController      envoi du SVG vers l'éditeur vectoriel
        ├─ job_queue     = JobQueueController     file d'attente (graveur : interface Engraver)
        ├─ image         = ImageController        « Graver une image » : image source, taille, tramage dans un thread, comparaison des algorithmes (vue : ui/tabs/image/)
        ├─ separation    = SeparationController   séparation couleur : image, tonalité, aperçus, export (vue : ui/tabs/separation/)
        └─ camera        = CameraController       créé à la demande par WindowController : capture, calibration optique, alignement plateau
```

Le code vit dans `src/laser_studio/` : le `main.py` de la racine n'ajoute que `src/` au `sys.path` et appelle `laser_studio.main.main()` (`python -m laser_studio` fonctionne aussi une fois installé, voir `pyproject.toml`). La fenêtre principale s'affiche une fois `SPLASH_SCREEN_DURATION` écoulé, et le thème est réappliqué après la construction de l'interface.

`FullLaserStudio` est le **point d'assemblage** : il construit la fenêtre, crée les modèles, les contrôleurs et les objets de `ui/app/`, et les relie par leurs signaux. Il garde la lecture de la taille et de la position du job pour les contrôleurs (`_job_geometry`, `_image_frame`) et les messages (`show_status_message`, `log_message`, utilisés aussi par Stencil Studio).

---

## 2. Arborescence complète

```
laser-studio-pro/
├── main.py                           # lance l'application depuis le dépôt (ajoute src/ au chemin) et point d'entrée PyInstaller
├── pyproject.toml                    # disposition src/ : paquets laser_studio, laser_common et stencil_studio ; version lue dans core/version.py
├── requirements-linux.txt / requirements-windows.txt   # dépendances par plateforme
├── requirements_principal.txt        # versions exactes figées pour les builds
├── .copr/Makefile                    # paquet source (SRPM) construit par Copr depuis le commit courant, voir packaging/fedora/
├── .github/workflows/                # tests.yml (unittest hors écran ; job checks : ruff + check_ui_attributes), release.yml (tag vX.Y.Z → Linux AppImage et .deb, Windows, macOS, release en brouillon), macos-build.yml
├── docs/                             # page de présentation (index.html), captures (screenshots/, shot-*.png, result-*.jpg, gravure-test-*.jpg), bannière, architecture/ (signaux.svg / .png)
├── packaging/                        # compilation
│   ├── windows/                      # build.bat, setup.iss (Inno Setup)
│   ├── fedora/                       # laser-studio-pro.spec (paquet RPM, Copr), README.md
│   ├── debian/                       # build-deb.sh, debian/ (control, rules : paquet .deb, bibliothèques Debian), README.md
│   ├── linux/                        # build-linux.sh, build-appimage.sh, io.github.jgood3d.LaserStudioPro.desktop (entrée de menu), .metainfo.xml (fiche AppStream des logithèques)
│   ├── macos/                        # LaserStudioPro.spec, build_macos.sh, run_macos.sh, requirements-macos.txt, laser_studio_pro.icns, README.md
│   └── pyinstaller/                  # LaserStudioPro.spec (commun Windows / Linux), bundle_filter.py (filtre des fichiers inutiles)
├── src/
│   ├── laser_common/                 # partagé par Laser Studio et Stencil Studio
│   │   └── files.py                  # écriture sûre (atomique, en arrière-plan)
│   ├── laser_studio/                 # l'application
│   │   ├── main.py / __main__.py     # démarrage (python -m laser_studio)
│   │   ├── gcode/                    # génération du G-Code sans Qt : job (assemblage), params (JobParams : réglages d'un job, objet figé à champs nommés), raster (image), vector (calques), test_matrix, calibration (aller/retour), preview (modèle de l'aperçu 2D), common (power_value : seul calcul % → S, arrondi au plus proche ; LaserMoves : seul écrivain des déplacements laser, puissance portée par chaque mouvement, M3/M4 et M5 une seule fois, mots inchangés omis, car GRBL arrête la tête à chaque S ou M3/M4/M5 sans mouvement), timing (durée d'un G-Code comme GRBL la planifie : accélération par axe, jonctions $11, tampon de 15 blocs, G0, G4 ; limites lues dans $$ ou dans « Paramètres du graveur » ; marge TIME_MARGIN seulement sans limites), stats (statistiques d'un G-Code envoyé)
│   │   ├── core/                     # socle : version, paths (chemins, ressources), constants, debug_log, preferences (réglages mémorisés)
│   │   ├── models/                   # modèles de données (QObject à signaux) : vector_document (VectorDocument : objets, annuler / refaire, presse-papiers), vector_objects (objets du dessin : TextObject, ShapeObject, SvgPathObject), layers (LayersModel), layer_modes (codes des modes, sans Qt), machine (MachineConfig), grbl (GrblConfig), materials (MaterialsModel), image_settings (ImageSettings, ImageSettingsHistory), job_placement (JobPlacement : taille, décalage, origine, lignes/mm, optimisation du chemin), separation (SeparationSettings), macros (MacrosModel : macros.yaml), machine_state (état du graveur et ce qui est permis dans chaque état, sans Qt), settings (base SettingsModel), change_log (journal)
│   │   ├── i18n/                     # traductions : texts/ (textes FR / EN / DE / ES, un module par zone), translations.py (les assemble, refuse une clé en double), language.py (langue, tr), errors.py (message d'une erreur de générateur)
│   │   ├── grbl/                     # dialogue avec le graveur, sans Qt : commands (commandes GRBL, lecture de $$), streaming (envoi d'un job : tampon de 127 octets, réponses), macros (macros.yaml, détection du laser), connection, simulator, ports (ports série proposés + dernier port utilisé)
│   │   ├── image/                    # traitement d'image sans Qt : dithering (tramage), filters, size, resolution, matrix, separation, gain_test, vectorize
│   │   ├── vector/                   # géométrie vectorielle ; QtGui (QPainterPath, QTransform, QFont) accepté comme bibliothèque de géométrie, jamais QtWidgets (tests/test_pure_modules.py)
│   │   │   ├── importers.py / dxf.py                  # import SVG / DXF, conversion des résultats des générateurs en objets
│   │   │   ├── svg_extract.py                         # lecture des tracés SVG (d de <path>, arcs exacts), fusion de tracés
│   │   │   ├── layer_data.py                          # objets -> polygones par calque pour le G-Code (extract_vector_layer_data)
│   │   │   ├── path_ops.py                            # séparer un tracé, exploser, convertir en tracé (QtGui)
│   │   │   ├── boolean_ops.py                         # union, différence, intersection, exclusion des groupes ; surface peinte d'un masque SVG (QtGui)
│   │   │   ├── svg_style.py                           # styles SVG : couleurs CSS, cascade, héritage (sans Qt)
│   │   │   ├── svg_geometry.py                        # longueurs avec unité, transform CSS, tirets, détourage d'un tracé (QtGui)
│   │   │   ├── svg_tree_import.py                     # import SVG qui garde groupes, textes, couleurs -> calques, éléments cachés (QtGui)
│   │   │   ├── arrange.py                             # boîte d'un groupe, alignement, répartition, ancrage d'une forme (QtGui)
│   │   │   ├── order.py / nudge.py / font.py          # ordre de coupe, déplacement clavier, polices
│   │   │   ├── tabs.py / kerf.py / lead.py / perforate.py   # ponts de maintien, kerf, arcs d'entrée/sortie, perforation (sans Qt)
│   │   │   ├── text_on_path.py / text_on_arc.py       # texte le long d'un tracé / sur un cercle
│   │   │   ├── text_follow.py                         # texte posé sur le contour d'un objet, textes de médaille (QtGui)
│   │   │   ├── group_transform.py                     # sélection comme un groupe : encombrement, échelle, quart de tour, calque
│   │   │   ├── placement.py                           # placement d'un dessin importé : marge de surbalayage, ajouter / remplacer / à droite / au-dessus
│   │   │   ├── box_generator.py / box_3d.py / box_presets.py
│   │   │   ├── puzzle_generator.py
│   │   │   ├── ornament_generator.py / ornament_motifs.py / ornament_region.py
│   │   │   ├── keychain_generator.py
│   │   │   ├── nesting.py / nesting_apply.py
│   │   │   ├── serial_duplicate.py / serial_apply.py
│   │   │   └── jig.py
│   │   ├── camera/                   # module caméra sans Qt : capture, lens_calibration (objectif), workspace_alignment (homographie du plateau), storage
│   │   ├── controllers/              # contrôleurs : job, png2svg, matrix_image, job_queue, project, materials, layer_memory, machine_profiles, machine_connection, separation, camera, startup_safety, vector_editor, generators, layout, macros, window (WindowController), job_history (remplacent des mixins) ; workers.py : threads (QThread) du traitement d'image, de l'envoi du G-Code, du sondage d'état, de la génération
│   │   ├── resources/                # images : icône (.ico, 512 px), bannière, « Buy me a coffee »
│   │   │   ├── machines/             # catalogue des machines : un YAML par marque (README.md : format, sources)
│   │   │   └── icons/                # thèmes d’icônes FreeDesktop embarqués
│   │   │       ├── breeze/           # pack par défaut (LGPL-3) : 16x16, 22x22, 32x32
│   │   │       └── jarvis/           # pack cyan « HUD », activé avec le thème jarvis
│   │   └── ui/                       # interface PyQt6
│   │       ├── binding.py            # liaison champ ↔ modèle
│   │       ├── utils.py              # icônes dessinées, images haute résolution
│   │       ├── about/ / support/ / buy_me_a_coffee/   # boîtes du menu Aide, bouton ko-fi
│   │       ├── splashscreen/         # écran de démarrage (StartupSplash)
│   │       ├── statusbar/            # barre d'état (StatusBar : messages, progression)
│   │       ├── app/                  # coque de la fenêtre
│   │       │   ├── menu/             # AppActions, AppMenuBar, AppToolBar ; un fichier par menu (file, view, tools, help)
│   │       │   ├── main_window.py    # FullLaserStudio : assemble la fenêtre (modèles, builders des parties, objets de ui/app/)
│   │       │   ├── window_forms.py        # WindowForms : fenêtres ouvertes par WindowController (controllers/window.py)
│   │       │   ├── window_state.py   # WindowState : réglages machine, profil machine, projet, matériau choisi
│   │       │   ├── tabs.py           # MainTabs : onglets, plein écran, panneau du bas, séparateurs
│   │       │   ├── job_display.py    # JobDisplay : résultats du job, état du graveur
│   │       │   ├── image_actions.py  # ImageToolbarActions : pivoter / supprimer / miroirs de l'onglet affiché
│   │       │   ├── qt_messages.py    # filtre des avertissements Qt
│   │       │   └── theme.py          # 7 thèmes UI ; packs d'icônes Breeze et Jarvis
│   │       ├── widgets/              # ZoomableGraphicsView, HistoryLineEdit, AutoHideLabel, FloatingToolBar, FullscreenWindow, SliderWithButtons, StartHint
│   │       ├── machine/              # panneau machine (panel.py : MachinePanel)
│   │       │   ├── connection/       # ConnectionPanel (port, connecter, état GRBL, console directe) ; help_dialog : aide « Port introuvable ? »
│   │       │   ├── status/           # MachineStateView (état GRBL), AxisPositionRow (X / Y / Z)
│   │       │   ├── controls/         # JogControlPanel, RealtimeCommands
│   │       │   ├── job_actions/      # JobActionsPanel (actions de job, boutons des macros)
│   │       │   ├── macros_builder.py # build_macros : macros reliées au panneau, au graveur, aux profils
│   │       │   ├── job_position/     # JobPositionBox (à droite de l'aperçu 2D)
│   │       │   ├── console/          # DirectConsolePanel (dans Connexion)
│   │       │   └── sent_gcode/       # SentGcodeLog (à gauche du panneau machine)
│   │       ├── tabs/                 # un dossier par onglet
│   │       │   ├── layers/           # LayersTab (onglet Calques), layer_table.py (LayerManagerWidget, tableau des calques)
│   │       │   ├── image/            # ImageTab, ImageSettingsPanel, MaterialComboBox, EngraveLayerComboBox, ResolutionBox
│   │       │   ├── separation/       # SeparationTab (séparation couleur / verre)
│   │       │   ├── png2svg/          # Png2SvgTab, PngToSvgWidget, ZoomableSvgView
│   │       │   ├── preview_2d/       # Preview2DTab (dessin de l'aperçu, tête, suivi de la gravure ; modèle : gcode/preview.py), JobStatsPanel
│   │       │   ├── console/          # ConsoleTab (Console / G-Code)
│   │       │   └── job_queue/        # JobQueueTab (file d'attente)
│   │       ├── settings/             # window.py (SettingsWindow), categories.py (SettingsCategories : fenêtre « Paramètres »), appearance.py (AppearancePage : langue et thème), macros_page.py (MacrosPage) et pages : machine_params/, grbl_config/, test_matrix/ (TestMatrixPage, ImageTestGroup, TilePicker)
│   │       ├── vector_editor/        # éditeur vectoriel : tab.py (VectorEditorTab), empty_hint.py (EmptyCanvasHint : accueil du canevas vide, sur `StartHint`), canvas.py (VectorCanvasView), scene_layers.py (WorkAreaLayer, CameraLayer), document_items.py (DocumentItems), navigation.py (ViewNavigator), shortcuts.py, item.py (VectorGraphicsItem), properties_panel.py (VectorPropertiesPanel), objects_panel.py (ObjectsPanel : liste des objets), builder.py, boîtes text_dialog, medal_dialog, shape_dialog, assign_layer_dialog, resize_dialog ; forms.py (EditorForms : toutes les fenêtres de saisie vues par les contrôleurs, dont la fenêtre unique des générateurs `generators()`) ; context_menu.py (clic droit)
│   │       │   └── tools/            # outils de la souris du canevas : snapping (accroche), drawing (ligne, rectangle, cercle, ellipse), measure, node_edit (nœuds), moving (déplacement, panoramique), follow_handle (poignée du texte sur contour)
│   │       └── dialogs/              # fenêtres des outils
│   │           ├── library/          # LibraryDialog (grille, catégories, recherche), LibraryItemDialog (fiche, variantes)
│   │           ├── machine_catalog/  # MachineCatalogDialog (marques et modèles, recherche, fiche avec sources)
│   │           ├── generators/       # GeneratorsDialog : bibliothèque et générateurs dans une fenêtre (liste à gauche, fenêtre choisie à droite)
│   │           ├── box_generator/    # BoxGeneratorDialog + preview.py (BoxPreview) + preview_3d.py (Box3DView)
│   │           ├── ornament/         # OrnamentGeneratorDialog
│   │           ├── puzzle/           # PuzzleGeneratorDialog
│   │           ├── keychain/         # KeychainGeneratorDialog + KeychainPreview
│   │           ├── camera/           # dialog.py, lens_wizard.py, align_wizard.py
│   │           ├── nesting/          # NestingDialog
│   │           ├── jig/              # JigDialog (gabarit de placement)
│   │           ├── serial_duplicate/ # SerialDuplicateDialog
│   │           ├── dither_comparison/# DitherComparisonDialog
│   │           └── startup_safety/   # avertissement de sécurité laser (confirm_startup_safety)
│   └── stencil_studio/               # sous-application Stencil Studio
│       ├── LISEZMOI.md
│       ├── core/ · engrave.py / lightbox.py / subject_ai.py   # calcul, sans Qt (core/ : un module par métier)
│       ├── server.py                     # serveur local : page web et API (python -m stencil_studio)
│       ├── models/                       # session.py (photo, repères peints), presets.py (réglages enregistrés)
│       ├── controllers/                  # api.py (aperçu, visage, export), studio.py (StencilStudioController : fenêtre dans LSP)
│       ├── ui/                           # studio.html, dialog.py (StudioDialog), window.py (processus séparé), themes.py
│       ├── timing.py                     # mesure du temps d'ouverture (stencil_studio_timing.log)
│       ├── lasercut_stencil.py           # ligne de commande
│       ├── selftest.py                   # autotest : mêmes résultats OpenCV / numpy / scipy que les valeurs attendues
│       ├── i18n.py + locales/ (fr / en / de / es .json)
│       ├── resources/ (fonts/, models/u2netp.onnx) / exemple/
│       ├── requirements*.txt             # dépendances propres (+ requirements-lsp-ajouts.txt)
│       └── lancer_studio.bat / .sh
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
| **main.py** (racine) / **src/laser_studio/main.py** | La racine ajoute `src/` au chemin et appelle `laser_studio.main.main()`. Celui-ci lance l’app (ou Stencil Studio si `--stencil-studio`), puis : splash, icônes Breeze / Jarvis, thème enregistré, icône fenêtre, avertissement de sécurité, fenêtre principale. | → `ui/app/theme`, `controllers/startup_safety`, `ui/app/main_window.FullLaserStudio`, `core`, `ui.splashscreen` |
| **ui/app/theme.py** | Définition des 7 thèmes **dark / light / dusk / warm / neon / retro80 / jarvis** (palette Qt + stylesheet généré). `apply_app_theme()`, `apply_saved_theme()` (relit et normalise `QSettings("app_theme")`), `normalize_theme_name()` (alias FR/EN), `available_themes()`, `apply_icon_theme_for_ui()` (pack Jarvis pour le thème jarvis, sinon Breeze ; un thème système n'est pas écrasé), `install_breeze_icon_theme()`. Accessibilité : `contrast_ratio()` (rapport WCAG) et `focus_color()` (contour du widget qui a le focus clavier, visible dans tous les thèmes), vérifiés par `tests/test_accessibility.py`. | `main.py`, `controllers/window.change_theme`, `stencil_studio/studio_dialog` |
| **controllers/first_steps.py** · **ui/dialogs/first_steps/** | Premiers pas : `FirstStepsController` (étapes `STEPS` : catalogue des machines, connexion par `EngraverController.ensure_connected`, homing, cadrage ; `done()` d'après l'état du graveur ; `should_show_at_launch()`, préférence `first_steps/show_at_launch`) et sa fenêtre `FirstStepsDialog` (`open_first_steps(parent, steps)`, non modale, une seule à la fois). Ouverte par `main.py` au démarrage et par Aide › Premiers pas | `main.py`, `ui/app/main_window` |
| **controllers/startup_safety.py** | `StartupSafetyPolicy` : quand afficher l'avertissement laser du démarrage. Case « Ne plus afficher » : l'avertissement ne revient qu'en rappel tous les `REMINDER_EVERY` démarrages ; la variable d'environnement `NOWARNING` le désactive (tests). Prend tout objet de type `QSettings` | `main.py`, `ui/dialogs/startup_safety` |
| **grbl/ports.py** | Ports série proposés (`port_labels`, `is_usable`, `is_usb`, `port_of`) : masque les ports virtuels `/dev/ttyS*` sans matériel (description « n/a ») ; mémorise le dernier port (`load_last_port` / `save_last_port`). Sans Qt | `controllers/engraver`, `ui/machine/connection` |
| **core/preferences.py** | Préférences mémorisées, en un seul endroit : `ui_preferences()` (UIConfig : interface, thème, langue, onglets, projets récents, dernier port…), `machine_preferences()` (MachineConfig : plateau, profils, résolution), `app_preferences()` (caméra, matière de l'aperçu 2D). `Preferences` : lecture convertie (`get_bool`, `get_int`, `get_float`, `get_list` : QSettings rend parfois du texte), écriture immédiate (`set`). `in_memory()` remplace les vrais fichiers par des dictionnaires dans les tests (`job_fakes.memory_preferences`) : plus de faux QSettings | tout le code qui mémorise un réglage ; aucun `QSettings` ailleurs |
| **core/version.py** | Version (`APP_VERSION`), lue aussi par le build macOS ; identifiant de l'application (`APP_ID`) : nom du fichier .desktop et de l'icône sous Linux, identifiant de la fenêtre sous Wayland (`setDesktopFileName` dans `main.py`) | `ui/about`, `ui/app/menu` |
| **core/paths.py** | Dossier de l'exécutable et du bundle, dossier des données (autosave), ressources (`find_resource`) | Utilisé largement |
| **laser_common/files.py** | Écriture atomique (`atomic_write_json`), écrivain en arrière-plan (`get_background_writer`) | `controllers/project`, `controllers/job_queue`, `main_window` |
| **core/constants.py** | Valeurs fixes (lien ko-fi, splash, JOG, barre d'état) | `ui/` |
| **models/settings.py**, **machine.py**, **grbl.py** | `SettingsModel` : réglages nommés (`FIELDS` : type et défaut), lus comme des attributs, modifiés par `update()` qui convertit, n'émet `changed({nom: valeur})` que pour ce qui change et écrit l'ancienne et la nouvelle valeur dans le journal. `MachineConfig` (`machine`) : plateau, spot, vitesse et accélération max (`to_profile` / `apply_profile` pour les profils machine, `to_project` / `load_project` pour les projets, `to_preferences` / `load_preferences` pour les préférences du démarrage). `GrblConfig` (`grbl`) : commande laser (`M4` / `M3`), S-Max, homing, surbalayage, décalage aller/retour, ordre de découpe sûr, G-Code de début et de fin, réglages `$$` ; `to_profile` / `apply_profile` / `mechanical_values` pour les profils machine. Les pages Paramètres du graveur et Configuration GRBL ne sont plus que des vues liées à ces modèles | Créés par `main_window` ; lus par la génération, l'éditeur vectoriel, le traitement d'image, Stencil Studio (`lsp_bridge`) |
| **models/layer_modes.py** | Codes des modes de calque (`engrave_fill`, `cut`, `mark`, `perforate`), indépendants de la langue, enregistrés dans les projets, les profils et les commentaires du G-Code ; seul leur affichage est traduit (`LAYER_MODE_TR_KEYS`, `models.layers.layer_label`). `normalize_mode()` convertit les anciens libellés français (« Gravure Remplie », « Découpe », « Marquage (Contour) ») à la lecture. Aussi `layer_laser_cmd` / `layer_overscan_enabled` (commande laser et surbalayage effectifs d'un calque, objet ou dictionnaire). Sans Qt | `models/layers`, `vector/order`, `gcode/`, Stencil Studio |
| **models/image_settings.py** | `ImageSettings` (`SettingsModel`) : réglages de tramage de « Graver une image » (luminosité, contraste, gamma, netteté, négatif, matière, miroirs, algorithme, image déjà tramée `as_is`), liés aux champs de l'onglet (`ImageSettingsPanel.bind_settings`) et aux miroirs de la barre d'outils ; `choose_material()` coche ou décoche le négatif, `to_project()` / `load_project()` pour les projets, `processing_params()` pour le traitement. `ImageSettingsHistory` : annuler / refaire, changements rapprochés regroupés en une étape | `main_window`, `controllers/image`, `controllers/separation`, génération |
| **models/job_placement.py** | `JobPlacement` (`SettingsModel`) : placement du job — taille de l'image (`width_mm`, `height_mm`), origine (`origin`, par code ; `normalize_origin` relit les anciens libellés traduits), décalage (`offset_x`, `offset_y`), résolution (`lines_mm`) et `optimize_path`. Champs liés : taille dans « Graver une image » (`build_image_tab`), origine et décalage dans `JobPositionBox` (onglet Visualisation 2D), « Optimiser le chemin » dans le cadre « Génération » de l'aperçu ; les lignes/mm viennent de `ResolutionBox` (signal `resolution_changed`) et y retournent à l'ouverture d'un projet. `geometry()` pour `JobParams`, `to_project()` / `load_project()`, `to_profile()` / `apply_profile()` (origine) | `main_window` (`placement`), `controllers/job`, `controllers/image` (par ses fonctions), `ui/app/window_state` (projets, profils) |
| **image/resolution.py** | Lignes/mm, DPI, focale, et classement de l'écart entre les lignes par rapport au spot (`resolution_quality`). Sans Qt | `ui/tabs/image/resolution_box` |
| **image/dithering.py** | Traitement de l'image à graver sans Qt : `process_image` (taille de gravure, miroirs, luminosité, contraste, gamma, netteté, négatif, tramage), algorithmes (`ALGORITHMS`, diffusion d'erreur avec numba si présent, Bayer, seuil, niveaux de gris), vignettes de comparaison (`comparison_thumbnails`), aperçu des tons de l'originale (`tone_preview`), image déjà tramée gravée telle quelle (`as_is`, `is_binary`) | `controllers/image`, `workers.ImageProcessingWorker` |
| **image/gain_test.py** | Grille de calibrage du gain de point du verre peint (`build_gain_test_array`), sans Qt | `controllers/job` (`generate_gain_test`) |
| **models/change_log.py** | Journal des changements des modèles : une ligne par changement, sauf pour les textes saisis au clavier (G-Code de début et de fin, `$$`, nom d'un calque), écrits une seule fois à la fin de la saisie | `models/` |
| **models/materials.py** | `MaterialsModel` : les matériaux (nom -> réglages des calques) et le matériau choisi ; `store()` n'émet que si quelque chose change. Le matériau choisi suit chaque changement de calque (plus de bouton « Enregistrer »), sauf pendant le chargement d'un profil machine, d'un projet ou d'un matériau (`main_window._material_autosave_paused`) | `controllers/materials` (liste déroulante tenue à jour par ses signaux) |
| **ui/binding.py** | `bind(champ, modèle, réglage)` : lie un champ (spinbox, case, liste, texte) à un réglage d'un modèle, dans les deux sens, sans boucle | Pages Paramètres du graveur et Configuration GRBL |
| **core/debug_log.py** | Logging debug / résumés G-Code | `controllers/engraver`, `controllers/job_queue`, `grbl`, `controllers/workers`, `models/` |
| **models/layers.py** | `LayersModel` (`QObject`) : la liste des calques (`LaserLayer`), seule source de leurs réglages. Toute modification passe par `update()`, `add_layer()`, `remove_layer()`, `move_layer()` ou `load_list()`, qui émettent `layer_changed`, `layer_added`, `layer_removed`, `layers_reordered` ou `layers_reset`, puis `changed`, et écrivent l'ancienne et la nouvelle valeur dans le journal de débogage (`laser_studio.gravure.modeles`). `engrave_layer()` : calque de la gravure des images (celui choisi dans l'onglet image, `select_engrave_layer()` → signal `engrave_layer_selected`, sinon le premier calque de gravure), dont la vitesse et la puissance sont lues à chaque usage (`engrave_speed` / `engrave_power`). Chaque calque a aussi `overscan` (surbalayage, vrai par défaut) et `laser_cmd` (`""` = commande de Configuration GRBL, `M4` dynamique ou `M3` constante, voir `LAYER_LASER_CMDS`) ; `layer_overscan_enabled()` et `layer_laser_cmd()` donnent la valeur effective d'un calque (objet ou `to_dict`) en la combinant avec le réglage global, qui reste maître pour le surbalayage (mode et distance). Chaque calque de découpe a aussi `tabs` (ponts de maintien activés, faux par défaut), `tab_count` (ponts par contour extérieur fermé, 4 par défaut, au plus `TAB_COUNT_MAX`) et `tab_width` (largeur d'un pont en mm, entre `TAB_WIDTH_MIN_MM` et `TAB_WIDTH_MAX_MM`), puis `kerf` (compensation du kerf activée, faux par défaut) et `kerf_width` (saignée en mm, 0,15 par défaut, entre `KERF_WIDTH_MIN_MM` et `KERF_WIDTH_MAX_MM`), puis `lead` (arcs d'entrée et de sortie activés, faux par défaut) et `lead_radius` (rayon en mm, 1,0 par défaut, entre `LEAD_RADIUS_MIN_MM` et `LEAD_RADIUS_MAX_MM`), puis `perf_dash` / `perf_gap` (perforation) et `ramp` (rampe de puissance activée, faux par défaut) / `ramp_power` (puissance de la dernière passe en %, 100 par défaut, entre `RAMP_POWER_MIN_PCT` et `RAMP_POWER_MAX_PCT`), validés par `validated_settings` et mémorisés par profil machine (`layer_memory`). Un ancien projet sans ces champs garde les valeurs par défaut (aucune de ces options) | `main_window`, `LayerManagerWidget`, `controllers/materials`, `controllers/layer_memory`, génération |
| **ui/app/qt_messages.py** | Filtre warnings Qt (Wayland…) | `main.py` |
| **i18n/** | Traductions FR / EN / DE / ES : `texts/` (un dictionnaire `TEXTS` par zone : app, vector, box, ornament, generators, camera, image, machine, materials), `translations.py` (assemble `TRANSLATIONS`, ImportError si une clé est définie deux fois), `language.py` (langue mémorisée, `tr()`), `errors.py` (`generator_error_text` : clé `<générateur>.err.<code>` remplie avec les infos de l'erreur), `durations.py` (`duration_text` : « 46 s », « 3 min 12 s », « 2 h 05 min », seule mise en forme d'une durée). `from i18n import tr` | Toute l’UI |
| **grbl/connection.py** | `LaserUSBController` : connexion série au graveur (ou au graveur simulé), envoi des commandes, lecture du rapport d'état | `controllers/machine_connection`, `controllers/workers` |
| **grbl/streaming.py** | Envoi d'un job, partie sans Qt ni port : `resume_gcode` (reprise d'un job arrêté : état du G-Code au point de reprise ; départ au trait qui passe par la position d'arrêt de la tête, relue par `EngraverController` une fois la machine arrêtée, sinon PLANNER_BLOCKS lignes avant la dernière acquittée), `gcode_lines` (lignes de la console que GRBL sait lire ; `is_sent_line`, la même règle pour une ligne, sert aussi à l’aperçu 2D pour numéroter ses traits), `classify` (ok, erreur, statut, autre), `CharacterCountingStream` (prochaine ligne si elle tient dans le tampon de 127 octets, lignes en attente de leur « ok » ; `wire_bytes` : la ligne part sans espaces ni commentaire, la console garde la ligne lisible). `GCodeStreamerThread` (controllers/workers.py) ne fait plus que les lectures et écritures au bon rythme, l'attente de Idle et l'arrêt sur erreur | `controllers/workers` |
| **grbl/macros.py** | Macros de l'utilisateur sans Qt : `Macro` (nom, G-Code, infobulle, confirmation, profils machine ; `fires_laser`, `shown_for`), `load_macros` / `dump_macros` (YAML, G-Code en bloc littéral), `MacroError` (code traduit `macros.err.<code>`), `fires_laser` (M3 / M4 actif avec S > 0, puissance modale) | `models/macros`, `controllers/macros`, `ui/dialogs/macros` |
| **models/machine_state.py** | État du graveur vu par l'application, sans Qt : `machine_state(connecté, activité, état GRBL, reconnexion)` donne `DISCONNECTED`, `RECONNECTING`, `READY`, `ALARM`, `COMMANDS`, `HOMING` ou `STREAMING` (jamais enregistré à part : déduit de ce qui est vrai à l'instant) ; `ALLOWED` / `allowed(état, action)` : seule table de ce qui est permis (`JOG`, `CONSOLE`, `HOME`, `UNLOCK`, `MACRO`, `SEND_JOB`, `SETTINGS`, `REALTIME`, `CONNECT`, `DISCONNECT`). Pendant un job ou un homing, seules les commandes temps réel ; en alarme, déverrouillage, homing, console et `$$` | `controllers/machine_connection` (`state`, `can`, `state_changed`), `controllers/engraver` (`allowed`), `controllers/macros`, `controllers/job_queue` (`may_send`), panneaux de `ui/machine/` (`set_allowed`, `MachinePanel.set_machine_state`) |
| **models/macros.py** | `MacrosModel` : liste des macros lue dans `macros.yaml` (dossier des données), `changed`, `set_macros` (enregistre, écriture atomique), `visible_for(profil)` ; un fichier illisible n'est pas écrasé (`load_error`) | `controllers/macros`, `ui/machine/macros_builder` |
| **controllers/macros.py** | `MacroController` : `run(rang)` (graveur connecté, jamais pendant un job ; laser → `confirm_default_no` toujours, sinon `confirm` si la case est cochée ; envoi par `EngraverController.send_direct`), `manage()` (éditeur, puis enregistrement), import / export. Construit par `ui/machine/macros_builder.build_macros`, qui relie aussi `JobActionsPanel.set_macros` / `macro_requested` / `manage_macros_requested`, les profils machine (`MachineProfilesController.add_listener`) et le menu **Outils › Macros…** | `main_window`, `controllers/window` |
| **gcode/stats.py** · **models/job_history.py** · **controllers/job_history.py** | Historique des gravures. `gcode_statistics` (sans Qt) : lignes, G0 / G1, distance gravée et à vide, F et S maximales, encombrement. `JobHistory` : une ligne JSON par job dans `historique-gravures.jsonl` (dossier des données), ajout seulement, export CSV, effacement. `JobHistoryRecorder` : branché sur `EngraverController.stream_starting` / `stream_ended` (envoi direct et file d'attente) et `JobController.generated` (durée estimée retrouvée par l'empreinte du G-Code) ; note l'issue (terminée, arrêtée, erreur GRBL, interrompue), la durée réelle et les réglages de la machine ; statistiques calculées dans un thread. Fenêtre `ui/dialogs/job_history/` (Outils › Historique des gravures…) | `main_window`, `controllers/window` |
| **grbl/simulator.py** | `SimulatedGrblSerial` : graveur GRBL 1.1 simulé (`LASER_STUDIO_SIMULATION`), imite la partie de pyserial utilisée | `grbl.connection`, `controllers/engraver` (port « SIMULATION ») |
| **camera/capture.py** | Détection des périphériques vidéo, capture d'images et gestion du flux vidéo brut via OpenCV, sans Qt. | `controllers/camera`, `ui/dialogs/camera/` |
| **camera/lens_calibration.py** | Calibration optique de l'objectif (mire d'étalonnage, matrice intrinsèque, coefficients de distorsion) et redressement des images (`undistort`), sans Qt. | `controllers/camera`, `ui/dialogs/camera/lens_wizard.py` |
| **camera/workspace_alignment.py** | Détection des AprilTags (normaux ou en négatif, plusieurs passes), fusion de plusieurs captures, homographie entre les pixels redressés de la caméra et les coordonnées millimétrées du plateau à partir des 4 coins de chaque tag ; redressement perspectif de l'espace de travail complet (`warp_to_bed`), sans Qt. | `controllers/camera`, `ui/dialogs/camera/align_wizard.py` |
| **camera/storage.py** | Persistance et chargement des profils de calibration optique et d'alignement plateau liés à la machine (`QSettings` / fichiers JSON), sans Qt. | `controllers/camera`, `camera/` |

### 3.2 Fenêtre principale et ses objets

| Fichier | Rôle | Dépend de / appelle |
|-----------------|------|---------------------|
| **ui/app/main_window.py** | `FullLaserStudio` (`QMainWindow`, sans mixin) : point d'assemblage. Crée les modèles et les contrôleurs partagés (job, graveur, projet), appelle le builder de chaque partie de l'interface, place les onglets et le panneau machine, crée les objets de `ui/app/` et relie les parties entre elles ; fermeture, drag&drop, messages (`show_status_message`, `log_message`). Plus aucun alias de champ (`spin_w`, `chk_homing`…) : on lit la page ou le modèle | `controllers/`, `models/`, `ui/app/`, builders de `ui/` |
| **ui/…/builder.py** | Un builder par partie de l'interface : `build_image_tab`, `build_separation_tab`, `build_png2svg_tab`, `build_layers_tab`, `build_job_queue_tab` (`ui/tabs/…`), `build_vector_editor` (`ui/vector_editor/`), `build_machine_panel` (`ui/machine/`), `build_machine_params_page`, `build_grbl_config_page`, `build_test_matrix_page` (`ui/settings/…`). Chacun crée la vue et sa logique et les relie ; il reçoit ses dépendances en paramètres (modèles, contrôleurs, rappels), jamais la fenêtre | `controllers/`, `models/` |
| **ui/app/menu/** | `AppActions` crée toutes les actions (icône, libellé, raccourci, état) et émet les signaux (`save_project_requested`, `mirror_changed`, `camera_requested`, `generator_requested(page)`…) ; les outils de l'éditeur vectoriel (`vector_tool_actions` : import, boîte, puzzle, boules de Noël, porte-clés — la fenêtre des générateurs sur leur page) ouvrent d'abord son onglet. `AppMenuBar` et un fichier par `QMenu` (Fichier — avec l'historique et « Paramètres… » —, Outils, Aide ; Ctrl+J est une action de la fenêtre), `AppToolBar` (mêmes actions + « Générer » et, à droite, le bouton ko-fi) ne font que les ranger | `ui/buy_me_a_coffee` |
| **controllers/window.py** · **ui/app/window_forms.py** | `WindowController` (`QObject`) : ce qui agit sur la fenêtre entière, sans construire de fenêtre : `WindowForms` ouvre pour lui à propos, support, café, aide, historique, caméra, fenêtres de réglages et comparaison des tramages, et applique le thème Qt. Créé par la fenêtre une fois toutes ses parties construites, il reçoit explicitement ce dont il se sert (formulaires, dialogues, actions, onglets, machine, job, image, historique, éditeur vectoriel, pages, registres des fenêtres de réglages et des onglets du menu Outils) : il ne lit plus rien dans la fenêtre, qui ne lui sert que de parent Qt. Le menu et la barre d'outils (`AppActions`) sont branchés par la fenêtre (`FullLaserStudio._connect_app_actions`). `change_theme`, `select_language`, aide, ouverture Stencil Studio (et son préchauffage), fenêtre Caméra, fenêtres de réglages (`show_settings_window`), onglet demandé par le menu (`show_main_tab`), matrice de test générée puis affichée ; « Graver une image » : résolution reportée dans la matrice et la Séparation (`resolution_changed`), focale des Paramètres Machine (`machine_focal_changed`), comparaison des tramages ; Stencil Studio (`stencil()`) ; fond caméra de l'éditeur vectoriel | `ui/app/theme`, `ui/app/menu`, `ui/app/window_forms`, `stencil_studio.controllers.studio`, `controllers/camera` |
| **ui/app/window_state.py** | `WindowState` (`QObject`) : ce que la fenêtre enregistre et restaure — réglages machine au démarrage et à la fermeture (`save_machine_settings`, `load_machine_settings`), champs d'un profil machine (`capture_machine_profile`, `apply_machine_profile`, `machine_memory`, `apply_profile_layers`, `after_machine_profile_selected`), état d'un projet (`capture_project`, `restore_project` : chaque modèle de `_project_models()` — placement, machine, image, GRBL, job — donne et relit sa partie par `to_project` / `load_project`), réglages en cours au format d'un matériau (`job_settings`, `apply_job_settings`) et recopie automatique des calques dans le matériau choisi (`store_layers_in_material`, suspendue par `material_autosave_paused`). Ses méthodes sont passées en fonctions aux contrôleurs qui décident quand enregistrer | `controllers/machine_profiles`, `controllers/project`, `controllers/materials`, `controllers/layer_memory` |
| **ui/app/tabs.py** | `MainTabs` (`QObject`) : onglets du centre. `show(onglet)` (rendu visible, ou fenêtre plein écran ramenée devant), plein écran de l'onglet affiché (`toggle_current_fullscreen` : fenêtre commune `FullscreenWindow`, fenêtre à part pour l'éditeur vectoriel), séparateurs mémorisés (`save_splitter_sizes` / `load_splitter_sizes`, tailles dépliées du panneau du bas) | `ui/widgets` (`FullscreenWindow`) |
| **ui/app/bottom_panel.py** | `BottomPanel` : panneau du bas façon VS Code, sous les onglets dans `center_v_splitter` : onglets Graveur (panneau machine), Console G-Code (`ConsoleTab`), File d'attente ; replié = sa barre d'onglets seule (`set_collapsed`, `toggle`, `show_page`, signal `collapsed_changed`, état dans `UIConfig`). Déplié par Ctrl+J (`AppActions.bottom_panel`), le clic sur la pastille de la barre d'état (`StatusBar.machine_clicked`) et `JobDisplay` (gravure lancée, alarme qui survient) | `ui/app/main_window` |
| **ui/app/job_display.py** | `JobDisplay` (`QObject`) : montre ce qu'annoncent `JobController` (progression, erreur, G-Code généré ou importé : console, statistiques, `plot` vers l'aperçu 2D, « Enregistrer le G-Code ») et le graveur (`connect_machine` : connexion, état et position, suivi de l'envoi, traits gravés, bip de fin). `set_homing_available` : cases « Inclure $H » grisées sans homing (pour `EngraverController`) | `ui/tabs/preview_2d`, `ui/machine`, `ui/statusbar`, `gcode` |
| **ui/app/image_actions.py** | `ImageToolbarActions` (`QObject`) : « Pivoter », « Supprimer » et miroirs de la barre d'outils et des barres flottantes, sur l'image de l'onglet affiché. Chaque onglet d'image s'inscrit (`add` : image chargée ?, pivoter, retirer, confirmation, miroirs utiles) ; `update_state` grise les actions sans image | `ui/user_dialogs` |
| **ui/widgets/floating_toolbar.py** | `FloatingToolBar` : petite barre d'outils posée par-dessus un aperçu, un canevas ou une table (séparation, PNG→SVG, aperçu 2D, onglet Calques, éditeur vectoriel) | `main_window`, `ui/tabs/*` |
| **gcode/framing.py** | Parcours du cadrage, sans Qt, d'après les traits gravés du G-Code (`burn_segments`) : `burn_extent`, `box_path` (rectangle : X max, Y max, retour à X0 puis Y0), `contour_paths` (tour au plus près de chaque pièce : grille de 0,5 mm remplie, écarts de moins de 2 mm refermés, bord extérieur suivi et simplifié par OpenCV, chargé au premier usage). Commandes : `grbl.commands.frame_commands` (G0 au départ, M3 à `GrblConfig.frame_power_pct` % du S-Max, 0,5 par défaut, réglage de la machine dans Configuration GRBL ; G1, M5) | `controllers/engraver.frame(contour)` |
| **ui/app/menu/job_menu.py** | `JobMenu` : menu Job (F5 générer, F6 / Maj+F6 cadrer, Ctrl+Entrée envoyer, F7 pause, F8 reprise, F9 arrêt d'urgence ; bouton rouge de la barre d'outils pendant un travail, `AppActions.set_machine_state`), actions `AppActions.job_actions` branchées par `main_window` | `ui/app/menu/menu_bar.py` |
| **ui/wheel_guard.py** | `install_wheel_guard(app)` : filtre de toute l'application (un seul, à l'application, retiré par `atexit` avant la fin de Python, sinon Qt l'appellerait pendant que Python se termine) ; la molette sur un champ numérique, une liste ou un curseur sans focus fait défiler la zone qui le contient (les barres de défilement ne sont jamais filtrées) | `main_window` |
| **ui/widgets/start_hint.py** | `StartHint` : carte d'accueil posée au centre d'une zone vide (titre, rangées de gros boutons, signal `command(nom)`), visible tant que `is_empty()` est vrai ; `refresh()` après un changement de contenu | `ui/vector_editor/empty_hint` (canevas vide), `ui/tabs/image/tab` (aucune image) |
| **ui/tabs/image/** | `ImageTab` : onglet « Graver une image », réglages à gauche (`ImageSettingsPanel` : taille + offset, réglages photo, matière, tramage, résolution, **calque de gravure** — `EngraveLayerComboBox`, calques en mode gravure seulement, signal `engrave_layer_changed(id)` sur choix de l'utilisateur ; transmis à `LayersModel.select_engrave_layer`, liste remise à jour à chaque changement des calques par `build_image_tab`), aperçus originale / tramé côte à côte (`show_source`, `show_processed`). `ImageSettingsPanel.bind_settings` lie les champs du tramage à `ImageSettings` ; `ResolutionBox` garde lignes/mm, DPI et focale d'accord entre eux (`set_focal`, `apply_focal`, `refresh`) et émet `resolution_changed(lignes/mm)`. Émet `compare_requested`, `fullscreen_requested` ; le panneau émet `processing_changed`, `size_changed`, `material_changed`, `resolution_mode_changed`… | Construit et relié par `ui/tabs/image/builder.py` (`build_image_tab`) ; `ImageSettingsPanel.size_mm` / `offset_mm`, `ResolutionBox.lines_per_mm` / `saved_state` / `restore_state` remplacent les anciens noms des champs |
| **ui/machine/job_position/** | `JobPositionBox` : cadre « Position du job » (origine du repère et décalage X / Y, liés au modèle `JobPlacement` par `bind_placement` ; l'origine par code, quelle que soit la langue) | Construit dans `main_window._build_image_tab`, placé en haut de la colonne de droite de `Preview2DTab` |
| **ui/machine/sent_gcode/** | `SentGcodeLog` : suivi du G-Code envoyé (`clear_lines`, `append_lines`, `mark_end`) | Placé à gauche par `MachinePanel` ; alimenté par `JobQueueController` (`sent_log`) et l'envoi direct (`EngraverController`, affichage par `JobDisplay`) |
| **ui/machine/** | `MachinePanel` : assemble sous les onglets la rangée G-Code envoyé / connexion / pilotage / actions de job, et la barre de progression du job. Pas de signaux à lui : la fenêtre s'abonne à ceux de ses sous-panneaux ; `set_connected()` verrouille les commandes, `set_status()` répartit l'état GRBL (Connexion) et la position (sous le pilotage) | Construit et abonné dans `main_window._build_machine_panel` |
| **ui/machine/controls/** | `JogControlPanel` : jog, homing, pas, vitesse, commandes temps réel, envoi du job. Émet des signaux (`jog_requested`…), sans logique machine | Abonné : `EngraverController` (via `main_window._build_machine_panel`) |
| **ui/machine/job_actions/** | `JobActionsPanel` : cadrage, zéro, aller au zéro, répétition. Émet des signaux, construit depuis une liste d'actions (futures macros) | Abonné : `EngraverController` (via `main_window._build_machine_panel`) |
| **ui/machine/status/** | `MachineStateView` : état GRBL coloré, « Déverrouiller » visible seulement en alarme (émet `unlock_requested`), dans `ConnectionPanel`. `AxisPositionRow` : X / Y / Z à parts égales, en bas de `JogControlPanel` | Alimentés par `JobDisplay.show_machine_state` → `MachinePanel.set_status` |
| **ui/machine/console/** | `DirectConsolePanel` (sans cadre, dans `ConnectionPanel`) : champ de commande GRBL avec historique (flèches) et bouton « Envoyer ». Émet `command_submitted(commande)` | Abonné : `EngraverController.send_console_command` |
| **ui/settings/machine_params/** | `MachineParamsPage` (QScrollArea) : profils machine, dimensions du lit, spot, limites. Émet `profile_selected`, `new/update/delete_profile_requested`, `bed_size_changed(l, p)`, `focal_changed(mm)`, `max_speed_changed` | Construite et reliée par `build_machine_params_page` ; `bind_settings(machine)` lie ses champs au modèle `MachineConfig`, que lit la logique (`machine.bed_w`…) |
| **ui/settings/test_matrix/** | `TestMatrixPage` : réglages de la matrice (puissances, passes, vitesses, cases), affichage selon le mode gravure / découpe, test à partir d'une image (aperçu `TilePicker`). Émet `generate_requested`, `choose_image_requested`, `use_loaded_image_requested`, `image_test_toggled` ; fournit `matrix_params()`, `tile_settings()` ; reçoit `set_lines_mm()`, `set_source_image()` | Construite et reliée par `build_test_matrix_page` ; lue par `JobController.generate_test_matrix` (via `WindowController.generate_test_matrix_and_show`) |
| **ui/settings/grbl_config/** | `GrblConfigPage` : commande laser, S-Max, homing, surbalayage (la page affiche la distance ou le pourcentage selon le mode), ordre de découpe sûr, décalage aller/retour, G-Code de début et de fin, réglages GRBL complets ($$). Émet `bidir_test_requested`, `scan_offset_changed`, `read_settings_requested`, `send_settings_requested`, `export_settings_requested`, `import_settings_requested`, `link_settings_to_profile_requested` | Construite et reliée par `build_grbl_config_page` ; `bind_settings(grbl)` lie ses champs au modèle `GrblConfig`, que lisent la génération, les profils, les projets et la connexion |
| **controllers/** | Contrôleurs : objets Python ordinaires, construits par la fenêtre avec ce dont ils ont besoin, sur lesquels elle branche les signaux de l'interface. `JobController` (`controllers/job.py` : paramètres du job, contrôles avant génération, génération dans un thread, G-Code périmé (`mark_stale` dès qu'un calque, la configuration GRBL, le placement, l'image ou le dessin change ; `is_stale(texte)`, signal `gcode_stale_changed`, mention cliquable de la barre d'état, confirmation dans `EngraverController.confirm_safe_gcode`), estimation rapide, export / import du G-Code, motif aller/retour, test du gain de point (verre peint, onglet Séparation), matrice de test et clic sur une case, réglages de gravure (et ceux de l'ancienne découpe SVG, supprimée, encore lus et écrits dans les projets et les matériaux) ; questions par `UserDialogs`, résultats par signaux `started`, `progress`, `generated`, `failed`, `imported`, `log`, `status`), `Png2SvgController` (SVG de l'onglet PNG→SVG → objets de l'éditeur vectoriel), `MatrixImageController` (matrice à partir d'une image : fichier ou image de « Graver une image », zone gravée de chaque case), `JobQueueController` (liste des jobs, sauvegarde, enchaînement des envois par l'interface `Engraver`), `ProjectController` (fichier du projet : format JSON et image en base64, boîtes Enregistrer / Ouvrir, projets récents, sauvegarde automatique et récupération ; l'état est fourni et réappliqué par `WindowState.capture_project` / `restore_project` (`ui/app/window_state.py`), qui assemble la partie de chaque modèle — `to_project()` / `load_project()` de `MachineConfig` (plateau), `ImageSettings` (tramage), `GrblConfig` (ordre de découpe sûr) et `JobController` (gravure des anciens projets, ancienne découpe) — avec les champs de la fenêtre (taille, position, résolution), les calques, les matériaux et les objets vectoriels), `layer_memory.py` (fonctions, pas une classe : `apply_saved_layers`, `settings_from` ; réglages des calques mémorisés par profil machine et réappliqués à `LayersModel`), `CameraController` (`controllers/camera.py` : orchestre la capture vidéo, applique les calibrations, projette l'image du plateau sur le canevas vectoriel et gère les assistants) | Construits dans `main_window` (`_build_png2svg_tab`, `_build_test_matrix_page`, `_build_job_queue_tab`, etc.) ; testés seuls (`tests/test_controllers.py`) |
| **ui/dialogs/camera/** | Interface et assistants de la caméra : `dialog.py` (`CameraDialog` : sélection caméra, aperçu en direct, capture de fond de plateau, lancement des assistants), `lens_wizard.py` (`LensCalibrationWizard` : étalonnage de la distorsion de lentille), `align_wizard.py` (`WorkspaceAlignmentWizard` : mire 4 points / gravure de repères pour calibrer le repère machine) | Pilotés par `controllers/camera.py` ; ouverts depuis le menu Outils / barre d'outils |
| **ui/tabs/layers/** | `LayersTab` : page de l'onglet « Calques ». Barre des profils matériaux (`material_combo`, `material_selected` sur un choix de l'utilisateur seulement, actions enregistrer / nouveau / supprimer / exporter / importer). Enveloppe `LayerManagerWidget` (`ui/tabs/layers/layer_table.py`, vue abonnée à `LayersModel`), relaie `layers_changed` (= `LayersModel.changed`), `refresh()`, `link_all_to_focal()`… | Construit et abonné dans `main_window._build_layers_tab` ; lu par Stencil Studio (`lsp_bridge`) |
| **ui/tabs/preview_2d/** | `Preview2DTab` : onglet « Visualisation 2D G-Code ». Options d'affichage (inverser, négatif, déplacements rapides), cadre « Génération » (optimiser le chemin, lié à `JobPlacement`), graphique pyqtgraph (`plot_widget`) avec le plateau de la machine en pointillés (`set_bed`, vue cadrée dessus tant qu'aucun G-Code n'est affiché). `show_gcode(gcode, couleurs des calques, matrice en gravure)` dessine l'aperçu à partir du modèle `gcode/preview.py` (`parse_preview_cached` : la dernière lecture est gardée, une option d'affichage changée redessine sans relire le G-Code, et `AdvancedGCodeWorker` le lit d'avance dans son thread) : traits ou image reconstituée par groupe, fond de matière (à l'intérieur des découpes), légende ; `set_head_position` / `clear_head_position` : point de la tête ; `set_lines_acked`, `update_burn`, `reset_burn`, `finish_burn` : traits déjà gravés en rouge pendant un job (`BurnTracker`). À droite, séparateur réglable (position mémorisée) : colonne étroite avec `JobPositionBox`, le cadre « Génération » puis `JobStatsPanel` (`set_stats`). Émet `display_options_changed`, `plot_clicked(x_mm, y_mm)`, `log(texte)`, `fullscreen_requested` | Construit et abonné dans `main_window._build_2d_preview_tab` ; `JobDisplay.plot` lui passe le G-Code ; l'affichage du graveur (`JobDisplay.status_updated`, `_stream_starting`) pilote la tête et le suivi |
| **ui/tabs/console/** | `ConsoleTab` : onglet « Console / G-Code », masqué au démarrage (menu Affichage). Console `console_edit` ; les statistiques (`JobStatsPanel` : lignes, puissance moyenne, temps estimé, fichier `job_stats_panel.py` de `ui/tabs/preview_2d/`) sont à droite de l'aperçu 2D, l'export dans « Fichier > Enregistrer le G-Code » | Construit dans `main_window._build_console_tab`, qui garde le nom `txt_console` utilisé partout |
| **ui/tabs/job_queue/** | `JobQueueTab` : onglet « File d'attente ». Liste réordonnable, boutons (le G-Code envoyé est suivi dans le panneau machine). Émet `add_current_requested`, `remove_selected_requested`, `clear_requested`, `run_requested`, `reordered` | Construit dans `main_window._build_job_queue_tab`, piloté par `JobQueueController` ; le suivi du G-Code envoyé (`SentGcodeLog`, panneau machine) sert aussi à l'envoi direct (`EngraverController.start_stream`) |
| **controllers/image.py** | `ImageController` (`QObject`, boîtes de dialogue par `UserDialogs`) : image de « Graver une image » — ouverture (taille d'origine d'après la résolution du fichier, réduite au plateau), rotation, retrait, image reçue de la Séparation ou d'un projet, proportions conservées, traitement retardé de 150 ms puis lancé dans un thread (`processed_array`, relance si les réglages changent pendant le calcul), comparaison des algorithmes, algorithme mémorisé, réinitialisation, rappel de la matière. Signaux : `source_changed`, `processed`, `status`, `loading_file`, `resetting` | `image/dithering`, `image/size`, `workers` |
| **controllers/vector_editor.py** · **vector_import.py** · **grouping_actions.py** · **text_follow_actions.py** · **object_list_actions.py** | `VectorEditorController` (`QObject`) : cœur de l'éditeur vectoriel sur le `VectorDocument` et le canevas — insertion et modification de textes et de formes, opérations sur la sélection (pivoter, dupliquer, supprimer, copier / coller, déplacer aux flèches, calque, taille `resize_group`, forme du clic droit, tout supprimer, calque / position / taille du panneau des propriétés, alignement et répartition), placement de tout dessin importé (`import_objects`, `vector/placement.py` : marge de surbalayage `overscan_margin(largeur)` fournie par `JobController.overscan_margin`, et choix ajouter / remplacer / à droite / au-dessus si l'éditeur n'est pas vide, en une étape d'annulation). `changing(objets)` : gestionnaire de contexte d'une modification — étape d'annulation avant, `notify_changed` et panneau des propriétés après. Il compose des actions spécialisées qui le reçoivent comme contexte : `importer` (`VectorImporter` : `open_dialog`, `import_file` aussi pour le glisser-déposer, `import_stencil_export`), `grouping` (`GroupingActions` : `group_selection`, `group`, `set_operation`, `ungroup_selection`, `explode_selection`), `text_follow` (`TextFollowActions` : `follow_selection`, `follow`, `resync`, `resync_linked` quand un contour bouge, `medal`), `object_list` (`ObjectListActions` : `move`, `rename`, `set_visible`, `toggle_ignored`, `delete` ; arbre des groupes par `vector/object_tree.py`). Le clavier et le clic droit du canevas les demandent par signaux, branchés par `ui/vector_editor/builder.py` sur la même table de commandes que les boutons (`commands()`). Les règles de la sélection (paire texte / contour, contour lié, contour de médaille) sont dans `vector/text_follow.py`. Aucune fenêtre construite : texte, forme, calque d'un tracé, médaille et taille de la sélection passent par `EditorForms` (`ui/vector_editor/forms.py`, rappel `before_apply` pour prendre l'annulation avant d'appliquer), les messages par `UserDialogs`. Signaux `show_editor`, `properties_changed(obj)`, `status(str)` | `main_window`, `ui/vector_editor/builder`, `controllers/window` (exports de Stencil Studio) |
| **vector/object_tree.py** | Arbre des objets du dessin, sans Qt : `ancestors` (groupes qui contiennent un objet, du dessus de la pile à son groupe), `refresh_ancestors` (recalcul des groupes, renvoie l'objet du dessus à redessiner), `remove_from_group` (retire un objet, un groupe vidé disparaît à son tour) | `controllers/object_list_actions` |
| **controllers/generators.py** | `GeneratorsController` : boîte, puzzle, boules de Noël, porte-clés et gabarit. Fenêtres par `EditorForms` (valeurs simples ou None), calcul dans `vector/`, ajout par `VectorEditorController.import_objects` (le puzzle garde sa position, `keep_position`) ; garde les derniers réglages ; messages d'erreur par `i18n/errors.generator_error_text`. Testé sans fenêtre (`tests/test_generators_controller.py`) | `ui/vector_editor/builder`, `controllers/window` (menu Outils) |
| **controllers/layout.py** | `LayoutController` : imbrication (`open_nesting`) et duplication en série (`open_serial_duplicate`), taille de feuille partagée avec les boules (`sheet_default`, `remember_sheet`). C'est lui qui touche le canevas (annuler, ajout des exemplaires, sélection) : `vector/nesting_apply.py` (`apply_result`) et `vector/serial_apply.py` (`plan_serial_duplicate`) ne font que calculer et écrire les positions dans les objets | `ui/vector_editor/builder`, `GeneratorsController` |
| **ui/vector_editor/properties_panel.py** | `VectorPropertiesPanel` : panneau sous le canevas (description, X / Y, rotation, calque, largeur / hauteur avec ancrage), rempli d'après la sélection ; les saisies vont au contrôleur. Widgets construits par la fenêtre (`PropertiesWidgets`) | `main_window` |
| **vector/arrange.py** | Disposition : `group_bounds`, `align_offsets`, `distribute_offsets`, coins et ancrage d'une forme (`shape_world_anchor`), `resize_shape` | `controllers/vector_editor`, `ui/vector_editor/properties_panel` |
| **ui/user_dialogs.py** | `UserDialogs` : messages (`info`, `warning`, `error` ; `notify` pour un succès, écrit dans la barre d'état sans fenêtre à fermer), questions (`confirm` Oui / Annuler, `confirm_default_no` Oui / Non avec Non par défaut, `confirm_yes_no`, `ask_yes_no`), saisie de texte (`ask_text`), choix parmi plusieurs réponses (`choose`, renvoie la clé ou None) et choix de fichier ou de dossier (`save_file`, `open_file`, `open_folder`). Une instance par fenêtre (`main_window.dialogs`), passée à **tous les contrôleurs** : aucun n'ouvre de `QMessageBox` / `QFileDialog` / `QInputDialog` lui-même (vérifié par `tests/test_user_dialogs.py`). Dans les tests, remplacé par `tests/job_fakes.FakeDialogs`, qui répond à la place de l'utilisateur | `controllers/*` |
| **gcode/** | Génération du G-Code, fonctions pures sans Qt (aucun import de PyQt6, vérifié par `tests/test_gcode_package.py`) : `JobParams` (`params.py` : réglages d'un job en dataclass figée — un nom inconnu lève `TypeError` ; `image_cmd`, `image_overscan_enabled`, `overscan_for(largeur)`, `vector_origin()` ; construit par `JobController.build_params`, modifié par `dataclasses.replace`), `build_job_gcode` (en-tête, image, calques vectoriels, fin, d'après un `JobParams` ; résultat `GcodeResult`), fonctions communes à arguments explicites (`overscan_distance`, `scan_offset_mm`, `start_lines`, `timing.job_duration`) que la matrice de test et le motif aller/retour appellent avec leurs propres dictionnaires, `raster_image_gcode` et `image_origin` (gravure d'image, surbalayage, décalage des lignes retour ; ne visite que les pixels où la puissance change), `build_vector_layers_gcode` (gravure remplie, découpe, marquage ; commande et surbalayage de chaque calque ; compensation du kerf, ponts de maintien puis arcs d'entrée et de sortie des calques de découpe, voir `vector/kerf.py`, `vector/tabs.py` et `vector/lead.py` ; rampe de puissance d'une passe à l'autre pour les calques de contour, `_pass_power` : la puissance passe linéairement de celle du calque à `ramp_power`, le commentaire de chaque passe l'indique), `build_test_matrix_gcode`, `bidir_test_gcode` ; `preview` : modèle de l'aperçu 2D (`parse_preview`, `is_raster_group`, `cut_contours` (rejoint les tronçons qu'un pont de maintien sépare et écarte les arcs d'entrée et de sortie, pour que la matière de la pièce reste dessinée), `material_background_rect`, `raster_image`, `BurnTracker`, presets matière) | `workers` (`AdvancedGCodeWorker`, `TestMatrixWorker` : simples enveloppes de thread), `controllers/job`, `controllers/engraver` (cadrage : `image_origin`) |
| **gcode/rotary.py** | Axe rotatif, sans Qt : le G-Code du job, l'aperçu et les contrôles restent « à plat » (mm de surface) ; seul ce qui part vers la machine est converti. `RotaryConfig` (réglages `rotary_*` de `GrblConfig` : `from_settings`, `active`, `factor`, `circumference_mm`), `machine_gcode(text, config, header=True)` (ligne de commentaire d'en-tête pour le fichier enregistré, omise à l'envoi) et `machine_lines(lignes, config)` : chaque mot Y devient `facteur × Y` sur l'axe Y (`facteur = course_par_tour / (π × diamètre)`, diamètre de l'objet pour un mandrin, des rouleaux pour des rouleaux), ou un mot A en degrés (`360 / (π × diamètre)`) ; F est recalculé à chaque déplacement (`F × √(dx² + (facteur·dy)²) / √(dx² + dy²)`) pour que la surface avance à la vitesse demandée ; G90/G91 suivis ; arcs G2/G3 et pouces refusés (`RotaryError`) ; sans effet si inactif. `surface_y(y, config)` : position de la tête reconvertie pour l'aperçu (axe Y seulement). Appliqué par `controllers/engraver` (`start_stream` sans ligne d'en-tête : le texte envoyé garde les lignes du G-Code à plat, que `resume_gcode` repère par numéro de ligne ; `frame` ; refus avant confirmation dans `send_job` ; rappel dans la confirmation de lancement ; `_surface_head` reconvertit la position de la tête avant qu'elle serve à la reprise d'un job : axe Y reconverti, axe A inconnu donc reprise quelques lignes avant l'arrêt) et `controllers/job` (`export_gcode` ; contrôle du motif contre le tour de l'objet à la place de la course du plateau). `MachineConnection.start_stream(texte, fin, stream_text)` envoie le texte converti et garde le G-Code à plat dans `last_sent_gcode` (« Répéter »). `rotary_enabled` n'est pas enregistré dans les profils (décoché à chaque démarrage). Testé dans `tests/test_rotary.py` | `controllers/engraver`, `controllers/job`, `ui/app/job_display`, `ui/settings/grbl_config` |
| **controllers/engraver.py** | `EngraverController` : ports et connexion (vérification de `$22` et `$32` après connexion), pilotage (jog, homing, zéro, cadrage, pause, reset, console directe), envoi d'un job (« Envoyer au laser » avec une seule fenêtre de confirmation : avertissement de sécurité, points à vérifier de `launch_warnings` — G-Code périmé, lignes à risque, pas de homing — puis la question, par `launch_confirmation_text`, avec le rappel de l'axe rotatif s'il est actif (`_rotary_confirmation`) ; G-Code converti pour l'axe rotatif au moment de l'envoi (`gcode/rotary.py`) ; sur un graveur sans homing ($22), `$H` remplacé par `G4 P0` dans le G-Code envoyé (`grbl/commands.without_homing`) ; à l'ajout à la file, `confirm_safe_gcode` pour un G-Code périmé, qui réécrit la configuration ou dépasse le S-Max, aussi appelée par la file d'attente ; répétition ; reprise d'un job arrêté avant la fin : `resume_point`, signal `resume_available`, `resume_job` (signal `resume_starting(job entier, décalage des lignes)` : l'aperçu 2D garde le job entier et continue le tracé déjà gravé), qui en ALARM explique qu'il faut d'abord un homing ou un déverrouillage ; fin de job, reconnexion), cadrage (`frame(contour)`, voir `gcode/framing.py`), configuration GRBL (`$$` : lire, envoyer, exporter, importer). Questions par `UserDialogs`, résultats par signaux (`ports_changed`, `stream_starting`, `stream_ended`, `direct_job_started`…) ; `start_stream` / `end_stream` servent aussi à la file d'attente | `controllers/machine_connection`, `grbl/commands`, `main_window`, `window_controller` |
| **grbl/commands.py** | Commandes GRBL sans Qt : `HOME`, `UNLOCK`, `SET_WORK_ZERO`, `GO_TO_WORK_ZERO`, `jog_command`, `frame_commands` (laser allumé à la puissance donnée), `risky_lines` (lignes qui modifient la carte ou dépassent le S-Max), `parse_grbl_settings`, `setting_lines` (seulement les réglages numériques $N=valeur : jamais $RST, $N0, $J…), `homing_support` (base des futures macros) | `controllers/engraver`, `controllers/machine_connection` |
| **controllers/machine_connection.py** | `MachineConnection` (`QObject`, sans boîte de dialogue) : port série, threads (sondage de l'état, envoi du job, commandes, reconnexion après coupure), état « référencé » (`homed`, vrai seulement après le « ok » de `$H`), état du graveur (`state`, `can(action)`, signal `state_changed` ; table de `models/machine_state.py`) : l'activité en cours (commandes, homing, job) est notée au départ de son thread et effacée par son signal de fin, avant les fonctions de l'appelant ; refus de toute commande ou second job pendant une activité (`is_streaming`, `is_busy`), dernier job envoyé, `read_settings()` ($$). Signaux : `connection_changed`, `status_updated`, `log`, `position_lost`, `stream_progress` / `stream_lines_sent` / `stream_lines_acked`, `reconnecting` / `reconnected` | `grbl.connection`, `workers` |
| **controllers/separation.py** | `SeparationController` (`QObject`, boîtes de dialogue par `UserDialogs`) : ouverture, rotation et retrait de l'image source, tonalité cadrée sur la plaque envoyée à « Graver une image » (`tone_ready`), aperçus (original, gravure, impression, simulation) avec cache du calque couleur, aperçu affiché recalculé seul, les autres à leur ouverture (`preview_ready`), export (PNG et PDF 1:1, choix du dossier), réglages du verre appliqués à `ImageSettings` puis rendus (`apply_glass_settings` / `release_glass_settings`) | `image.separation`, `models/separation`, `models/image_settings` |
| **models/separation.py** | `SeparationSettings` (`SettingsModel`) : plaque, résolution d'impression, gain de point, saturation, clarté, miroir d'impression, diffusion, intensité ; liés aux champs de `SeparationTab` (le cadrage reste lu par `SeparationTab.frame_args`) | `controllers/separation` |

### 3.3 Vectoriel (cœur édition)

| Fichier | Rôle | Utilisé par |
|---------|------|-------------|
| **models/vector_document.py** | `VectorDocument` (`QObject`) : les objets du dessin, dans l'ordre (`add`, `remove`, `replace`, `object_by_id`, `serialize`, `load`), annuler / refaire (`push_snapshot`, `undo`, `redo`, `drop_last_snapshot`, 30 étapes), presse-papiers de l'éditeur (`copy`, `paste`, `duplicate`). Signaux `object_added`, `object_removed`, `objects_reset`, `objects_changed` (`notify_changed` après modification d'objets existants). Créé par la fenêtre (`main_window.vector_document`) et passé au canevas, qui en est la vue | `ui/vector_editor/canvas`, `controllers/job`, `controllers/vector_editor` |
| **vector/work_area.py** | Zone de travail de l'éditeur vectoriel, sans Qt : `WorkArea` (dataclass figée : plateau en mm, `px_per_mm`, `to_scene` / `to_mm` entre repère machine Y-haut et scène Qt Y-bas, `grid()` → `Grid` des graduations principales et secondaires, `grid_step`), `fit_scale` (zoom qui fait tenir un contenu dans la fenêtre) | `ui/vector_editor/canvas`, `scene_layers`, `navigation` |
| **vector/path_ops.py** | Opérations de géométrie qui fabriquent de nouveaux objets sans toucher au document : `ungroup_object` (sous-tracés d'un tracé ; grouper : `GroupObject`), `explode_object`, `bake_object` (forme ou texte en tracé), `can_ungroup`, `can_explode`, `path_to_polylines`, `polylines_to_path` | `ui/vector_editor/canvas` |
| **models/vector_objects.py** | Objets du dessin : `VectorObject` (position en mm, rotation, miroirs, calque, `world_path()`), `TextObject` (police, taille, texte sur un cercle ou le long d'un tracé), `ShapeObject`, `SvgPathObject` ; `to_dict` / `from_dict` | Canevas, générateurs, import, G-Code |
| **ui/vector_editor/** | `VectorEditorTab` (`tab.py`) : l'onglet — rangée des outils, barres flottantes du canevas (créer et dessiner, édition, alignement), champs des propriétés ; chaque bouton émet `command(nom)` (table `COMMANDS`, actions dans `VectorEditorController.commands()`), les outils de la souris `draw_tool_requested` (`VectorEditorController.choose_draw_tool`). L'interrupteur « Fond caméra » émet `camera_background_toggled(actif)` et « Actualiser l'image caméra » `camera_refresh_requested()` (`WindowController.set_camera_background_enabled` / `refresh_camera_clicked`) ; `show_camera_background` le coche sans émettre. `VectorCanvasView` (`canvas.py`, 360 lignes) : vue du `VectorDocument`, qui assemble ses parties et aiguille les événements vers elles : `work_area` (`vector/work_area.py`, `WorkArea` figée et sans Qt : plateau, échelle, `to_scene` / `to_mm`, grille `grid()`, `fit_scale`), `grid` et `camera` (`scene_layers.py` : `WorkAreaLayer`, plateau gradué ; `CameraLayer`, image de la caméra, `show` / `clear` / `set_opacity`), `items` (`document_items.py`, `DocumentItems` : un élément graphique par objet, créé, redessiné ou retiré d'après les signaux du document, empilé dans son ordre ; sélection `select` / `selected` / `selected_object` / `select_all_active` ; testable avec une simple scène), `navigation` (`navigation.py`, `ViewNavigator` : zoom, cadrage différé `request_recenter`, `center_on`) et les raccourcis (`shortcuts.py` : `key_command`, `zoom_direction`, `arrow_nudge`). Il garde les entrées utilisées partout : `objects`, `add_object`, `item_for`, `select_objects`, `selected_items_vector`, `push_undo_snapshot`, `set_work_area` (redessine aussi les objets : leur Y d'écran dépend de la hauteur du plateau), `scene_to_mm` / `mm_to_scene`, `px_per_mm`, `set_draw_tool` / `draw_tool`, `set_camera_background`. Il ne modifie pas le document lui-même : clavier et clic droit émettent `command_requested(nom)`, `nudge_requested`, `layer_requested`, `combine_requested`, `shape_requested`, `text_resync_requested`, et `objects_moved` après un déplacement à la souris (textes liés à recaler). Ses gestionnaires d'événements passent la main, dans un ordre de priorité fixe, aux outils de `tools/` qui gardent chacun leur état : `EndpointSnap` (accroche aux extrémités), `DrawingTool` (ligne, rectangle 3 points, cercle, ellipse, dimensions au clavier), `MeasureTool`, `NodeEditor` (glisser, ajouter, supprimer un sommet), `MoveTool` (déplacement groupé avec grille, panoramique), `FollowHandle` (glisser un texte le long de son contour) ; on les appelle directement (`canvas.nodes.enter()`, `canvas.measure.clear_labels()`…). Le menu du clic droit est construit par `context_menu.build_context_menu` ; le calcul du texte sur contour est dans `vector/text_follow.py`, celui de la sélection traitée comme un groupe (redimensionner, quart de tour, calque) dans `vector/group_transform.py`, la boîte de taille dans `resize_dialog.py` (`GroupResizeDialog`, ouverte par `EditorForms.group_resize`). Testés avec de vrais événements souris et clavier (`tests/test_canvas_tools.py`), et chaque partie seule (`tests/test_canvas_parts.py`). `VectorGraphicsItem` (`item.py`) : un objet sur le canevas (rappel du double-clic `on_double_click`). Boîtes de saisie : `TextInsertDialog`, `MedalTextDialog`, `ShapeInsertDialog`, `AssignLayerDialog` | `main_window`, `controllers/vector_editor` |
| **ui/tabs/layers/layer_table.py** | `LayerManagerWidget` : tableau des calques, vue de `LayersModel` (colonnes Couleur, Nom, Mode, Puissance, Vitesse, Passes, Pas, Surbalayage — grisée hors gravure remplie —, Laser — Auto / M4 / M3 —, Ponts, Larg. pont, Kerf et Arc — case et valeur, grisées hors découpe ; le nombre et les largeurs le sont aussi tant que leur case est décochée —, Perforation — trait et vide, grisés hors mode Perforation —, Rampe — case et puissance finale, grisées hors découpe, perforation et marquage —, Actif) | `ui/tabs/layers/tab.py` |
| **vector/svg_extract.py** / **vector/layer_data.py** | Lecture des tracés SVG (`d` de `<path>`, arcs en courbes exactes) et fusion de tracés, pour les importeurs ; objets → polygones en mm par calque pour `gcode/vector` (`extract_vector_layer_data`) | `vector/svg_tree_import`, `vector/svg_import`, `controllers/job` |
| **vector/importers.py** / **vector/dxf.py** | Import SVG/DXF (groupé par défaut) | `controllers/vector_editor` |
| **vector/svg_import.py** | Modèles de la bibliothèque, avant l'import : options = sous-calques d'un groupe, un seul visible (`find_variant_groups`) ; textes remplaçables (`find_texts`, y compris dans un `<mask>`) ; `svg_preview` applique options et textes au fichier (aperçu de la fiche ; `drop_hidden` retire ce qui reste caché, pour l'import). Fournit aussi à `svg_tree_import` ses briques de lecture (transformations, unités, formes, traits, textes). L'import lui-même passe par `svg_tree_import.import_library_svg` : plus de blanc qui creuse, les modèles font de vraies Différences | `controllers/library`, `ui/dialogs/library`, `vector/svg_tree_import` |
| **vector/boolean_ops.py** · `GroupObject` (**models/vector_objects.py**) | Groupes de l'éditeur vectoriel. `combine(tracés, opération)` (sans widget) : GROUP juxtapose, UNION / DIFFERENCE / INTERSECTION / EXCLUSION combinent les tracés du dessous vers le dessus, chacun en règle pair-impair. `GroupObject` garde ses objets entiers (`children`, à leur place au groupement, `origin`) et se déplace / pivote comme un tracé SVG ; `placement()` ramène les objets à leur place actuelle, `released_children()` les rend au dégroupage, `engraving_parts()` donne [(calque, tracé)] à graver : chaque objet d'un simple groupe, ou le tracé combiné sur le calque du groupe (celui de l'objet du dessous). `VectorDocument.move` change l'ordre (signal `order_changed`, empilement du canevas). Masquer : `hidden` (affichage seulement, toujours gravé) ; ignorer : `set_ignored` met l'objet sur `IGNORED_LAYER_ID`, pseudo-calque hors du modèle des calques (la génération ne prend que les calques actifs) en retenant `saved_layer_id` ; un groupe le fait pour chacun de ses objets, et un objet ignoré ne compte plus dans son opération | `ui/vector_editor/canvas`, `vector/layer_data`, `controllers/vector_editor` |
| **ui/vector_editor/objects_panel.py** | `ObjectsPanel` : liste des objets à droite du canevas (du dessus vers le dessous, groupes dépliables, calque), boutons monter / descendre / grouper / dégrouper / combiner ; signaux `selection_requested`, `move_requested`, `group_requested`, `ungroup_requested`, `rename_requested`, `visibility_requested` (œil), `ignore_requested` (« X »), `delete_requested` (poubelle), branchés par `ui/vector_editor/builder.py` sur le canevas et `VectorEditorController` (`move_objects`, `group_selection`, `ungroup_selection`, `rename_object`, `set_object_visible`, `toggle_ignored`, `delete_object`) | `ui/vector_editor/tab`, `builder` |
| **vector/svg_tree_import.py** · **vector/svg_style.py** | Import SVG du bouton « Importer », d'après la spécification SVG du W3C. `svg_style` (sans Qt) : `parse_color` (147 noms CSS, #rgb[a], #rrggbb[aa], rgb[a](), hsl[a](), currentColor), `StyleSheet` (feuille `<style>`, sélecteurs simples), `computed_style` (présentation < feuille < style, `!important`, `inherit`, héritage limité aux propriétés héritées), `paint_alpha`. `svg_tree_import` : parcours du rendu (display:none, visibility héritée et rétablissable, opacité cumulée, fill-rule converti en pair-impair, `<use>`/`<symbol>`, `<switch>`, `<svg>` imbriqué, preserveAspectRatio via `svg_import.viewbox_transform`, clipPath et mask (surfaces découpées, contours gardés en traits par `svg_geometry.clip_lines`, texte gardé modifiable s'il est entièrement visible), tirets `svg_geometry.dashed`, longueurs `svg_geometry.user_length`, propriété CSS transform, px de 90 (Inkscape < 0.92) ou 72 (Illustrator) par pouce : `document_px_mm`) ; un `GroupObject` par groupe, nommé par inkscape:label ou `<title>` ; `color_role` : couleur -> rôle de calque (teinte ± 30°), blanc -> calque « Ignoré » ; ce qui ne se dessine pas -> calque « Ignoré ». Le contenu d'un `<mask>` est peint par `boolean_ops.paint_region` (clair visible, sombre caché) | `controllers/vector_editor` (import_file), `controllers/library` et les aperçus de la bibliothèque (`import_library_svg`) |
| **library/machine_catalog.py** | Catalogue des machines, sans Qt : `MachineModel` (surface, point, vitesses par axe, laser, sources, date de vérification ; `profile_values()` donne les clés w, h, focal, max_speed d'un profil machine, la focale étant la moyenne des deux dimensions du point et la vitesse celle de l'axe le plus lent), `load_machine_catalog` (fichiers de `resources/machines/` puis du dossier `machines/` des données, prioritaire). Fenêtre `ui/dialogs/machine_catalog/` ouverte par « Depuis le catalogue… » (`open_machine_catalog`, `ui/settings/machine_params/builder.py`) ; profil créé par `MachineProfilesController.new_profile_from_catalog` | `ui/settings/machine_params/builder` |
| **library/catalog.py** | Catalogue de la bibliothèque, sans Qt : catégories et modèles des dossiers `resources/library/` (à côté de l'exécutable et dans le bundle), `_category.json`, `info.json`, aperçu, readme | `controllers/library` |
| **controllers/library.py** | `LibraryController` : fournit la page « Bibliothèque » de la fenêtre des générateurs (`generator_request` : catalogue, taille des aperçus mémorisée ; ouverte par `GeneratorsController.open_generators`), importe (`import_choice`) le modèle choisi avec ses variantes, chaque rôle sur le calque de base de même rôle, par `VectorEditorController.import_objects`. Plus aucun contrôleur ne construit de fenêtre (garde-fou : `tests/test_generators_controller.py`) | `main_window`, `window_controller` |
| **vector/order.py** / **vector/nudge.py** / **vector/font.py** | Ordre de coupe, nudge clavier, polices | Éditeur |
| **vector/tabs.py** | Ponts de maintien (micro-joints), sans Qt : `cut_runs(poly, count, width)` renvoie les tronçons À COUPER d'un contour fermé (les ponts en sont exclus), `effective_count` (un petit contour en reçoit moins, ou aucun : chaque tronçon coupé fait au moins 2 largeurs de pont), `tab_positions`, `is_closed`, `perimeter`. Ponts répartis à égale distance, centrés entre le point de départ et le suivant. `gcode/vector._tabbed_polygons` ne les pose que sur les contours extérieurs fermés (profondeur d'imbrication paire, `order.nesting_depths`) : ni trous ni tracés ouverts ; chaque tronçon est un tracé à part, à chaque passe. Testé dans `tests/test_cut_tabs.py` | `gcode/vector`, `gcode/preview` |
| **vector/kerf.py** | Compensation du kerf, sans Qt : `compensate_kerf(polygons, kerf_mm)` décale chaque contour FERMÉ de kerf/2 (vers l'extérieur pour une pièce, vers l'intérieur pour un trou : profondeur d'imbrication paire ou impaire, `order.nesting_depths`) et renvoie `(tracés, décalés, non compensés)` ; les tracés ouverts ne changent pas. `offset_polygon(poly, d)` : chaque côté déplacé de `d`, sommets rejoints par leur intersection, biseau au-delà de `MITER_LIMIT` fois le décalage ; le résultat est vérifié (aire dans le bon sens, côtés non retournés, aucune boucle) et refusé (`None`) pour un détail plus fin que le décalage : le contour est alors coupé tel quel et signalé dans le G-Code (`; ATTENTION : … contour(s) trop fin(s)`). Appliquée par `gcode/vector` avant l'ordre de coupe et les ponts. Testé dans `tests/test_kerf.py` | `gcode/vector` |
| **vector/lead.py** | Arcs d'entrée et de sortie, sans Qt : `add_leads(paths, reference, radius, skip)` ajoute à chaque contour fermé un quart de cercle tangent au départ (le laser s'allume sur la chute) et un autre à l'arrivée ; la chute est à l'extérieur d'une pièce et à l'intérieur d'un trou (profondeur d'imbrication, `order.nesting_depths`, comme le kerf et les ponts). Un arc n'est posé que s'il a la place (aucun croisement de contour, aucun point sur la matière d'une pièce voisine, règle pair-impair) : rayon réduit de moitié puis d'un quart, contour repris du milieu de son plus long côté (coin de trou), sinon contour coupé sans arc et compté à part (`; ATTENTION : … sans arc` dans le G-Code). Tracés ouverts et tronçons à ponts : sans arc. Renvoie `(tracés, avec arc, sans arc)`. Testé dans `tests/test_cut_lead.py` | `gcode/vector` |
| **vector/perforate.py** | Perforation (mode de calque `perforate`), sans Qt : `perforate(polygons, dash, gap)` coupe chaque tracé par traits de `dash` mm séparés de vides de `gap` mm et renvoie `(traits, nombre de traits)` ; `dashes(poly, dash, gap)` pour un tracé. Le motif est ajusté à la longueur : un tracé fermé fait un nombre entier de périodes, un tracé ouvert commence et finit par un trait ; trait et vide sont mis à l'échelle (rapport conservé). Un tracé plus court qu'un trait est coupé en entier. Les traits suivent les angles du tracé. `gcode/vector` les écrit comme les autres contours (G0 laser éteint entre deux traits) ; ni kerf, ni ponts, ni arcs (réservés à la découpe) ; le mode n'est pas une découpe pour l'ordre de coupe (exécuté avant les découpes, comme le marquage). Réglages du calque : `perf_dash` et `perf_gap` (mm, 2,0 et 1,0 par défaut, entre `PERF_LENGTH_MIN_MM` et `PERF_LENGTH_MAX_MM`). Testé dans `tests/test_perforation.py` | `gcode/vector` |
| **vector/text_on_path.py** | Texte le long d'un tracé quelconque, sans Qt : `path_placements(advances, points, center_fraction, spacing, reverse, gap)` donne `(x, y, rotation)` de chaque lettre (direction = corde sous la largeur de la lettre ; prolongement droit au-delà d'un tracé ouvert, bouclage sur un tracé fermé). `orient_path` (fermé : sens horaire ; ouvert : de gauche à droite), `default_center_fraction`, `is_closed`, `relative_points`, `scaled_points`. Testé dans `tests/test_text_on_path.py` | `models/vector_objects.TextObject._follow_path` |
| **vector/text_on_arc.py** | Texte sur un cercle, sans Qt : `arc_placements(advances, rayon, centre, intérieur, espacement)` donne `(x, y, rotation)` de chaque lettre (repère mathématique, Y vers le haut, centre du cercle en (0, 0) ; 90° = haut, 270° = bas), `arc_span_deg`, `text_length`, `default_center_deg`. Extérieur : lettres vers l'extérieur, lu dans le sens horaire ; intérieur : lettres vers le centre, lu de gauche à droite en bas. Testé dans `tests/test_text_on_arc.py` | `models/vector_objects.TextObject` |
| **vector/box_generator.py** / **box_3d.py** / **box_presets.py** | Boîte à encoches, modèle 3D de la boîte assemblée (aperçu), préréglages nommés | `controllers/vector_editor`, `ui/dialogs/box_generator` |
| **vector/puzzle_generator.py** / **vector/nesting.py** / **vector/nesting_apply.py** | Puzzle jigsaw, imbrication | `controllers/vector_editor`, `ui/dialogs` |
| **vector/ornament_generator.py** / **ornament_motifs.py** / **ornament_region.py** / **keychain_generator.py** | Boules de Noël (géométrie, motifs, soudure) et porte-clés prénom (voir §8.0 et §8.2) | `controllers/vector_editor`, `ui/dialogs/ornament`, `ui/dialogs/keychain` |
| **vector/serial_duplicate.py** / **vector/serial_apply.py** | Duplication en série : exemplaires, texte par exemplaire, grille (logique pure, testée sans Qt) ; passerelle vers le canevas et l'imbrication | `controllers/vector_editor`, `ui/dialogs/serial_duplicate` |
| **vector/jig.py** | Gabarit de placement : géométrie de la plaque et des poches (logique pure, testée sans Qt) ; les objets sont créés par `vector/importers.jig_to_objects` | `controllers/vector_editor`, `ui/dialogs/jig` |

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

Modèle / vue / contrôleur, comme LSP, et sans aucun import de `laser_studio` (un test le vérifie) : le Studio se lance seul.

| Fichier | Rôle |
|---------|------|
| **core/**, **lightbox.py**, **engrave.py**, **subject_ai.py** | `core/` rangé par métier : params (réglages, résultat), framing (cadrage), subject (sujet, visage), tones (tons -> matière), plate (formes, anneau, œillet, ponts, contours), halftone (trame), engraving (gravure), lowpoly, qr, colors (palette), layers (multicouche), pipeline (`process`), render (aperçus), export (SVG, DXF) ; `core/__init__.py` expose les noms utilisés par l'API, la CLI et les tests (`core.process`, `core.Params`…). Calcul sans Qt : pochoir, trame, gravure, couches, QR, low poly, caisson lumineux, détourage par IA (onnxruntime, facultatif) |
| **models/session.py** | `StudioSession` : photo chargée, version d'affichage, repères peints (sujet / fond), numéros de version pour le cache |
| **models/presets.py** | `PresetsStore` : réglages enregistrés (`presets.json`, dans le dossier du Studio ou le profil de l'utilisateur) |
| **controllers/api.py** | `StudioApi` : ce que la page demande (aperçu, détection du visage, export SVG / DXF / caisson / test de flexion), un calcul à la fois, résultat en cache |
| **server.py** | Serveur HTTP local (127.0.0.1) : routes vers `StudioApi`, page `ui/studio.html`, langues ; `start_server(port)` dans un thread |
| **controllers/studio.py** | `StencilStudioController` : ouverture de la fenêtre, préchauffage (imports dans un thread, page chargée dans une fenêtre invisible), repli en processus séparé ou dans le navigateur, thème à chaud. Reçoit de LSP `theme()` (couleurs), la langue et `dialogs` ; émet `export_ready(chemin)` |
| **ui/dialog.py** | `StudioDialog` : vue QtWebEngine, couleurs passées à `window.setTheme`, exports SVG / DXF téléchargés puis annoncés (`export_downloaded`), les autres fichiers enregistrés |
| **ui/window.py** | Le Studio dans son propre processus (Qt refuse QtWebEngine dans LSP) : écrit `STENCIL_EXPORT:<chemin>` sur sa sortie à chaque export |
| **ui/themes.py** | Couleurs par défaut et repli d'après la palette Qt ; dans LSP, elles viennent de `laser_studio.ui.app.theme.page_colors` |

Côté LSP : `WindowController.stencil()` crée le contrôleur, `VectorImporter.import_stencil_export` (`editor.importer`) importe ses exports (voir 8.1). `selftest.py` vérifie que les bibliothèques d'un PC (OpenCV, numpy, scipy) donnent les mêmes résultats que les valeurs attendues.

### 3.6 Image, machine, build

Inchangé dans l’esprit : `controllers/workers.py` (threads), `grbl/`, `ui/settings/window.py`, scripts `build.bat` / `macos/` / `setup.iss`. Voir CHANGELOG pour le détail des versions.

---

## 4. Schéma des dépendances principales

```
main.py
  ├─ ui.app.theme.apply_app_theme
  ├─ resources/icons/breeze  (QIcon theme)
  └─ FullLaserStudio
        ├─ WindowController ──► menu thème ──► change_theme ──► ui.app.theme
        │                 ├─► StencilStudioController (stencil_studio) ──► StudioDialog ──► server ──► StudioApi
        │                 │       (couleurs : page_colors ; exports : export_ready ──► import_stencil_export)
        │                 └─► CameraController ──► camera/ (capture, lens_calibration, workspace_alignment, storage)
        │                                      └─► ui/dialogs/camera/ (dialog, lens_wizard, align_wizard)
        ├─ VectorEditorController (controllers/vector_editor) ──► VectorDocument ◄── VectorCanvasView (ui/vector_editor/canvas)
        │         ├─ import SVG/DXF (groupé)
        │         ├─ panneau des propriétés (ui/vector_editor/properties_panel)
        │         ├─ explode_selected / enter_node_edit
        │         └─ nesting / box_generator / puzzle_generator
        ├─ JobController (controllers/job) ──► controllers/workers (threads) ──► gcode/ (G-Code sans Qt)
        │         └─ signaux ──► JobDisplay (console) ──► Preview2DTab ◄── gcode/preview (aperçu sans Qt)
        └─ EngraverController (controllers/engraver) ──► MachineConnection ──► grbl.connection / grbl.simulator ; grbl/commands
```

---

## 5. Flux fonctionnels typiques

### 5.1 Gravure image
Chargement → filtres (`ImageController`, calcul dans `image/dithering`) → génération G-Code → stream machine.

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
    └─ si Stencil Studio ouvert → StencilStudioController.set_theme(page_colors(name))
```

### 5.4 Stencil Studio → LSP
Export SVG/DXF dans le Studio → téléchargement intercepté par `StudioDialog` → `export_ready(chemin)` → `VectorEditorController.import_stencil_export` : objets rangés dans les calques (`controllers/stencil_import.py`), une étape d'annulation, fichier temporaire supprimé ; repli sur l'import standard si le fichier est illisible.

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

1. **Pas de mixin** : modèle / vue / contrôleur, objets qui reçoivent ce dont ils ont besoin ; ne pas mélanger les responsabilités (UI ≠ G-Code ≠ USB).
2. **Repère machine** : origine bas-gauche, Y vers le haut dans le modèle monde ; conversion écran dans `VectorGraphicsItem.refresh`.
3. **Import vectoriel groupé par défaut** ; dégroupage / explosion **explicites** (clic droit ou boutons).
4. **Thème unique source de vérité** : `ui.app.theme.THEMES` + la préférence `app_theme` (`current_theme_name`, relue par `apply_saved_theme`) ; Stencil Studio reçoit ses couleurs par `page_colors`.
5. **Undo canevas** : toute mutation géométrique (nœuds, explode, dessin) doit appeler `push_undo_snapshot()` avant modification.
6. **i18n** : toute nouvelle chaîne UI passe par `tr("…")`, avec sa clé dans le module de sa zone, `i18n/texts/<zone>.py`.
7. **Ressources** : images dans `resources/`, chargées via `find_resource` ; pack d'icônes `resources/icons/` ; penser à `--add-data "resources;resources"` dans les builds.
8. **Logique caméra découplée de Qt** : les calculs de distorsion (`lens_calibration.py`), d'homographie (`workspace_alignment.py`) et de capture (`capture.py`) résident dans `camera/` sans dépendance PyQt6 pour rester testables unitairement.
9. **Calcul sans interface** : `gcode/`, `grbl/`, `image/`, `camera/`, `library/` n'importent pas Qt ; `vector/` utilise QtGui et les valeurs de QtCore comme bibliothèque de géométrie, jamais QtWidgets. Vérifié par `tests/test_pure_modules.py`.
10. **Préférences** : toujours par `core/preferences.py`, jamais `QSettings` directement ; dans les tests, `memory_preferences(self)` (tests/job_fakes.py).
11. **Erreurs** : un `except Exception` journalise l'erreur (`core/debug_log`, actif avec `LASER_STUDIO_DEBUG`), la signale ou la relance ; s'il se tait, un commentaire dit pourquoi (vérifié par `tests/test_exceptions.py`). Les tests qui construisent la fenêtre le font avec des préférences en mémoire (`job_fakes.start_memory_preferences`, vérifié par `tests/test_preferences.py`).

---

## 7. Évolutions récentes (mémo)

| Domaine | Ajout |
|---------|--------|
| Thèmes | `dark`, `light`, `dusk`, `warm`, puis **`neon`**, **`retro80`**, **`jarvis`** (`ui/app/theme.py`) |
| Icônes | Packs **Breeze** et **Jarvis** embarqués (`resources/icons/`) |
| Import | Plus de dégroupage automatique SVG/DXF |
| Dessin | Outils souris ligne / rectangle / ellipse |
| Édition | **Exploser en segments** + **mode nœuds** |
| Stencil Studio | Thème lié à LSP (7 thèmes, sync à chaud), autotest `selftest.py` ; modèle / vue / contrôleur (`models/`, `controllers/`, `ui/`), plus aucun import de LSP, routage des exports dans `controllers/stencil_import.py` |
| UI claire | Stylesheet dédié (boutons ±, spinbox, etc.) |
| Sécurité | Avertissement laser au démarrage (`controllers/startup_safety`, `ui/dialogs/startup_safety`), rappel périodique, `NOWARNING` pour les tests |
| Machine | `grbl/ports.py` : ports virtuels masqués, dernier port mémorisé ; aide « Port introuvable ? ». Pilotage du graveur dans `EngraverController`, commandes dans `grbl/commands.py` ; `LaserControlMixin` supprimé |
| Boîte | Couvercles `hinged` / `pinned`, pieds, aimants, motifs gravés, aperçu 3D, préréglages |
| Générateurs | Porte-clés prénom (`keychain_generator`), motifs de boules de Noël (`ornament_motifs`) |
| Interface | `FloatingToolBar` sur les aperçus |
| Texte | Texte sur un cercle (médailles, tampons), voir `vector/text_on_arc.py` ; texte le long de n'importe quel objet, voir `vector/text_on_path.py` |
| Dessin | Boutons séparés cercle / ellipse, tracés d'un seul geste ; le rectangle garde ses 3 points ; icônes `draw-circle` et `text-follow-path` (Breeze et Jarvis) |
| Image | `ImageProcessingMixin` supprimé : tramage sans Qt dans `image/dithering` (résultat identique, vérifié sur 144 traitements et 60 vignettes), image et traitement dans `ImageController`, résolution dans `ResolutionBox`, affichage dans `ImageTab` |
| Fenêtre | `WindowControllerMixin` supprimé, plus aucun mixin : `WindowController` (menus, réglages), `WindowState` (réglages machine, profils, projet), `MainTabs` (onglets, plein écran, panneau du bas), `JobDisplay` (résultats du job, état du graveur), `ImageToolbarActions` (barre d'outils de l'image) |
| Séparation | `SeparationMixin` supprimé : actions (ouverture, rotation, aperçus, export) dans `SeparationController`, affichage dans `SeparationTab`, test du gain de point dans `JobController` |
| Modes de calque | Codes indépendants de la langue (`models/layer_modes`) ; matériau choisi enregistré automatiquement |
| G-Code | Génération sortie des threads et de `vector_layers` dans le paquet `gcode/`, sans Qt et testée seule ; G-Code inchangé. Préparation du job dans `JobController` (`controllers/job.py`), boîtes de dialogue par `UserDialogs`. Aperçu 2D : modèle `gcode/preview.py`, dessin dans `Preview2DTab` ; `GcodeGenerationMixin` supprimé. Boîtes de dialogue des contrôleurs : toutes par `UserDialogs` |
| Build | `packaging/pyinstaller/` (spec commun, filtre), AppImage, workflows `tests.yml` / `release.yml` ; numpy 2, OpenCV headless |
| Caméra | Module `camera/` (calibration objectif, alignement homographique du plateau) + assistants (`ui/dialogs/camera/`) + superposition sur le canevas vectoriel |

---

## 8. Générateur de Puzzle

| Fichier | Rôle |
|---------|------|
| **vector/puzzle_generator.py** | Géométrie jigsaw (ergot à col étroit et tête ronde qui déborde : 3 Béziers, dimensionné sur la plus petite dimension d'une pièce, hauteur plafonnée par `MAX_TAB_DEPTH` = 0,30) + grille ondulée ; validation ; `PuzzleResult` : `pieces` (aperçu seulement), **`outline`** (contour extérieur fermé, agrandi de kerf/2) et **`edges`** (arêtes internes, chacune une seule fois, tracés ouverts) |
| **ui/dialogs/puzzle/** | `PuzzleGeneratorDialog` (aperçu live, réglages forme, calque de découpe) |
| **vector/importers.puzzle_to_objects** | `outline` + `edges` → 2 `SvgPathObject` (contour fermé ; arêtes internes regroupées en un objet) |
| **GeneratorsController.open_puzzle_generator** | Fenêtre des générateurs ouverte sur le puzzle (`open_generators`), puis `_make_puzzle` : placement sur canevas |
| **ui/vector_editor/tab.py** (`EDIT_ACTIONS`) | Icône « Générateurs » de la barre d'édition (fenêtre unique des générateurs) ; `EDIT_GROUPS` range les outils plus rares dans les boutons à menu « Disposer » et « Tracés et textes » (`_grouped`) |
| **i18n/texts/** | Clés `menu.tools.puzzle`, `ui.vector_puzzle_*`, `puzzle.*`, `puzzle.err.*` |

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
| **GeneratorsController.open_ornament_generator** | Fenêtre des générateurs ouverte sur la boule (`open_generators`), puis `_make_ornament` : placement sur le canevas |
| **i18n/texts/** | Clés `menu.tools.ornament`, `ui.vector_ornament_generator*`, `ornament.*`, `ornament.err.*` |

Principes : le prénom, les flocons et l'anneau sont **soudés** en une seule pièce avant d'être envoyés au laser : un contour qui traverse de la matière serait découpé à l'intérieur d'une lettre. Les lettres sont d'abord fusionnées (écritures cursives), leurs contreformes (a, e, o) restent des contours à part. Le prénom est tenu à l'anneau par une barre posée sur la ligne de base (choix « Barre », par défaut) ; sans elle il doit toucher l'anneau des deux côtés (`floating_name` avertit sinon). Un point de i ou un accent reste détaché et tombe. Tests : `tests/test_ornament_generator.py` (formes et disposition sans Qt ; soudure avec le vrai Qt, ignorée sans lui).

## 8.1 Stencil Studio → calques (controllers/stencil_import.py)

Export Studio vers LSP : routage par nom de calque DXF / groupe SVG

| Nom export | Calque LSP |
|------------|------------|
| CUT | Découpe |
| FRAME (cadrage, mark, contour) | Marquage (de préférence un calque dont le nom contient « cadr ») |
| ENGRAVE (gravure, fill) | Gravure remplie |
| LAYER_n | Calque dédié `LAYER_n` (créé si besoin par `LayersModel.append_layer`), mode Découpe, réglages repris du premier calque Découpe, pas de remplissage = focale de la machine |

Fichier : **src/laser_studio/controllers/stencil_import.py** (`route_objects`, `ensure_multi_layer`, `kind_for_layer_name`, `pick_layer`, `import_summary`), appelé par `VectorEditorController.import_stencil_export`.

## 8.2 Porte-clés prénom (NameKey)

| Fichier | Rôle |
|---------|------|
| **vector/keychain_generator.py** | Géométrie pure, sans Qt (`build_keychain`, `KeychainParams`, `KeychainResult`, `KeychainError`) : prénom, base dilatée soudée à l'anneau. Deux ensembles de polygones fermés : `base_contours` (base + trou d'anneau → calque Découpe) et `text_contours` (texte centré sur la base → calque Gravure). Repère LSP (mm, Y vers le haut, coin bas-gauche en (0, 0)) |
| **ui/dialogs/keychain/** | `KeychainGeneratorDialog` + `KeychainPreview` : aperçu en direct découpe + gravure ; `error_text()` |
| **vector/importers.keychain_to_objects** | Contours → objets sur le calque de découpe et celui de gravure |
| **GeneratorsController.open_keychain_generator** | Fenêtre des générateurs ouverte sur le porte-clés (réglages mémorisés dans `keychain_settings`), puis `_make_keychain` : placement sur le canevas ; lancé par le menu Outils (`keychain_generator_requested`) ou l'icône « Générateurs » de l'éditeur |

## 9. Commandes utiles

```bash
# Lancer l’application
python main.py

# Lancer Stencil Studio seul, dans le navigateur
cd src && python -m stencil_studio

# Tests (comme le workflow tests.yml)
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests

# Qualité traductions / UI (check_ui_attributes et ruff tournent aussi en CI, job « checks »)
python tools/check_translations.py
python tools/check_ui_attributes.py
ruff check src tools tests        # réglages dans [tool.ruff] de pyproject.toml

# Compilation syntaxe rapide
python -m compileall -q main.py src
```

---

*Document d’architecture — à tenir à jour lors des changements structurants (nouveaux contrôleurs, flux d’import, thèmes, pont Stencil Studio, caméra, arborescence).*