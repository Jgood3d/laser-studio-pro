# Changelog — Laser Studio Pro

Toutes les modifications notables du projet sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/) —
versionnage sémantique (`MAJEUR.MINEUR.CORRECTIF`).

## [2.2.0] — 2026-10-04

### Ajouté
- **Image / Filtres — sélecteur « Matière »** : liste placée juste au-dessus de « Inverser Couleurs ».
  « Fond noir » (aluminium anodisé, verre peint, ardoise, acrylique noir : le laser éclaircit ce qu'il brûle) active l'inversion ; « Fond clair » (bois, carton, cuir : le laser noircit ce qu'il brûle) la désactive.
  Le sélecteur ne fait que cocher/décocher « Inverser Couleurs » : la case reste modifiable à la main et le miroir reste indépendant.
  Le choix est enregistré dans le projet (un ancien projet le déduit de son inversion), pris en compte par Annuler/Rétablir, et remis sur « fond clair » par la réinitialisation des réglages image.
  L'alerte de confirmation avant gravure d'une image rappelle la matière, par exemple « Matière : fond noir (négatif activé) » ; elle reflète l'état réel de la case et signale donc une incohérence. Traduit en FR / EN / DE / ES.
- **Calques — réglages mémorisés par machine** : mode, puissance, vitesse, passes, pas de remplissage (et son lien à la focale) et état actif de chaque calque sont rangés dans le profil de la machine active.
  Enregistrement 0,6 s après chaque modification et à la fermeture (donc aussi après un plantage) ; restauration complète des calques au démarrage (noms, couleurs, calques ajoutés).
  En changeant de machine en cours de session, seuls les réglages de l'autre machine sont appliqués, aux calques existants (par identifiant puis par position) : aucun calque n'est ajouté, supprimé ni renommé, pour que les objets du canevas restent rattachés à leur calque. « Nouvelle machine » et « Mettre à jour » incluent les calques. Les anciens profils sans calques mémorisés ne changent rien.
- **Onglet « Séparation Couleur / Verre »** : à partir d'une image couleur, produit le calque noir à graver (tonalité envoyée à Image / Filtres, qui applique luminosité, contraste, gamma, tramage et résolution), le calque couleur à imprimer à la même taille physique, une simulation du rétro-éclairage, et un PDF A4 à l'échelle 1:1 avec repères de coin. Réglages : recadrage, gain de point, miroir à l'impression.
  À l'import, les réglages « verre » (matière fond noir, négatif, miroir horizontal) sont appliqués puis restitués au chargement d'une image classique.
- **Tests automatiques** (dossier `tests/`, `python -m unittest discover tests -v`) : génération du G-code d'image rejouée comme GRBL, écriture atomique, reset/référencement, mémorisation des calques par machine, contrôle des traductions.
- **Outil `tools/check_translations.py`** : rapport sur les clés jamais utilisées, les textes d'interface écrits en dur, les valeurs identiques entre langues et le mélange tutoiement/vouvoiement.

### Modifié
- **Éditeur vectoriel — vue** : la vue se cadre et se centre automatiquement sur le SVG importé (import SVG et PNG → SVG) ainsi qu'à l'entrée et à la sortie du plein écran. Le zoom s'ajuste à l'objet (plafonné pour les très petits objets).
- **Interface — panneau du bas** : le panneau Position machine / Jog / Commandes / Console GRBL n'est affiché que dans « Visualisation 2D G-Code », « Console / G-Code » et « File d'attente ». Il reste visible tant qu'un job est en cours, quel que soit l'onglet (Pause, Reset et Arrêt d'urgence toujours accessibles). Sa hauteur réglée est mémorisée.
- **RESET / ARRÊT D'URGENCE** : les deux boutons passent par une seule fonction commune.
- **Traductions** : message de fin de file d'attente et description de la fenêtre « À propos » désormais traduits ; deux clés définies en double dans `i18n.py` supprimées.

### Corrigé
- **Gravure d'image — puissance appliquée au mauvais segment** : à chaque changement de puissance, le G-code envoyait le déplacement jusqu'à la frontière avec la puissance du segment *suivant* (GRBL applique le `S` d'une ligne à son propre déplacement). Une ligne sur deux, les zones à conserver étaient gravées et celles à graver épargnées ; en balayage retour (droite → gauche), la frontière était en plus décalée d'un pixel (motif en peigne). Corrigé et couvert par un test qui rejoue le G-code.
- **Reset / Arrêt d'urgence en mouvement** : GRBL perd sa position lorsqu'il est réinitialisé alors que la machine bouge. Le statut « référencé » est maintenant retiré (un message l'indique dans la console) et un nouveau homing est demandé avant le job suivant. Un reset fait machine à l'arrêt ne change rien.
- **Sauvegardes** : l'autosave, la file d'attente et la sauvegarde manuelle du projet s'écrivent maintenant de façon atomique (fichier temporaire puis remplacement) ; un plantage, une coupure ou un disque plein en cours d'écriture ne laisse plus un fichier tronqué.
- **Chargement de projet** : l'état mémorisé par l'onglet Séparation est réinitialisé ; charger ensuite une image dans Images / Tramage ne remet plus à tort l'ancien négatif, miroir et matière par-dessus ceux du projet.
- **Homing (`$H`)** : la réponse n'est plus coupée au bout de 2 s pendant que la machine se déplace (délai porté à 90 s pour les commandes `$H…`).
- **File d'attente** : noms de jobs désormais uniques (deux jobs ajoutés dans la même seconde empêchaient de sauvegarder le nouvel ordre après un glisser-déposer) ; la barre de progression ne divise plus par zéro.
- **Console GRBL** : la flèche Bas n'efface plus ce que tu es en train de taper.
- **Interface** : un libellé à masquage automatique sans parent ne s'affiche plus comme une fenêtre isolée avant sa mise en page.
- **Aperçu 2D** : quand « Aperçu en négatif » est décoché, la gravure noire était illisible sur le fond sombre. Elle est maintenant simulée sur un fond clair (matériau), avec les découpes et contours toujours visibles par-dessus.

### Migration
- Aucun format n'est cassé : les projets, profils machine et files d'attente existants se chargent normalement (les clés ajoutées, `material_bg` et `layers`, ont une valeur de repli).
- Au premier lancement, les calques gardent leurs valeurs par défaut jusqu'à la première fermeture de l'application (les profils existants n'ont pas encore de calques mémorisés).
- Les G-codes d'image générés avec une version antérieure sont à régénérer (voir la correction de la puissance par segment).

Fichiers modifiés :
app_utils.py, workers.py, image_processing_mixin.py, ui_setup_mixin.py, project_io_mixin.py,
gcode_generation_mixin.py, laser_control_mixin.py, job_queue_mixin.py, machine_profiles_mixin.py,
usb_controller.py, widgets_extra.py, separation_mixin.py, i18n.py — nouveaux : tests/, tools/

## [2.1.0] — 2026-09-28

### Ajouté
- **Éditeur vectoriel — sélection multiple** : Ctrl + clic gauche ajoute un objet à la sélection (ou le retire s'il y est déjà). Le déplacement groupé fonctionne ensuite sur tout le groupe.
- **Éditeur vectoriel — regroupement** : clic droit → « Regrouper en un seul objet » (ou Ctrl+G) fusionne les objets sélectionnés en un seul tracé, à leur position exacte, déplaçable et redimensionnable d'un bloc. Annulable avec Ctrl+Z.
- **Calques — ordre modifiable** : boutons « ▲ Monter » / « ▼ Descendre ». L'ordre de la liste est l'ordre d'exécution des calques dans le G-Code (ex. gravure avant découpe).
- **Onglet Machine — aide aux drivers USB** : indication discrète avec liens officiels pour installer le driver du contrôleur (CH340, CP210x, FTDI) et rappel Linux (groupe `dialout`). Traduit en FR / EN / DE / ES.
- **Aperçu 2D — bouton de soutien** : petit bouton (logo) dans la barre d'outils, ouvre la page Ko-fi dans le navigateur. Nouvelle ressource `buy_me_a_coffee.png` à embarquer dans le build (`--add-data`).

### Modifié
- **Matrice de test (gravure)** : le champ « Lignes/mm » reprend automatiquement la valeur de l'onglet Image / Filtres (champ grisé, mise à jour en direct, quel que soit le mode de saisie : lignes/mm, DPI ou focale).
- **Image / Filtres** : la ligne « Écart : … » n'est plus affichée que pour signaler un réglage trop fin (< 0,9× la focale, risque de surgravure) ; masquée quand l'écart est correct ou recommandé.

### Corrigé
- **Matrice de test** : le champ « Puissance Min » (gravure) / « Puissance Unique » (découpe) existait mais n'était jamais affiché dans le formulaire.
- **Éditeur vectoriel** : Ctrl + clic n'ajoutait pas l'objet cliqué à la sélection existante.
- **Interface** : espace vide sous le bouton « Générer le G-Code » (les libellés de progression de génération se masquent maintenant quand ils sont vides ; même correction dans les deux autres onglets concernés).

### Build
- Ajouter `--add-data "buy_me_a_coffee.png;."` (Windows) / `--add-data "buy_me_a_coffee.png:."` (Linux) aux commandes PyInstaller.
- Supprimer `build/`, `dist/` et `LaserStudioPro.spec` avant de rebuilder, pour que le nouveau fichier de ressource soit bien pris en compte.

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

## [1.7.0] - 2026-09-21

## Ajouté

Puissance minimum réglable dans la matrice de test (le champ existait déjà côté génération, il manquait sa ligne dans le formulaire).
Liaison focale automatique par calque (onglet Calques) : bouton 🔗/🎯 par calque pour lier son pas de remplissage à la taille du spot laser, avec pastille de qualité colorée.
Notification sonore de fin de job (2 bips), en plus du message déjà affiché.
Bouton de déverrouillage GRBL ($X) apparaissant automatiquement en état Alarm, toujours avec confirmation avant envoi.
Cases "Aperçu en négatif" et "Masquer les déplacements rapides G0" cochées par défaut.

## Corrigé

Focale (Paramètres Machine) : Lignes/mm, DPI et pastille de qualité d'Image & Filtres se recalculent systématiquement, quel que soit le mode de résolution actif.
Changement de profil machine : force le même rafraîchissement, qui ne se déclenchait pas si la nouvelle focale coïncidait avec l'ancienne.
Liaison focale par calque : posait le drapeau "lié" sans jamais appliquer la valeur de la focale au pas de remplissage.
Plein écran "Images / Tramage" : superposition visuelle du panneau de réglages par-dessus l'onglet réellement actif à la fermeture.
Aperçu image : régression de lenteur due à un cache de rendu mal adapté à un contenu changeant en permanence.
Windows : texte d'aide de "Paramètres Machine" pouvant dépasser l'espace disponible et bloquer le glisseur des séparateurs.

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

## 🚀 Release v1.4.1

### ✨ Améliorations & Ergonomie

* **Positionnement dynamique à la souris :** Possibilité de sélectionner et de déplacer l'intégralité d'un fichier SVG directement sur le plan de travail.
* **Ajustement de précision (Offset X / Y) :** Ajout des contrôles de décalage X et Y pour affiner la position exacte de vos éléments vectoriels au millimètre près.

---
*Cette version apporte plus de souplesse dans la manipulation des calques vectoriels et accélère la préparation de vos projets.*

## [1.4.0]

### Ajouté
- **Traduction quasi complète de l'application** (Français, Anglais,
  Allemand, Espagnol) : quasiment toutes les boîtes de dialogue, messages
  d'erreur/confirmation et libellés de boutons de l'ensemble des onglets
  utilisent désormais le système `i18n.py` — 319 chaînes traduites au
  total, vérifiées une à une contre le dictionnaire (aucune clé manquante).

### Corrigé
- `1.3.1` : corrections du rendu 2D pour les calques vectoriels/texte/SVG
  (voir détails ci-dessous) et adresse e-mail Support mise à jour
  (`laserstudiopro.support@proton.me`).
- Coquille `QQMessageBox` (au lieu de `QMessageBox`) dans
  `laser_control_mixin.py`, qui aurait fait planter l'appli au clic sur
  "Connecter" sans port COM sélectionné.
- `UnboundLocalError` au démarrage : `legacy_svg_box` était utilisé avant
  sa création dans `ui_setup_mixin.py` (ordre des blocs corrigé).
- Rendu 2D des calques vectoriels/texte/SVG : plusieurs calques classés à
  tort comme "balayage raster" étaient fusionnés dans une seule image,
  produisant un rendu incohérent. Chaque calque raster est maintenant
  reconstruit séparément, teinté avec sa propre couleur.

## [1.3.0]

### Ajouté
- **Vérification du mode laser GRBL ($32)** à la connexion USB : avertit si
  ce réglage n'est pas activé (l'optimisation du G-Code en mode M4 suppose
  ce mode actif pour couper le laser pendant les déplacements rapides).
- **Sauvegarde automatique périodique** du projet en cours (toutes les
  5 minutes), avec proposition de récupération au démarrage suivant en cas
  de fermeture inattendue.
- **Historique des commandes manuelles** dans la console GRBL : flèches
  Haut/Bas pour rappeler les dernières commandes tapées.
- **Projets récents** : nouveau sous-menu dans Fichier pour rouvrir vite un
  projet déjà utilisé.
- **File d'attente de jobs** : empiler plusieurs G-Codes à envoyer au laser
  les uns après les autres, sans reconfigurer manuellement entre chaque.
- **Clic sur une case de la matrice de test** (aperçu 2D) : applique
  directement sa puissance/vitesse (ou nombre de passes) aux réglages de
  gravure/découpe courants.
- **Export/import des profils matériaux** en fichier `.json` séparé,
  partageable entre utilisateurs d'une machine similaire.

### Corrigé
- `load_project` utilisait par erreur la boîte de dialogue "Enregistrer"
  au lieu de "Ouvrir" pour choisir le fichier projet à charger.

## [1.2.0]

### Ajouté
- Début du support multilingue : nouveau menu **Langue** (entre Fichier
  et Aide) permettant de choisir Français ou English. Le changement
  s'applique au prochain démarrage de l'application.
- Nouveau module `i18n.py` : dictionnaire de traduction centralisé et
  fonction `tr()`, sans dépendance externe.
- Traduits pour l'instant : les menus Fichier/Langue/Aide et les 7 noms
  d'onglets du panneau de réglages. Le reste de l'interface (champs,
  boutons, messages) sera traduit progressivement dans les prochaines
  versions.

## [1.1.0]

### Ajouté
- Menu Aide → **Support** : contact par e-mail pour suggestions/problèmes.
- Menu Aide → **Buy me a coffee** : lien vers la page Ko-fi.
- Onglet **Image & Filtres** : valeurs numériques affichées en direct à
  côté des sliders Luminosité / Contraste / Gamma.
- Nouveau sélecteur **Résolution** (Lignes/mm, DPI, ou Focale laser) avec
  synchronisation automatique dans les deux sens entre les trois, plus
  un indicateur de qualité coloré comparant l'écart de lignes réglé à la
  focale du laser configurée.
- Nouveau champ **Taille du spot (focale)** dans Paramètres Machine,
  avec accès rapide depuis l'onglet Image et sauvegarde par profil.
- Bouton **"→ Enregistrer comme focale machine"** pour synchroniser un
  réglage Lignes/mm ou DPI choisi manuellement vers la focale machine
  (avec confirmation).
- Le mode de résolution, la valeur Lignes/mm et la valeur DPI sont
  désormais mémorisés d'une session à l'autre.

### Corrigé
- Bannière et icône introuvables une fois l'application compilée en
  exécutable (`.exe` / binaire Linux) : recherche désormais à la fois à
  côté de l'exécutable et dans le bundle PyInstaller.
- Zones transparentes d'un PNG importé gravées en noir au lieu d'être
  traitées comme du blanc (canal alpha mal géré à la conversion en
  niveaux de gris).
- Surbalayage (overscan) de la gravure d'image gravé à la puissance du
  premier pixel de la ligne au lieu d'une puissance nulle.
- G-Code de gravure allégé en mode laser dynamique (M4) : la commande de
  mode et l'arrêt laser n'étaient plus renvoyés à chaque ligne quand ce
  n'est pas nécessaire (le mode M3 reste inchangé, ligne par ligne).
- Matrice de test : étiquette "VITESSE" tracée à l'envers (bug
  d'orientation du texte vertical), lettres O/M/B/R/D manquantes dans la
  police vectorielle, position en X parfois négative des titres
  "VITESSE"/"PUISSANCE"/"NOMBRE DE PASSES", contour du carré regravé en
  double après le remplissage raster en mode Gravure.
- Arrondi des étiquettes de puissance/vitesse de la matrice de test :
  utilisation d'un arrondi arithmétique standard au lieu de l'arrondi
  bancaire de Python (ex: S625 affichait 62 % au lieu de 63 %).
- Aperçu d'un G-Code importé (ex: depuis LaserGRBL) : rendu en blocs de
  couleur pleins au lieu de l'image réelle, chevauchement/écrasement des
  motifs les uns sur les autres, effet de bandes horizontales, et aperçu
  illisible tant qu'on n'avait pas zoomé fortement.
- Résolution (Lignes/mm, DPI, Focale) pas toujours correctement
  synchronisée avec la focale machine à l'ouverture de l'application.
- Boîte "Buy me a coffee" affichant le code HTML brut au lieu du lien
  cliquable.

## [1.0.0]

### Ajouté
- Version initiale : découpage de `app.py` (fichier unique) en modules
  distincts (mixins par thème, workers, police vectorielle, calques
  vectoriels, etc.) pour faciliter la maintenance et le travail à
  plusieurs, sans changement de fonctionnalité.
