# Les outils

[‹ Retour au sommaire](index.md)

Laser Studio Pro réunit des outils pour laisser libre cours à votre
créativité : vous choisissez quelques réglages, l'outil dessine la pièce et
l'envoie dans l'éditeur vectoriel, la découpe et la gravure déjà rangées
sur leurs calques. Vous pouvez ensuite la retoucher comme n'importe quel
dessin.

La plupart des outils se trouvent dans le menu **Outils**. Les outils de
mise en page s'ouvrent depuis l'éditeur vectoriel.

## Créer une pièce

### Bibliothèque de modèles

**Outils › Bibliothèque…**, ou le bouton *Bibliothèque* de l'éditeur
vectoriel. Des modèles prêts à graver, rangés par catégorie : médailles,
porte-clefs, totems, boules de Noël… Un double-clic ouvre la fiche du
modèle : choisissez ses options (forme, motif…), modifiez ses textes
(contenu, police, taille), l'aperçu suit vos choix. **Importer** le place
dans l'éditeur.

### Générateur de boîte

**Outils › Générateur de boîte…** Une boîte à encoches, dont les faces
s'emboîtent comme des doigts. Donnez les dimensions et l'épaisseur du
matériau, puis choisissez :

- le **couvercle** : aucun, à doigts, posé avec rebord, coulissant,
  charnière vivante (bois rendu souple par des fentes) ou charnière à axe ;
- des **cloisons** pour faire des compartiments ;
- des pieds, des aimants de fermeture, une encoche pour le doigt, un motif
  gravé sur le dessus, un numéro gravé sur chaque face pour l'assemblage.

Le **kerf** est la largeur de matière brûlée par le laser (souvent 0,1 à
0,2 mm) : l'outil en tient compte pour que les pièces s'emboîtent sans jeu.
Mesurez-le sur un essai. L'aperçu en 3D montre la boîte montée, ou ses
pièces écartées pour vérifier l'assemblage.

### Générateur de puzzle

**Outils › Générateur de puzzle…** Deux styles de découpe : le puzzle
classique, à tenons et mortaises, ou une grille ondulée. Choisissez la
taille et le nombre de pièces en largeur et en hauteur ; la forme des
tenons (profondeur, largeur du col, variations) se règle finement. Si une
image est chargée, le puzzle s'ajuste à sa taille : gravez l'image, puis
découpez le puzzle par-dessus.

### Boule de Noël

**Outils › Boule de Noël…** Une boule ajourée à suspendre au sapin, avec un
prénom et un motif : flocons, étoiles, sapins, Père Noël, bonhomme de
neige, cadeaux, houx, cloche, bougie… L'aperçu montre les contours
réellement découpés. Une barre relie le prénom à l'anneau pour qu'il ne
tombe pas à la découpe.

### Générateur de porte-clés

**Outils › Générateur de porte-clés…** Un prénom découpé sur une base qui
suit la forme des lettres, avec un anneau à gauche, à droite ou en haut.
Réglez la hauteur du texte, l'espacement des lettres et la bordure. Les
points isolés (i, accents) peuvent être reliés à la base.

## Mettre en page

Ces outils agissent sur les objets de l'éditeur vectoriel (clic droit sur
le dessin, ou barre d'outils de l'éditeur).

### Dupliquer en série

Reproduit la sélection en plusieurs exemplaires, rangés en grille ou
imbriqués automatiquement. Chaque exemplaire peut recevoir son propre
texte : saisissez une liste de prénoms, un par ligne, et vous obtenez un
porte-clés par prénom.

### Imbrication automatique

Le bouton **Imbrication auto** place les pièces au plus serré sur la
plaque, pour économiser la matière. Il tient compte de la forme réelle des
pièces : une petite pièce peut se loger dans le creux d'une grande. Réglez
la taille de la feuille, l'écart entre les pièces et les rotations
autorisées.

### Gabarit de placement

Découpe une plaque percée d'une poche par objet, à sa forme et à sa
taille, avec un peu de jeu. Posez-y vos porte-clés, stylos ou
décapsuleurs : ils seront toujours gravés au même endroit. Les poches sont
rangées comme les exemplaires de *Dupliquer en série*, pour que chaque
gravure tombe pile sur sa poche.

### Texte le long d'un objet

Clic droit sur un texte et une forme : **Courber le texte sur le tracé**
fait suivre au texte le contour de la forme, par exemple un cercle.

## Préparer les images

### Vectorisation d'image

L'onglet **Vectorisation d'image** transforme une image (logo, dessin au
trait) en dessin vectoriel, en noir et blanc ou en couleur, puis l'envoie
dans l'éditeur. Voir [Images vectorielles](images-vectorielles.md).

### Comparaison des algorithmes de tramage

Dans l'onglet *Graver une image*, ce bouton affiche une vignette de votre
image pour chaque algorithme de tramage, avec vos réglages actuels. Cliquez
sur la vignette qui vous plaît pour choisir cet algorithme.

### Séparation Couleur / Verre

L'onglet **Séparation Couleur / Verre** prépare une image en couleur sur
verre : la partie sombre est gravée sur le verre, la couleur est imprimée
sur un film transparent collé au dos. Une simulation montre le rendu
rétro-éclairé, et une grille de test aide à régler le gain de point.

## Régler la machine

### Matrice de test

**Outils › Matrice de Test** grave une grille de cases, chacune avec une
puissance et une vitesse différentes. Sur une chute de votre matériau,
elle montre d'un coup d'œil le bon réglage, que vous reportez ensuite dans
votre profil matériau. Le test peut aussi se faire à partir d'une image.

### Caméra

**Outils › Caméra…** Une caméra au-dessus du plateau affiche la plaque
dans l'éditeur vectoriel, pour placer le dessin exactement sur la pièce.
Deux assistants guident les réglages : la calibration de l'objectif (avec
un damier imprimé), puis l'alignement sur le plateau (avec des repères
gravés).

**L'alignement** utilise 4 repères (des AprilTags de 40 mm) aux coins du
plateau, imprimés sur une feuille ou gravés. Leur orientation n'a pas
d'importance. Le portique peut en cacher une partie : faites 2 à 3
captures en le déplaçant entre deux, l'assistant garde tous les repères
vus. Il indique la taille d'une case en pixels (6 px ou plus pour une
détection fiable). Indiquez aussi la **hauteur des repères** : 0 s'ils sont
imprimés sur une feuille à plat sur le plateau, l'épaisseur de la matière
s'ils sont gravés dessus. Les repères imprimés restent en place : on ne
refait pas l'alignement à chaque pièce.

**Fond caméra** : dans l'éditeur vectoriel, l'interrupteur « Fond caméra »
affiche l'image de la caméra sous la grille, et « Actualiser l'image
caméra » la recapture (après avoir posé ou déplacé la matière). Le
logiciel demande à chaque fois l'**épaisseur de la matière**, mesurée
depuis le plateau : le dessus d'une pièce épaisse est vu plus haut que les
repères et paraît décalé vers les bords de l'image, et cette correction
le remet à sa vraie place. Mettez 0 si la pièce est à plat sur le plateau.

### Historique des gravures

**Outils › Historique des gravures…** liste chaque job envoyé au graveur,
du plus récent au plus ancien : date, issue (terminée, arrêtée, erreur
GRBL), **durée réelle**, **durée estimée** et l'**écart** entre les deux,
distance gravée, nombre de lignes et machine. Le bas de la fenêtre donne le
total du temps de gravure.

**Exporter (CSV)…** ouvre l'historique dans un tableur, avec en plus la
vitesse et la puissance maximales, l'encombrement et les réglages de la
machine. L'historique reste sur l'ordinateur (fichier
`historique-gravures.jsonl` dans le dossier des données) ; **Vider
l'historique** l'efface.

### Les macros

Une macro envoie quelques lignes de G-code d'un clic : décaler la tête de
20 mm, revenir à l'origine machine, allumer un pointeur à faible
puissance… Ses boutons apparaissent sous les actions de job (cadrage, zéro,
répéter), à côté du jog.

**Outils › Macros…**, ou le bouton à droite des actions de job, ouvre
l'éditeur :

- **Ajouter**, **Dupliquer**, **Supprimer**, **Monter**, **Descendre** :
  la liste des macros, dans l'ordre des boutons ;
- **Nom** (le texte du bouton) et **Infobulle** ;
- **Demander confirmation avant l'envoi** ;
- **Profils machine** : les machines où la macro apparaît. Aucune case
  cochée : toutes les machines ;
- **G-code** : une commande par ligne. Les commentaires après « ; » sont
  retirés.

Une macro part seulement si le graveur est connecté, et jamais pendant
l'envoi d'un job. Si elle **allume le laser** (M3 ou M4 avec une puissance
S supérieure à 0), elle est marquée d'un ⚠ et une confirmation est toujours
demandée, avec **Non** par défaut.

Les macros sont enregistrées dans le fichier `macros.yaml`, dans le dossier
des données de Laser Studio Pro. **Exporter…** et **Importer…** permettent
de les partager. Le fichier se lit et se modifie aussi à la main :

```yaml
macros:
  - name: Décaler +20 X +10 Y
    tooltip: Déplace la tête, laser éteint
    gcode: |
      G91
      G0 X20 Y10
      G90
  - name: Pointeur 1 %
    machines: [Atomstack A5]
    gcode: |
      M3 S10
```

> **Attention** : en G91 (déplacements relatifs), pensez à revenir en G90
> à la fin de la macro, sinon le job suivant partirait de travers.

---

*Stencil Studio, l'atelier de pochoirs et d'effets lumineux, fait l'objet
d'une documentation séparée.*
