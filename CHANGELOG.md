# Changelog

Toutes les modifications notables du projet sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/) —
versionnage sémantique (`MAJEUR.MINEUR.CORRECTIF`).

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
