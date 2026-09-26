# Laser Studio Pro

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jb3dlaser)

Laser Studio Pro est un logiciel de pilotage GRBL pour graveur et découpeuse laser, avec :
- gravure d’images,
- découpe/gravure vectorielle,
- gestion de calques,
- génération de G-Code,
- export/import de projets,
- support multilingue (Français, English, Deutsch, Español).

## Lancer l’application

Lancez `main.py` depuis le dossier du projet.

```bash
python main.py
```

## Structure du projet

### Point d’entrée
- `main.py` — lance l’application
- `app_utils.py` — version de l’application et chemins de ressources

### Composants autonomes
- `graphics_view.py` — `ZoomableGraphicsView`
- `vector_font.py` — `VectorFont`
- `usb_controller.py` — `LaserUSBController`
- `workers.py` — threads et fonctions de traitement image / G-Code
- `i18n.py` — système de traduction multilingue

### Fenêtre principale découpée en mixins
- `main_window.py` — assemblage de la fenêtre principale
- `ui_setup_mixin.py` — interface utilisateur, menus, onglets, dialogues
- `machine_profiles_mixin.py` — profils machine / matériaux
- `image_processing_mixin.py` — chargement et traitement d’image
- `vector_editing_mixin.py` — éditeur vectoriel et SVG
- `gcode_generation_mixin.py` — génération, aperçu et export G-Code
- `laser_control_mixin.py` — USB / GRBL / commandes temps réel
- `project_io_mixin.py` — sauvegarde et ouverture de projet

<img width="1907" height="1005" alt="Tramage" src="https://github.com/user-attachments/assets/42ae3b7c-7740-4c4c-a704-d3b78d4d36ab" />

<img width="1919" height="1035" alt="Apercu tramages" src="https://github.com/user-attachments/assets/320160f2-a7c1-47b1-9626-cc1c96f9ae1d" />

<img width="3258" height="1830" alt="655698064-05eeca85-b211-4a80-817a-aea536a2c92c" src="https://github.com/user-attachments/assets/e6796d7b-6238-44d2-b888-1afc7ba696b0" />

## Fonctionnalités récentes

## [V2.0.0]

feat: Éditeur Vectoriel (redo/alignement/accroche), file d'attente persistante, GRBL complet, matériaux par machine, JPEG (v2.0.0)

## Ajouté :
- Éditeur Vectoriel : vrai Refaire (Ctrl+Y), alignement multi-objets
  (gauche/centre/droite, haut/milieu/bas) et distribution avec espacement
  égal (dès 3 objets, extrémités fixes), accroche à la grille pendant un
  déplacement (pas réglable en mm, préserve l'agencement relatif d'une
  sélection multiple en n'accrochant que l'objet réellement cliqué).
- File d'attente : réordonnancement des jobs par glisser-déposer, et
  persistance complète entre deux sessions (sauvegardée à chaque
  modification, restaurée au démarrage).
- Profils machine : import/export complet des réglages GRBL ($$) —
  lecture depuis la machine, envoi (avec confirmation, écrit en EEPROM),
  export/import en fichier texte ; capturés automatiquement par "Nouvelle
  Machine"/"Mettre à jour" comme le reste du profil.
- Base de matériaux (`materials_db`) propre à chaque profil machine —
  une nouvelle machine hérite de la liste active à sa création,
  personnalisable ensuite sans affecter les autres profils.
- Onglet PNG/JPEG → SVG (renommé) : accepte maintenant le JPEG en plus
  du PNG (le pipeline de conversion le gérait déjà nativement), glisser-
  déposer direct d'un fichier, et collage presse-papiers (Ctrl+V,
  pratique pour une capture d'écran).
- app_utils.py : nouvelle fonction get_autosave_dir() — dossier
  utilisateur toujours accessible en écriture (~/.local/share sous
  Linux, %APPDATA% sous Windows) pour l'autosave de projet et la file
  d'attente, plutôt que le dossier de l'exécutable (pouvait être en
  lecture seule une fois installé).

## Corrigé :
- Plantage au lancement (ImportError: get_autosave_dir) sur une
  installation où project_io_mixin.py avait déjà été mis à jour pour
  utiliser ce nouveau dossier utilisateur, sans que la fonction existe
  encore côté app_utils.py.

Fichiers modifiés :
app_utils.py, vector_layers.py, vector_editing_mixin.py, ui_setup_mixin.py,
i18n.py, job_queue_mixin.py, main_window.py, laser_control_mixin.py,
machine_profiles_mixin.py, png2svg_widget.py, project_io_mixin.py

feat: liaison focale automatique (Image Filtres + calques), correctifs plein écran (v1.7.0)

## Ajouté :
- Puissance minimum réglable dans la matrice de test (le champ existait
  déjà côté génération, il manquait juste sa ligne dans le formulaire) ;
  libellé dynamique "Puissance Min (%)" / "Puissance Unique (%)" selon le
  mode, traduit FR/EN/DE/ES.
- Liaison focale automatique par calque (onglet Calques) : bouton 🔗/🎯
  par calque pour lier son "Pas remplissage (mm)" à la taille du spot
  laser réglée dans Paramètres Machine, avec mise à jour immédiate à
  chaque changement de focale et pastille de qualité colorée (même
  logique que l'onglet Image & Filtres).
- Cases "Aperçu en négatif" et "Masquer les déplacements rapides G0"
  cochées par défaut, pour une meilleure lisibilité de l'aperçu 2D dès
  l'ouverture d'un projet.

## Corrigé :
- Focale (Paramètres Machine) : Lignes/mm, DPI et la pastille de qualité
  d'Image & Filtres se recalculent désormais systématiquement à chaque
  changement de focale, quel que soit le mode de résolution actif (avant :
  uniquement en mode "Focale laser", laissant Lignes/mm et DPI obsolètes
  dans les deux autres modes).
- Changement de profil machine (liste déroulante) : force maintenant le
  même rafraîchissement (Image Filtres + pastilles de qualité des
  calques), qui ne se déclenchait pas si la nouvelle focale coïncidait
  avec l'ancienne ou était absente d'un profil ancien format.
- Liaison focale par calque (`link_all_to_focal`) : posait le drapeau
  "lié" (icône verte) sans jamais appliquer la valeur de la focale au
  pas de remplissage, qui restait bloqué à 0.10 mm (valeur par défaut de
  la classe) tant qu'aucun changement de focale en direct n'avait eu
  lieu — lien vert trompeur ne correspondant pas à la focale réelle.
- Plein écran "Images / Tramage" : superposition visuelle du panneau de
  réglages par-dessus l'onglet réellement actif à la fermeture (forçage
  de visibilité en trop) ; l'onglet de réglages actif avant le plein
  écran est maintenant correctement restauré.
- Aperçu image (tramage) : régression de lenteur introduite par un cache
  de rendu (`CacheMode.DeviceCoordinateCache`) mal adapté à un contenu
  qui change en permanence — retiré, gardant uniquement le correctif de
  repaint au redimensionnement.
- Éditeur de calques : libellé "Puissance Unique (%)" de la matrice de
  test qui restait codé en dur en français.
- Windows : sur certains systèmes, le texte d'aide de l'onglet
  "Paramètres Machine" pouvait dépasser l'espace disponible (police
  système par défaut plus haute qu'en test), bloquant le glisseur des
  séparateurs gauche et centre/droite sans marge pour redimensionner.
  Cet onglet est maintenant défilant, et une hauteur minimale explicite
  a été posée sur les panneaux des deux séparateurs verticaux.

## Fichiers modifiés :
app_utils.py, ui_setup_mixin.py, image_processing_mixin.py,
machine_profiles_mixin.py, vector_layers.py, graphics_view.py, i18n.py

## [1.6.0]

feat: DRO temps réel, plein écran étendu, corrections rendu 2D (v1.6.0)

### Ajouté :
- Plein écran pour les onglets Images/Tramage, Visualisation 2D G-Code et
  Console/G-Code (même principe que l'Éditeur Vectoriel et PNG -> SVG).
- Plein écran Images/Tramage : panneau de réglages du tramage affiché à
  côté des aperçus, pour un retour en direct sans sortir du plein écran.
- DRO (position machine en temps réel) : état GRBL (Idle/Run/Hold/Alarm)
  et position X/Y/Z en direct, en jog comme en cours de job.
- Marqueur de position en direct sur l'aperçu 2D G-Code pendant le
  streaming.

### Corrigé :
- Éditeur Vectoriel : 3 messages restaient codés en dur en français au
  lieu de suivre la langue choisie.
- Aperçu 2D G-Code : les déplacements G1 à puissance nulle étaient
  affichés dans la couleur de la gravure réelle, rendant les deux
  indiscernables (visible entre les carrés de la matrice de test) ;
  affichés maintenant en gris pointillé, comme les G0.
- Couleur par défaut de la matrice de test / G-code importé : vert plus
  lumineux et contrasté (#00ff88 au lieu de #00cc66).
- Démarrage : la demande de restauration de sauvegarde automatique
  s'affichait avant que la fenêtre soit visible ; différée jusqu'à
  l'affichage réel de la fenêtre (évite un dialogue invisible bloqué en
  arrière-plan).

Fichiers modifiés :
usb_controller.py, workers.py, laser_control_mixin.py, job_queue_mixin.py,
gcode_generation_mixin.py, ui_setup_mixin.py, i18n.py, main_window.py,
vector_editing_mixin.py, app_utils.py

## [1.5.0]

### Ajouté
- **Utilitaire de conversion PNG vers SVG (Vectorisation)** :
  - Outil intégré permettant de transformer directement des images matricielles (PNG) en tracés vectoriels SVG.
  - Réglages fins de vectorisation : ajustement du seuil de tolérance (Noir/Blanc), simplification et lissage des contours, et filtrage du bruit.
  - Aperçu instantané du rendu vectoriel avant insertion dans le projet de découpe ou gravure.

<img width="1511" height="641" alt="Test svg" src="https://github.com/user-attachments/assets/0a68799f-e198-4044-b051-a263d4755464" />


## 🚀 Release v1.4.1

### ✨ Améliorations & Ergonomie

Positionnement dynamique à la souris : Possibilité de sélectionner et de déplacer l'intégralité d'un fichier SVG directement sur le plan de travail.
Ajustement de précision (Offset X / Y) : Ajout des contrôles de décalage X et Y pour affiner la position exacte de vos éléments vectoriels au millimètre près.
Cette version apporte plus de souplesse dans la manipulation des calques vectoriels et accélère la préparation de vos projets.

<img width="340" height="357" alt="Déplacement" src="https://github.com/user-attachments/assets/01d1e7df-ed98-4724-8aee-4857904e19cc" />


## [1.4.0]
Ajouté
Traduction quasi complète de l'application (Français, Anglais, Allemand, Espagnol) : quasiment toutes les boîtes de dialogue, messages d'erreur/confirmation et libellés de boutons de l'ensemble des onglets utilisent désormais le système i18n.py — 319 chaînes traduites au total, vérifiées une à une contre le dictionnaire (aucune clé manquante).
Corrigé

<img width="1918" height="1010" alt="English" src="https://github.com/user-attachments/assets/eaa4c939-b36d-4588-8538-12aa54dc01ea" />

<img width="1910" height="1008" alt="Allemand" src="https://github.com/user-attachments/assets/20f4c90a-8f35-44aa-b372-c88be354859c" />


## 1.3.1 + : corrections du rendu 2D pour les calques vectoriels/texte/SVG (voir détails ci-dessous) et adresse e-mail Support mise à jours.
Coquille QQMessageBox (au lieu de QMessageBox) dans laser_control_mixin.py, qui aurait fait planter l'appli au clic sur "Connecter" sans port COM sélectionné.
UnboundLocalError au démarrage : legacy_svg_box était utilisé avant sa création dans ui_setup_mixin.py (ordre des blocs corrigé).
Rendu 2D des calques vectoriels/texte/SVG : plusieurs calques classés à tort comme "balayage raster" étaient fusionnés dans une seule image, produisant un rendu incohérent. Chaque calque raster est maintenant reconstruit séparément, teinté avec sa propre couleur.

### 1.3.1
- finalisation du support multilingue sur les libellés restants de l’interface,
- traduction des onglets, panneaux, matrices de test, dialogues, messages GRBL,
- localisation des éléments de la console et du système d’édition vectorielle,
- texte de support et bouton “Buy me a coffee” maintenant traduits,
- amélioration de la cohérence de l’interface entre les langues supportées.

## Développement / validation

Pour vérifier la syntaxe Python :

```bash
py -m py_compile i18n.py ui_setup_mixin.py main_window.py
```

## Remerciements

Merci à toutes les personnes qui contribuent au projet, testent les fonctionnalités et signalent les bugs.

## Licence

Voir le fichier `LICENSE` associé au dépôt si présent.
