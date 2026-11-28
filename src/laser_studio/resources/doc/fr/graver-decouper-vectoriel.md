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

**Importer SVG / DXF** (ou glisser-déposer le fichier sur l'éditeur). Un
SVG arrive tel que votre logiciel de dessin (Inkscape, Illustrator…) le
montre :

- **ses calques et groupes sont gardés** : chacun devient un groupe de la
  liste des objets, avec son nom ;
- **chaque objet va sur un calque d'après sa couleur** : noir ou gris foncé
  sur la **gravure**, rouge sur la **découpe**, vert sur le **marquage**
  (les teintes proches comptent aussi) ; une autre couleur va sur le premier
  calque de découpe ;
- **le blanc n'est pas une couleur de laser** : un objet blanc arrive sur
  le calque **Ignoré**, rien n'est gravé. Pour évider une forme (un texte
  blanc sur un bandeau noir, par exemple), choisissez l'objet blanc dans la
  liste, donnez-lui un calque, puis groupez-le avec la forme en
  **Différence** ;
- **les textes restent des textes**, modifiables par double-clic ;
- **ce qui est caché dans le fichier** (calque masqué, objet invisible ou
  transparent) arrive sur le calque **Ignoré** : rien n'est affiché ni gravé,
  mais la tête laser de la liste le fait réapparaître. Pratique pour un
  modèle qui contient plusieurs variantes ;
- **ce qui est masqué par un détourage** (clipPath) ou un masque n'est pas
  gravé : seule la partie visible à l'écran est gardée ;
- **un trait en pointillés** donne des tirets (lignes de pliage ou de
  perforation), pas un trait continu ;
- en bas à gauche du plateau, décalé vers la droite de la distance de
  **surbalayage** quand il est activé, pour que la tête ait la place de
  dépasser à gauche.

Si l'éditeur contient déjà des objets (un premier porte-clés, par
exemple), Laser Studio Pro demande quoi faire du nouveau dessin :

- **Ajouter sans toucher aux objets** : il arrive au même endroit, par-dessus ;
- **Supprimer les objets présents** : il les remplace ;
- **Ajouter à droite** : il se place à droite des objets présents ;
- **Ajouter au-dessus** : il se place au-dessus des objets présents.

Il en va de même pour la bibliothèque, les générateurs (boîte, boule de
Noël, porte-clés, puzzle), la vectorisation et Stencil Studio. Le puzzle
garde la position choisie dans sa fenêtre (calée sur l'image), sauf si
vous l'ajoutez à droite ou au-dessus. **Ctrl+Z** annule l'ajout d'un
coup, objets supprimés compris.

Un DXF arrive groupé sur le premier calque de découpe. Pour donner des
calques différents à ses parties, **dégroupez-le** : clic droit ›
**Dégrouper**. Chaque tracé devient un objet séparé.

## Assigner un calque

1. Sélectionnez un ou plusieurs objets : clic, puis **Maj + clic** pour en
   ajouter, ou tracez un cadre autour.
2. Choisissez le calque dans la liste **Calque** du panneau des
   propriétés, ou faites clic droit › **Assigner au calque**.

Pour traiter plusieurs objets comme un seul, groupez-les (voir
ci-dessous) : chacun garde son calque.

## La liste des objets

À droite du canevas, la liste **Objets** montre tout ce qui est sur la
grille, du dessus de la pile vers le dessous, avec le calque de chacun.
Cliquer une ligne sélectionne l'objet sur le canevas (**Maj + clic** ou
**Ctrl + clic** pour en choisir plusieurs) ; ses propriétés s'affichent
juste en dessous. Un double-clic sur un nom permet de le renommer.

Sur chaque ligne :

- l'**œil**, en première colonne, masque l'objet sur le canevas pour y voir
  plus clair, y compris un objet à l'intérieur d'un groupe (le groupe est
  dessiné sans lui). Un objet masqué **reste gravé** : son nom passe en
  italique.
- la **tête laser**, en deuxième colonne (faisceau rouge : l'objet est
  gravé), met l'objet sur le calque **Ignoré** quand on clique dessus : il
  n'est plus affiché, ni gravé, ni découpé, son nom est barré et la tête
  laser aussi. L'objet retient son calque : un nouveau clic le lui rend,
  avec ses réglages de gravure ou de découpe. Sur un groupe, elle agit sur tous ses
  objets, chacun retrouvant son propre calque ; dans un groupe combiné, un
  objet ignoré ne compte plus dans l'opération.
- la **poubelle**, tout au bout, supprime l'objet. Dans un groupe, elle le
  retire du groupe (un groupe vidé disparaît aussi). **Ctrl+Z** l'annule.

Un objet masqué ou ignoré ne réagit plus à la souris sur le canevas, mais
on peut le choisir dans la liste : son contour apparaît en pointillés
gris et ses propriétés s'ouvrent. Choisir un calque dans la liste
**Calque** fait réapparaître un objet ignoré sur ce calque (pour un
groupe, sur tous ses objets).

Changer le calque d'un groupe (liste **Calque** des propriétés, ou clic
droit › **Assigner au calque**) le change pour tous les objets du groupe.

Les boutons sous la liste :

- **Monter** / **Descendre** : change la place de l'objet dans la pile.
- **Grouper** (Ctrl+G) : les objets se déplacent d'un bloc, et gardent
  chacun leur calque et leur remplissage. Un groupe se déplie dans la
  liste pour voir ses objets.
- **Dégrouper** : rend les objets du groupe, à leur place. Un texte
  redevient un texte modifiable.
- **Combiner** : groupe les objets en ne gardant qu'une surface, gravée
  sur le calque de l'objet du dessous :

| Opération | Ce qui est gravé |
|-----------|------------------|
| Union | Tout ce que couvre au moins un objet |
| Différence | L'intérieur de l'objet du dessous, moins celui des objets du dessus (pour évider une forme) |
| Intersection | Seulement la partie commune à tous les objets |
| Exclusion | Ce que couvre un seul objet ; les chevauchements restent vides |

Pour une différence, l'ordre compte : dépliez le groupe et utilisez
**Monter** / **Descendre** sur ses objets. Choisir une autre opération
avec le groupe sélectionné la change ; **Grouper** revient à un simple
groupe. Les mêmes choix sont dans le clic droit › **Combiner** sur le
canevas, et dans le clic droit sur la liste quand plusieurs objets y sont
sélectionnés (Groupe, Union, Différence, Intersection, Exclusion,
Dégrouper).

## Les outils de l'éditeur

**Ajouter et dessiner**

- **+ Texte** : un texte modifiable (police, gras, italique, taille,
  espacement des lettres), droit ou courbé sur un cercle.
- **+ Forme** : rectangle, ellipse, ligne ou polygone régulier.
- Outils de tracé : **Ligne**, **Rectangle**, **Ellipse**, **Cercle**, au
  clic-glisser sur le canevas (Échap pour annuler).
- **Mesure** : mesurer une distance sur le canevas.
- **Bibliothèque** (barre de gauche du canevas) et **Générateurs** (icône en
  tête de la barre d'édition, à droite du canevas : boîte, puzzle, boule de
  Noël, porte-clés) : voir [Les outils](outils.md).
- **Vectoriser une image**, à côté d'*Importer SVG / DXF* : ouvre l'onglet
  *Vectorisation d'image*, pour transformer une photo ou un dessin en tracé.
- Sur un canevas vide, de gros boutons proposent de commencer :
  **Importer un fichier**, **Dessiner une forme**, ouvrir la
  **Bibliothèque de modèles**, **Vectoriser une image**, ou créer une pièce
  avec l'un des quatre générateurs (boîte, puzzle, boule de Noël, porte-clés).

**Modifier**

- Panneau des propriétés : position **X / Y**, **Largeur**, **Hauteur**,
  **Rotation**, et **Ancrage** (le coin qui reste en place quand la taille
  change).
- **Pivoter 90°**, **Dupliquer**, **Supprimer**, **Tout supprimer**.
- **Annuler** (Ctrl+Z) et **Refaire** (Ctrl+Y).
- **Zoom avant** (Ctrl++) et **Zoom arrière** (Ctrl+-) : les loupes au bout
  de la barre d'édition, ou la molette de la souris.
- **Éditer les nœuds** pour déplacer les points d'un tracé, ou **Exploser
  en segments** pour le découper en morceaux : clic droit, ou le menu
  **Tracés et textes** de la barre d'édition (avec le texte sur un tracé et
  le texte de médaille).

**Organiser**

- **Alignement / Distribution** : dès que deux objets sont sélectionnés,
  une rangée de boutons apparaît sous leurs propriétés pour les aligner à
  gauche, au centre, en haut…, ou les répartir à intervalles égaux (trois
  objets au moins).
- **Accroche à la grille** pour placer les objets au millimètre.
- **Dupliquer en série**, **Imbrication auto** et **Gabarit de placement** :
  le menu **Disposer** de la barre d'édition. Ces outils et le **texte le
  long d'un objet** sont décrits dans [Les outils](outils.md).
- **Plein écran** pour travailler plus confortablement.

## L'ordre de découpe

La case **Ordre de découpe sûr** (*Fichier › Paramètres › Configuration GRBL*) fait
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
