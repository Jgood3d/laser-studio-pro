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


## Fonctionnalités récentes

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
