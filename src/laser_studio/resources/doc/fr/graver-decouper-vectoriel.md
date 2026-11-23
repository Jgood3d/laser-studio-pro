# Comment graver ou découper avec une image vectorielle

[‹ Retour au sommaire](index.md)

L'onglet **Graver une image vectorielle** est l'éditeur vectoriel. C'est
là que l'on prépare tout travail qui mélange **gravure, marquage et
découpe** : une pièce découpée avec un décor gravé, un texte marqué sur
une forme, plusieurs objets sur la même plaque…

Si la notion de vecteur ne vous est pas familière, commencez par la page
[Images vectorielles](images-vectorielles.md).

## Le principe : un calque par élément

Chaque élément du dessin est rangé sur un **calque**, et c'est le calque
qui décide de ce que fait le laser : graver, marquer ou découper. Vous
pouvez donc appliquer un calque différent :

- à **un seul élément** (un cercle, une lettre, un trait) ;
- à **un groupe d'éléments** (tout un logo, toutes les découpes
  intérieures) ;
- à **tout le dessin**.

C'est ce qui permet de graver, marquer ou découper **tout ou partie**
d'une image vectorielle. Une forme apparaît dans la couleur de son calque :
vous voyez d'un coup d'œil ce qui sera gravé, marqué ou découpé.

## Importer un dessin

**Importer SVG / DXF** (ou glisser-déposer le fichier sur l'éditeur). Le
dessin arrive :

- **groupé** : on le déplace et on le redimensionne d'un bloc ;
- sur le **premier calque de découpe**.

Pour donner des calques différents à ses parties, **dégroupez-le** :
clic droit › **Dégrouper**. Chaque tracé devient un objet séparé.

## Assigner un calque

1. Sélectionnez un ou plusieurs objets : clic, puis **Maj + clic** pour en
   ajouter, ou tracez un cadre autour.
2. Choisissez le calque dans la liste **Calque** du panneau des
   propriétés, ou faites clic droit › **Assigner au calque**.

Pour traiter plusieurs objets comme un seul, sélectionnez-les puis clic
droit › **Regrouper en un seul objet**.

## Les outils de l'éditeur

**Ajouter et dessiner**

- **+ Texte** : un texte modifiable (police, gras, italique, taille,
  espacement des lettres), droit ou courbé sur un cercle.
- **+ Forme** : rectangle, ellipse, ligne ou polygone régulier.
- Outils de tracé : **Ligne**, **Rectangle**, **Ellipse**, **Cercle**, au
  clic-glisser sur le canevas (Échap pour annuler).
- **Mesure** : mesurer une distance sur le canevas.
- **Bibliothèque** et générateurs (boîte, puzzle, boule de Noël,
  porte-clés) : voir [Les outils](outils.md).

**Modifier**

- Panneau des propriétés : position **X / Y**, **Largeur**, **Hauteur**,
  **Rotation**, et **Ancrage** (le coin qui reste en place quand la taille
  change).
- **Pivoter 90°**, **Dupliquer**, **Supprimer**, **Tout supprimer**.
- **Annuler** (Ctrl+Z) et **Refaire** (Ctrl+Y).
- **Zoom avant** (Ctrl++) et **Zoom arrière** (Ctrl+-) : les loupes au bout
  de la barre d'édition, ou la molette de la souris.
- Clic droit › **Éditer les nœuds** pour déplacer les points d'un tracé,
  ou **Exploser en segments** pour le découper en morceaux.

**Organiser**

- **Alignement / Distribution** : aligner les objets à gauche, au centre,
  en haut…, ou les répartir à intervalles égaux.
- **Accroche à la grille** pour placer les objets au millimètre.
- **Imbrication auto**, **Dupliquer en série**, **Gabarit de placement**
  et **Texte le long d'un objet** : voir [Les outils](outils.md).
- **Plein écran** pour travailler plus confortablement.

## L'ordre de découpe

La case **Ordre de découpe sûr** (*Paramètres › Configuration GRBL*) fait
graver avant de découper, et découpe l'intérieur d'une pièce avant son
contour. Sinon, une pièce déjà détachée
peut bouger ou tomber, et la suite du travail serait décalée. Laissez-la
cochée.

## Quelques cas d'usage

**Un porte-clés en bois avec un prénom**
Le contour et le trou de l'anneau sur le calque **Découpe**, le prénom sur
le calque **Gravure**. La gravure est faite d'abord, puis la pièce est
découpée.

**Un sous-verre avec un logo**
Un cercle sur **Découpe**. Le logo importé, dégroupé : ses aplats sur
**Gravure**, son contour fin sur **Marquage**, pour souligner le dessin
sans creuser.

**Une boîte à assembler**
Le générateur de boîte place les faces sur **Découpe** et les numéros
d'assemblage sur **Gravure**. Une fois la boîte maîtrisée, désactivez la
gravure des numéros.

**Une série de prénoms**
Préparez un exemplaire (contour en **Découpe**, prénom en **Gravure**),
puis **Dupliquer en série** avec la liste des prénoms : un objet par
prénom, rangés sur la plaque.

**Repérer sans découper**
Pour vérifier une position avant de découper une matière chère, passez
temporairement le contour sur **Marquage** : le laser trace un trait léger
au lieu de traverser.
