# Comment graver une image

[‹ Retour au sommaire](index.md)

L'onglet **Graver une image** sert à graver simplement une photo, un
dessin ou un logo : vous chargez l'image, vous la réglez, et Laser Studio
Pro la transforme en points gravés, ligne après ligne.

C'est le bon onglet pour une **gravure seule**, sans découpe. Pour graver
et découper la même pièce, ou pour travailler avec des formes, utilisez
l'onglet *Graver une image vectorielle* (voir
[Comment graver ou découper avec une image vectorielle](graver-decouper-vectoriel.md)).

## En bref

1. Cliquez sur **Charger Image**, ou glissez-déposez le fichier dans
   l'onglet (PNG, JPEG ou BMP).
2. Donnez la **taille** voulue en millimètres.
3. Choisissez la **matière** (fond clair ou fond noir) et le **calque de
   gravure**.
4. Ajustez **luminosité, contraste, gamma et netteté** en regardant
   l'aperçu.
5. Choisissez l'**algorithme de tramage**.
6. **Générez le G-code** et vérifiez-le dans *Visualisation 2D G-Code*.

## Taille et position

| Réglage           | Rôle |
|-------------------|------|
| Largeur, Hauteur  | Taille de la gravure, en mm |
| Conserver le ratio | Modifier la largeur ajuste la hauteur, pour ne pas déformer l'image |
| Offset X, Offset Y | Position de l'image sur le plateau, depuis l'origine de la machine |

À l'ouverture, l'image est insérée à sa taille d'origine, ou réduite si
elle dépasse la zone de travail. La barre d'outils permet aussi de la
**pivoter** de 90°, de la **retourner** (miroir horizontal ou vertical) et
de la **supprimer**.

**Recadrer** (barre flottante au-dessus de l'aperçu) ouvre l'image entière :
tracez le cadre à garder, déplacez-le en glissant à l'intérieur,
redimensionnez-le par ses coins et ses bords (**Garder les proportions** au
choix). La taille gravée suit le cadre, à la même échelle. Le cadre reste
modifiable : rouvrez **Recadrer** pour l'élargir, ou cliquez sur **Toute
l'image** pour revenir à l'image complète.

## La matière

Le laser ne grave pas de la même façon sur toutes les surfaces :

- **Fond clair** (bois, carton, cuir) : le laser **noircit** ce qu'il
  brûle. Les zones sombres de l'image sont gravées.
- **Fond noir** (aluminium anodisé, verre peint, ardoise, acrylique
  noir) : le laser **éclaircit** ce qu'il brûle. L'image est inversée
  automatiquement pour que le résultat ressemble à la photo.

Le choix de la matière coche ou décoche pour vous la case **Inverser
Couleurs (Négatif)**, que vous pouvez aussi régler à la main.

## Le calque de gravure

L'image est gravée avec la **puissance** et la **vitesse** d'un calque en
mode *Gravure remplie*. Choisissez-le dans la liste *Calque de gravure* ;
ses réglages se modifient dans l'onglet *Calques (Layers)*. Voir
[Comprendre les calques et les matériaux](calques-et-materiaux.md).

## Les réglages de l'image

| Réglage    | Effet |
|------------|-------|
| Luminosité | Éclaircit ou assombrit toute l'image |
| Contraste  | Écarte les clairs et les sombres : l'image devient plus franche |
| Gamma      | Éclaircit ou assombrit les tons moyens, sans toucher au noir et au blanc |
| Netteté    | Accentue les contours : visages, petits détails et textes ressortent mieux. Au-delà de 60, des halos peuvent apparaître |
| Appliquer un filtre | **Effet BD** : noircit le bord des traits pour donner un effet bande dessinée. Une fenêtre s'ouvre avec deux curseurs, et l'aperçu les suit en direct : **Rayon du masque** (en mm sur la pièce : petit rayon, traits fins ; grand rayon, traits épais et aplats noirs) et **Pourcentage de noir** (plus haut, plus de noir autour des traits). **OK** garde l'effet, **Annuler** remet l'image d'avant. Choisir à nouveau « Effet BD » permet de le régler, « Aucun » le retire |

Chaque réglage s'annule avec **Ctrl+Z** et se refait avec **Ctrl+Y**.
**Réinitialiser Réglages Image** remet tout à zéro. La case **Afficher
l'originale** montre l'image de départ à côté du rendu.

## Le tramage

Un laser ne sait pas faire du gris : à chaque point, il grave ou il ne
grave pas. Le **tramage** imite les nuances en dosant la densité des
points gravés, comme dans un journal imprimé.

| Algorithme | Rendu |
|------------|-------|
| Floyd-Steinberg | Le plus courant, bon pour les photos |
| Jarvis, Judice & Ninke, Stucki | Grain plus fin et plus doux, très bons pour les portraits |
| Atkinson | Contraste marqué, clairs et sombres francs |
| Sierra, Sierra Lite, Burkes | Variantes proches de Floyd-Steinberg ; Sierra Lite est le plus rapide |
| Bayer 2x2, 4x4, 8x8 | Trame régulière en motif, effet graphique ou rétro |
| Seuil Simple (Binaire) | Noir ou blanc, sans nuance : idéal pour un logo ou un texte |
| Niveaux de Gris | Pas de points : la puissance du laser varie selon le gris (voir [les modes de gravure](modes-de-gravure.md)) |

Vous hésitez ? Le bouton **Algorithme de tramage** affiche une vignette de
votre image pour chaque algorithme, avec vos réglages actuels. Cliquez sur
celle qui vous plaît.

## La résolution

La résolution est le nombre de **lignes par millimètre** gravées. Deux
façons de la régler :

- **Lignes / mm** : vous saisissez la valeur.
- **Focale laser (spot)** : la valeur est calculée d'après la taille du
  point de votre laser (bouton *Configurer la focale du laser*).

Un indicateur dit si l'écart entre les lignes convient : *trop fin*
(les lignes se chevauchent et la matière brûle), *zone recommandée*, ou
*grossier* (on voit des rayures). En général, 5 à 10 lignes/mm conviennent
à une diode laser.

> **Astuce** : avant une gravure importante, faites un essai sur une chute
> de la même matière avec **Outils › Matrice de Test**, qui peut graver
> une zone de votre image avec plusieurs puissances et vitesses.
