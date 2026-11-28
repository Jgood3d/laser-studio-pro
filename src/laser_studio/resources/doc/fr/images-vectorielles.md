# Images vectorielles

[‹ Retour au sommaire](index.md)

## Deux façons de décrire une image

Une **image matricielle** (photo JPEG, PNG…) est une grille de petits
carrés de couleur, les *pixels*. Elle décrit très bien les nuances d'une
photo, mais si on l'agrandit, les pixels deviennent visibles et les bords
sont crénelés.

Une **image vectorielle** (SVG, DXF…) ne contient pas de pixels : elle
décrit des **formes géométriques** par leurs coordonnées. Au lieu de dire
« ces 10 000 pixels sont noirs », elle dit « un cercle de 20 mm de diamètre,
centré ici ». On peut l'agrandir autant qu'on veut, le tracé reste
parfaitement net.

## Qu'est-ce qu'un vecteur ?

Le dessin vectoriel est fait de **chemins** (ou *tracés*). Un chemin est
une suite de points reliés par des segments droits ou par des **courbes de
Bézier**, dont la forme est réglée par des poignées.

- Un chemin **fermé** revient à son point de départ : il délimite une
  surface (un cercle, un cœur, une lettre).
- Un chemin **ouvert** a deux extrémités : c'est une simple ligne.

Chaque chemin peut avoir :

- un **contour** (*stroke*) : le trait qui suit le chemin, avec une
  épaisseur et une couleur ;
- un **remplissage** (*fill*) : la couleur de la surface à l'intérieur d'un
  chemin fermé.

Un texte est lui aussi une forme vectorielle : chaque lettre est dessinée
par des chemins.

## Pourquoi c'est idéal pour le laser

Le laser se déplace d'un point à un autre : un chemin vectoriel lui donne
directement le trajet à suivre. C'est ce qui permet de **découper** et de
**marquer** avec précision, à la cote exacte.

Dans l'éditeur vectoriel, chaque élément est attribué à un calque :

| Élément du dessin           | Calque conseillé |
|-----------------------------|------------------|
| Contour extérieur d'une pièce, trous | Découpe (le laser suit le chemin et traverse) |
| Trait décoratif, ligne de pliage | Marquage (le laser suit le chemin en surface) |
| Surface pleine, texte en aplat | Gravure remplie (le laser balaie l'intérieur) |

Une même forme peut servir deux fois : un cercle peut être gravé en plein
puis découpé, en le dupliquant sur deux calques. La marche à suivre est
expliquée dans [Comment graver ou découper avec une image
vectorielle](graver-decouper-vectoriel.md).

## D'où viennent les dessins vectoriels ?

- **Logiciels de dessin** : Inkscape (gratuit), Illustrator, ou un logiciel
  de CAO pour les fichiers DXF. Importez-les par **Outils › Importer SVG /
  DXF…**
- **L'éditeur de Laser Studio Pro** : textes, formes simples, et les
  générateurs du menu Outils (voir [Les outils](outils.md)).
- **La bibliothèque de modèles**, prêts à graver.
- **L'onglet Vectorisation d'image**, qui transforme une image matricielle
  (un logo, un dessin au trait) en chemins vectoriels, en noir et blanc ou
  en couleur.

> **Astuce** : la vectorisation donne de bons résultats sur des dessins
> nets et contrastés. Pour une photo, préférez l'onglet *Graver une image*,
> qui grave les nuances par tramage.
