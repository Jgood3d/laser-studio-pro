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

### Point d’entrée
- `main.py` — lance l’application
- `app_utils.py` — version de l’application, chemins de ressources, écriture atomique des fichiers de données
- `app_constants.py` — valeurs fixes de l’application (liens, adresses)

### Composants autonomes
- `graphics_view.py` — `ZoomableGraphicsView`
- `vector_font.py` — `VectorFont`
- `vector_layers.py` — calques et objets vectoriels, canevas de l’éditeur
- `usb_controller.py` — `LaserUSBController`
- `workers.py` — threads et fonctions de traitement image / G-Code
- `widgets_extra.py` — petits widgets réutilisables (historique de commandes, libellé à masquage automatique)
- `ui_utils.py` — utilitaires partagés par les éléments d’interface (icônes dessinées)
- `ui/splashscreen/` — `StartupSplash`, écran de démarrage (affichage réel sous Wayland, durée minimale)
- `qt_messages.py` — filtre des avertissements de Qt sans conséquence (Wayland)
- `separation_engine.py` — calculs de séparation couleur / verre (sans Qt)
- `image_filters.py` — filtres d’image purs (netteté)
- `vector_order.py` — ordre de découpe sûr (gravure avant découpe, intérieur avant extérieur)
- `nesting.py` — imbrication automatique des pièces sur une feuille (sans Qt)
- `image_size.py` — taille d’origine d’une image d’après sa résolution (sans Qt)
- `vector_nudge.py` — pas de déplacement aux flèches du clavier (sans Qt)
- `dxf_import.py` — lecteur DXF texte (sans Qt, sans dépendance)
- `box_generator.py` — calcul des panneaux d’une boîte à encoches (sans Qt)
- `vector_import.py` — passerelle vers les objets de l’éditeur vectoriel (DXF, boîte, décor)
- `png2svg_widget.py` — widget de conversion PNG/JPEG → SVG (utilise le module `converter`)
- `i18n.py` — système de traduction multilingue

### Fenêtre principale découpée en mixins
- `main_window.py` — assemblage de la fenêtre principale
- `ui_setup_mixin.py` — assemblage de l’interface (`init_ui`), outils communs aux onglets, fermeture de la fenêtre
- `ui_machine_params_page.py` — page « Paramètres du graveur »
- `ui_machine_profiles_page.py` — page « Matériaux et connexion au graveur »
- `ui_test_matrix_page.py` — page « Matrice de test »
- `ui_grbl_config_page.py` — page « Configuration GRBL »
- `ui_image_tab.py` — onglet « Graver une image » et position du job
- `ui_preview_2d_tab.py` — onglet d’aperçu 2D du G-Code
- `ui_job_tabs.py` — onglets Console / G-Code et File d’attente
- `ui_machine_panel.py` — panneau machine sous les onglets (DRO, jog, console directe)
- `ui/statusbar/` — barre d’état (`StatusBar` : messages d’information, progression de la génération)
- `ui_legacy_svg_box.py` — ancien mode SVG, conservé pour compatibilité
- `ui_menus.py` — barre de menus, barre d’outils principale, thème, état de la connexion
- `ui/about/` — boîte « À propos » (`AboutDialog`, `AboutBannerPixmap`, `AboutLabel`)
- `ui/support/` — boîte « Support » (`SupportDialog`, `SupportLabel`)
- `ui/buy_me_a_coffee/` — boîte « Buy me a coffee » (`BuyMeACoffeeDialog`, `BuyMeACoffeeLabel`)
- `ui/machine/controls/` — panneau de pilotage `JogControlPanel` : jog, homing, curseurs de pas et de vitesse, commandes temps réel, envoi du job (émet des signaux)
- `ui/machine/job_actions/` — panneau `JobActionsPanel` : cadrage, zéro, aller au zéro, répétition (émet des signaux ; accueillera les macros)
- `machine_profiles_mixin.py` — profils machine / matériaux / réglages de calques par machine
- `image_processing_mixin.py` — chargement et traitement d’image, matière
- `vector_editing_mixin.py` — éditeur vectoriel et SVG
- `gcode_generation_mixin.py` — génération, aperçu et export G-Code
- `laser_control_mixin.py` — USB / GRBL / commandes temps réel
- `project_io_mixin.py` — sauvegarde et ouverture de projet, sauvegarde automatique
- `job_queue_mixin.py` — file d’attente de jobs
- `png2svg_mixin.py` — onglet PNG/JPEG → SVG
- `separation_mixin.py` — onglet Séparation Couleur / Verre
- `box_dialog.py` — fenêtre du générateur de boîte
- `nesting_apply.py`, `nesting_dialog.py` — imbrication dans l’éditeur vectoriel (passerelle et fenêtre de réglage)
- `settings_window.py` — fenêtres « Paramètres du graveur », « Matériaux et connexion au graveur » et « Configuration GRBL » ouvertes depuis le menu Paramètres

### Qualité
- `tests/` — tests automatiques (G-Code, fin de job, calibrage, séparation couleur/verre, sauvegardes, reset/référencement, calques par machine, traductions)
- `tools/check_translations.py` — rapport sur les traductions (clés inutilisées, textes en dur, registre tu/vous)
- `tools/check_ui_attributes.py` — détecte les widgets utilisés mais jamais construits (fichier resté à l’ancienne version)

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

Vérifier qu’aucun widget n’est utilisé sans être construit (utile après avoir remplacé plusieurs fichiers) :

```bash
python tools/check_ui_attributes.py
```

Contrôler les traductions (rapport détaillé) :

```bash
python tools/check_translations.py
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
