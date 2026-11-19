# Laser Studio Pro

Laser Studio Pro est plus qu'un logiciel de gravure : c'est un véritable
**studio de création**. Vous y préparez vos images, dessinez ou importez
vos formes, créez des objets prêts à découper (boîtes, puzzles, boules de
Noël, porte-clés…), puis vous pilotez votre graveur laser jusqu'à la pièce
terminée.

Cette aide s'ouvre à tout moment avec la touche **F1** ou par le menu
**Aide › Documentation**.

## Sommaire

- [Premiers pas](premiers-pas.md) : de l'image au G-code en quatre étapes
- [Images vectorielles](images-vectorielles.md) : qu'est-ce qu'un vecteur ?
- [Les outils](outils.md) : bibliothèque, générateurs, imbrication…

## Les trois façons de travailler au laser

Tout travail au laser repose sur trois opérations.

**La gravure** : le laser balaie une surface, ligne après ligne, et noircit
ou creuse la matière. C'est ainsi que l'on reproduit une photo, un logo
plein ou un texte en aplat.

**La découpe** : le laser suit un contour, lentement et avec beaucoup de
puissance, en une ou plusieurs passes, jusqu'à traverser la matière. C'est
ce qui détache la pièce de la plaque.

**Le marquage** : le laser suit lui aussi un contour, mais avec peu de
puissance. Il laisse un trait fin à la surface, sans traverser : contour
décoratif, repère d'assemblage, ligne de pliage…

## Les calques

Dans Laser Studio Pro, ces trois opérations sont réalisées par des
**calques** (*layers*). Chaque élément de votre travail est rangé sur un
calque, et c'est le calque qui dit au laser comment le traiter.

Trois calques de base existent toujours : **Gravure**, **Découpe** et
**Marquage**. Ils ne peuvent pas être supprimés (on les désactive s'ils ne
servent pas). Vous pouvez en ajouter d'autres, par exemple deux gravures
plus ou moins foncées.

Chaque calque a ses réglages :

| Réglage           | Rôle |
|-------------------|------|
| Mode              | *Gravure remplie*, *Découpe* ou *Marquage (contour)* |
| Puissance (%)     | Force du laser. Plus elle est élevée, plus la trace est profonde |
| Vitesse (mm/min)  | Vitesse de la tête. Plus elle est lente, plus le laser chauffe la matière |
| Passes            | Nombre de fois où le travail est répété, utile pour découper une matière épaisse |
| Pas remplissage   | Distance entre deux lignes de gravure (voir ci-dessous) |
| Surbalayage       | Gravure remplie : la tête dépasse un peu du dessin pour graver à vitesse constante |
| Laser             | Mode de puissance : *M3 fixe*, *M4 dynamique* ou *Auto* (voir ci-dessous) |
| Actif             | Un calque décoché n'est pas envoyé au graveur |

**Le remplissage.** En gravure remplie, la surface est couverte de lignes
parallèles. Le *pas de remplissage* est l'écart entre ces lignes : trop
grand, on voit des rayures ; trop petit, on brûle la matière et le travail
est plus long. Il peut être lié à la taille du point du laser : il se met
alors à jour tout seul quand vous changez de lentille ou de focale.

**Puissance continue ou adaptative.** En mode *M3 fixe*, le laser garde la
même puissance tout le temps. En mode *M4 dynamique*, il adapte sa
puissance à la vitesse réelle de la tête : dans les angles, où la tête
ralentit, il chauffe moins, ce qui évite les points brûlés. *Auto* reprend
le choix fait dans **Paramètres › Configuration GRBL**.

**L'ordre des calques** compte : ils sont exécutés de haut en bas. Placez
la découpe en dernier, pour que la pièce ne bouge pas pendant la gravure.

## Les trois onglets principaux

**Graver une image** : chargez une photo ou un dessin, réglez la taille, la
luminosité, le contraste, la netteté, puis choisissez l'algorithme de
tramage (Floyd-Steinberg, Jarvis, Stucki, Atkinson…) qui transforme les
nuances de gris en points gravés. Le bouton de comparaison montre le
résultat de chaque algorithme côte à côte.

**Graver une image vectorielle** : l'éditeur vectoriel. Importez un fichier
SVG ou DXF, ajoutez du texte et des formes, arrangez le tout sur le
plateau, puis attribuez chaque élément à un calque de gravure, de découpe
ou de marquage. Pour comprendre ce qu'est un dessin vectoriel, lisez la
page [Images vectorielles](images-vectorielles.md).

**Calques (Layers)** : la gestion des calques et des **profils
matériaux**. Un profil matériau (bois, bambou, cuir, verre, ardoise…)
regroupe les réglages de tous les calques pour ce support. Créez un profil
par matière, ajustez chaque calque, puis il suffit de choisir la matière
pour retrouver les bons réglages. Les profils s'exportent et s'importent
pour les partager.

D'autres onglets complètent ces trois-là : *Vectorisation d'image* (une
image devient un dessin vectoriel), *Séparation Couleur / Verre*,
*Visualisation 2D G-Code*, *Console / G-Code* et *File d'attente*.

## Le G-code

Une fois tout réglé, il reste à **générer le G-code** : Laser Studio Pro
transforme l'image et les éléments vectoriels en commandes GRBL, la langue
que comprend votre graveur laser (déplacements, vitesse, puissance). Avant
de lancer le travail, vérifiez le tracé dans l'onglet *Visualisation 2D
G-Code* : vous y voyez le chemin du laser et la durée estimée.

> **Sécurité** : ne laissez jamais le graveur fonctionner sans surveillance
> et portez des lunettes adaptées à la longueur d'onde du laser.
