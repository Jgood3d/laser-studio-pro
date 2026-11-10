# Laser Studio Pro — Architecture & cartographie du code

> Document mis à jour pour faciliter la prise en main et la modification du projet.  
> Branche de référence : **Dev** — dépôt : https://github.com/Jgood3d/laser-studio-pro  
> Version applicative : **2.5.0** (voir `app_utils.APP_VERSION`)

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
  ├─► install_breeze_icon_theme()   # icons/breeze (surtout Windows)
  ├─► apply_app_theme()            # app_theme.py (dark / light / dusk / warm)
  ├─► StartupSplash
  │
  └─► main_window.py  (classe FullLaserStudio : construit la fenêtre, init_ui)
        │
        │  Hérite de tous les mixins :
        │
        ├─ UiSetupMixin          (ui_setup_mixin.py)    contenu des onglets (éditeur vectoriel…)
        ├─ WindowControllerMixin (ui_window_controller.py) signaux du menu, thème, connexion
        ├─ …PageMixin            (ui_*_page.py)         pages de réglages
        ├─ ImageTabMixin, Preview2DTabMixin, JobTabsMixin,
        │  LegacySvgBoxMixin                           (ui_*.py, un par bloc)
        ├─ MachineProfilesMixin  (machine_profiles_mixin.py)
        ├─ ImageProcessingMixin  (image_processing_mixin.py)
        ├─ VectorEditingMixin    (vector_editing_mixin.py)
        ├─ GcodeGenerationMixin  (gcode_generation_mixin.py)
        ├─ LaserControlMixin     (laser_control_mixin.py)
        ├─ ProjectIOMixin        (project_io_mixin.py)
        ├─ JobQueueMixin         (job_queue_mixin.py)
        ├─ Png2SvgMixin          (png2svg_mixin.py)
        └─ SeparationMixin       (separation_mixin.py)
```

`FullLaserStudio` est le **cœur** : il assemble les mixins et possède les objets partagés (`usb`, `layer_manager`, images, file d’attente…).

---

## 2. Arborescence complète

```
laser-studio-pro/
├── .github/workflows/macos-build.yml
├── docs/                             # captures, page de présentation
├── macos/                            # build macOS (spec, scripts, icns)
├── icons/
│   └── breeze/                       # thème d’icônes FreeDesktop embarqué
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
│   └── check_ui_attributes.py
├── main.py                           # point d’entrée (+ Breeze + thème)
├── main_window.py
├── app_theme.py                      # thèmes UI : dark / light / dusk / warm
├── app_utils.py
├── i18n.py
├── debug_log.py / qt_messages.py
├── simulated_grbl.py / usb_controller.py / workers.py
├── graphics_view.py / widgets_extra.py / ui_utils.py
├── ui_setup_mixin.py
├── ui_window_controller.py / ui_legacy_svg_box.py
├── ui_image_tab.py / ui_preview_2d_tab.py / ui_job_tabs.py   # onglets
├── ui_machine_params_page.py / ui_machine_profiles_page.py
├── ui_test_matrix_page.py / ui_grbl_config_page.py            # pages de réglages
├── ui/about/ / ui/support/ / ui/buy_me_a_coffee/   # boîtes du menu Aide (classes), bouton ko-fi
├── ui/splashscreen/                  # écran de démarrage (StartupSplash)
├── ui/statusbar/                     # barre d'état (StatusBar : messages, progression)
├── ui/app/menu/                      # menu et barre d'outils (AppActions, AppMenuBar, AppToolBar)
├── ui/machine/controls/              # panneau de pilotage (JogControlPanel, signaux)
├── ui/machine/job_actions/           # actions de job (JobActionsPanel, signaux)
├── ui/machine/dro/                   # position de la machine (DroPanel : set_status, unlock_requested)
├── ui/machine/console/               # console directe (DirectConsolePanel : command_submitted)
├── ui/tabs/layers/                   # onglet Calques (LayersTab : layers_changed)
├── settings_window.py
├── machine_profiles_mixin.py
├── image_processing_mixin.py / image_filters.py / image_size.py
├── vector_editing_mixin.py
├── vector_layers.py                  # calques + canevas + nœuds / explode
├── vector_font.py / vector_order.py / vector_nudge.py / vector_import.py
├── dxf_import.py
├── box_generator.py / box_dialog.py
├── nesting.py / nesting_apply.py / nesting_dialog.py
├── gcode_generation_mixin.py / laser_control_mixin.py
├── project_io_mixin.py / job_queue_mixin.py
├── png2svg_mixin.py / png2svg_widget.py / converter.py
├── separation_mixin.py / separation_engine.py
├── requirements-linux.txt / requirements-windows.txt
├── build.bat / setup.iss / BUILD.md
├── ARCHITECTURE.md / CHANGELOG.md / README.md / LICENSE
└── ressources graphiques (.ico, .png, banner…)
```

---

## 3. Rôles détaillés par fichier

### 3.1 Point d’entrée & infrastructure

| Fichier | Rôle | Liens principaux |
|---------|------|------------------|
| **main.py** | Lance l’app (ou Stencil Studio si `--stencil-studio`). Installe Breeze, applique le thème, splash, icône fenêtre. | → `app_theme`, `main_window.FullLaserStudio`, `app_utils`, `ui.splashscreen` |
| **app_theme.py** | Définition des thèmes **dark / light / dusk / warm** (palette Qt + stylesheet généré). `apply_app_theme()`, `available_themes()`. | `main.py`, `ui_window_controller.change_theme` |
| **app_utils.py** | Version (`APP_VERSION`), chemins ressources (`find_resource`), écriture atomique, autosave, background writer | Utilisé largement |
| **debug_log.py** | Logging debug / résumés G-Code | `laser_control_mixin`, `job_queue_mixin` |
| **qt_messages.py** | Filtre warnings Qt (Wayland…) | `main.py` |
| **i18n.py** | Traductions FR / EN / DE / ES (y compris thèmes, nœuds, explode, outils dessin) | Toute l’UI |
| **simulated_grbl.py** | Port GRBL simulé | `laser_control_mixin` |

### 3.2 Fenêtre principale = assemblage de mixins

| Mixin / fichier | Rôle | Dépend de / appelle |
|-----------------|------|---------------------|
| **main_window.py** | `FullLaserStudio` : mixins + USB + `LayerManager` + timers. Construit la fenêtre (`init_ui` appelle les `_build_*`), crée `MachinePanel` et l'abonne à la logique (`_build_machine_panel`), fermeture, drag&drop, affichage du panneau machine et tailles du séparateur, plein écran d'un onglet, fenêtres de réglages | Tous les mixins, `ui/machine`, `ui/statusbar`, `settings_window` |
| **ui_setup_mixin.py** | Contenu des onglets : éditeur vectoriel (boutons dessin / mesure / explode / nœuds), barre d'outils d'onglet (`_build_tab_toolbar`), actions de la barre d'outils sur l'image. Partira dans `ui/tabs/` | `vector_layers` |
| **ui/app/menu/** | `AppActions` crée toutes les actions (icône, libellé, raccourci, état) et émet les signaux (`save_project_requested`, `mirror_changed`…). `AppMenuBar` et un fichier par `QMenu` (Fichier, Paramètres, Outils, Aide), `AppToolBar` (mêmes actions + ports, « Générer » et, à droite, le bouton ko-fi) ne font que les ranger | `ui/buy_me_a_coffee` |
| **ui_window_controller.py** | Contrôleur de la fenêtre : abonne la fenêtre aux signaux de `AppActions`, `change_theme`, langue, `update_connection_widgets`, ouverture Stencil Studio | `app_theme`, `ui/app/menu`, `stencil_studio.studio_dialog` |
| **ui_image_tab.py** | Onglet « Graver une image » : réglages, taille + offset, aperçus originale / tramé côte à côte | `graphics_view` |
| **ui/machine/** | `MachinePanel` : assemble sous les onglets la rangée position du job / pilotage / actions de job / DRO, la barre de progression du job et la console directe. Pas de signaux à lui : la fenêtre s'abonne à ceux de ses sous-panneaux ; `set_connected()` verrouille les commandes | Construit et abonné dans `main_window._build_machine_panel` |
| **ui/machine/controls/** | `JogControlPanel` : jog, homing, pas, vitesse, commandes temps réel, envoi du job. Émet des signaux (`jog_requested`…), sans logique machine | Abonné : `LaserControlMixin` (via `main_window._build_machine_panel`) |
| **ui/machine/job_actions/** | `JobActionsPanel` : cadrage, zéro, aller au zéro, répétition. Émet des signaux, construit depuis une liste d'actions (futures macros) | Abonné : `LaserControlMixin` (via `main_window._build_machine_panel`) |
| **ui/machine/dro/** | `DroPanel` : état GRBL coloré, position X / Y / Z, « Déverrouiller » visible seulement en alarme. Reçoit l'état par `set_status()`, émet `unlock_requested` | Alimenté par `LaserControlMixin._update_dro_display` |
| **ui/machine/console/** | `DirectConsolePanel` : champ de commande GRBL avec historique (flèches) et bouton « Envoyer ». Émet `command_submitted(commande)` | Abonné : `LaserControlMixin.send_manual_cmd` |
| **ui/tabs/layers/** | `LayersTab` : page de l'onglet « Calques ». Enveloppe `LayerManagerWidget` (encore dans `vector_layers.py`), relaie `layers_changed`, `refresh()`, `link_all_to_focal()`… | Construit et abonné dans `main_window._build_layers_tab` ; lu par Stencil Studio (`lsp_bridge`) |
| **machine_profiles_mixin.py** | Profils machine, matériaux, réglages calques mémorisés | `vector_layers.LAYER_MODES` |
| **image_processing_mixin.py** | Image, filtres, matière, undo image | `workers`, `image_filters`, `image_size` |
| **vector_editing_mixin.py** | Import SVG/DXF, outils dessin (`set_vector_draw_tool`), alignement, nesting, boîtes | `vector_layers`, `vector_import`, `dxf_import`, `nesting_*` |
| **gcode_generation_mixin.py** | Génération G-Code image + vectoriel, aperçu 2D | `workers`, `vector_layers` |
| **laser_control_mixin.py** | USB/série, stream, status, homing, urgences | `usb_controller`, `workers` |
| **project_io_mixin.py** | Projets + autosave | `app_utils` |
| **job_queue_mixin.py** | File d’attente G-Code | `workers.GCodeStreamerThread` |
| **png2svg_mixin.py** / **separation_mixin.py** | PNG→SVG et séparation couleur | widgets / engines dédiés |

### 3.3 Vectoriel (cœur édition)

| Fichier | Rôle | Utilisé par |
|---------|------|-------------|
| **vector_layers.py** | Calques (`LayerManager`), objets (`TextObject`, `ShapeObject`, `SvgPathObject`), **`VectorCanvasView`** | Éditeur, G-Code, profils |
| **vector_import.py** / **dxf_import.py** | Import SVG/DXF (groupé par défaut) | `vector_editing_mixin` |
| **vector_order.py** / **vector_nudge.py** / **vector_font.py** | Ordre de coupe, nudge clavier, polices | Éditeur |

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
| **app_theme.py** | 4 thèmes : `dark`, `light`, `dusk` (gris-bleu), `warm` (gris chaud ambré) |
| Menu **Paramètres → Thème** | `available_themes()` + `change_theme()` ; persistance `QSettings("app_theme")` |
| **icons/breeze/** | Pack minimal Breeze (LGPL-3) ; activé par `install_breeze_icon_theme()` si pas de thème système |
| **build.bat / BUILD.md** | `--add-data "icons;icons"` pour embarquer le pack |

### 3.5 Stencil Studio

| Fichier | Rôle |
|---------|------|
| **studio_dialog.py** | Fenêtre QtWebEngine intégrée ; `theme_for_lsp()` mappe dark/light/dusk/warm ; `sync_theme_from_lsp()` à chaud |
| **lsp_bridge.py** | Intercepte exports SVG/DXF → import dans l’éditeur vectoriel |
| **studio.py** | Serveur HTTP local + logique de conversion |

Thèmes Studio (`LSP_THEME_*`) alignés sur les palettes LSP.

### 3.6 Image, machine, build

Inchangé dans l’esprit : `workers.py` (threads), `usb_controller.py`, `settings_window.py`, scripts `build.bat` / `macos/` / `setup.iss`. Voir CHANGELOG pour le détail des versions.

---

## 4. Schéma des dépendances principales

```
main.py
  ├─ app_theme.apply_app_theme
  ├─ icons/breeze  (QIcon theme)
  └─ FullLaserStudio
        ├─ WindowControllerMixin ──► menu thème ──► change_theme ──► app_theme
        │                 └─► open_stencil_studio ──► studio_dialog
        │                        (theme_for_lsp / sync_theme_from_lsp)
        ├─ VectorEditingMixin ──► VectorCanvasView (vector_layers)
        │         ├─ import SVG/DXF (groupé)
        │         ├─ set_vector_draw_tool (line/rect/ellipse)
        │         ├─ explode_selected / enter_node_edit
        │         └─ nesting / box_generator
        ├─ GcodeGenerationMixin ──► workers + vector_layers G-Code
        └─ LaserControlMixin ──► usb_controller / simulated_grbl
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
4. **Thème unique source de vérité** : `app_theme.THEMES` + `QSettings("app_theme")` ; Stencil Studio consomme via `theme_for_lsp`.
5. **Undo canevas** : toute mutation géométrique (nœuds, explode, dessin) doit appeler `push_undo_snapshot()` avant modification.
6. **i18n** : toute nouvelle chaîne UI passe par `tr("…")` dans `i18n.py`.
7. **Ressources** : images/icônes via `find_resource` / pack `icons/` ; penser à `--add-data` dans les builds.

---

## 7. Évolutions récentes (mémo)

| Domaine | Ajout |
|---------|--------|
| Thèmes | `dark`, `light`, **`dusk`**, **`warm`** (`app_theme.py`) |
| Icônes | Pack **Breeze** embarqué (`icons/breeze`) |
| Import | Plus de dégroupage automatique SVG/DXF |
| Dessin | Outils souris ligne / rectangle / ellipse |
| Édition | **Exploser en segments** + **mode nœuds** |
| Stencil Studio | Thème lié à LSP (4 thèmes, sync à chaud) |
| UI claire | Stylesheet dédié (boutons ±, spinbox, etc.) |

---

## 8. Commandes utiles

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
python -m py_compile main.py app_theme.py vector_layers.py ui_setup_mixin.py ui_window_controller.py ui_image_tab.py
```

---

*Document d’architecture — à tenir à jour lors des changements structurants (nouveaux mixins, flux d’import, thèmes, pont Stencil Studio).*
