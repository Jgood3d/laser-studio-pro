# Changelog

Toutes les modifications notables du projet sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/) —
versionnage sémantique (`MAJEUR.MINEUR.CORRECTIF`).

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
