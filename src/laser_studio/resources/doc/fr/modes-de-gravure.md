# Comprendre les différents modes de gravure

[‹ Retour au sommaire](index.md)

Deux réglages influencent beaucoup la qualité d'une gravure : la façon dont
le laser **dose sa puissance** (fixe ou variable) et le **surbalayage**.

## Puissance fixe ou variable

### Le problème

La tête du laser ne va pas toujours à la même vitesse : elle **ralentit**
pour démarrer, freiner et tourner dans les angles. Or, plus la tête est
lente, plus le laser reste longtemps au même endroit, et plus il chauffe
la matière.

### M3 : puissance fixe

En mode **M3**, le laser garde **exactement la même puissance**, quelle que
soit la vitesse. Là où la tête ralentit (angles, débuts et fins de ligne),
la gravure est plus foncée, et parfois brûlée.

Ce mode reste utile pour la **découpe** : une puissance constante aide à
traverser la matière régulièrement, y compris dans les angles.

### M4 : puissance variable (dynamique)

En mode **M4**, le graveur **adapte la puissance à la vitesse réelle** : si
la tête ralentit de moitié, la puissance baisse de moitié. La quantité
d'énergie reçue par la matière reste la même partout.

C'est le mode conseillé pour la **gravure** et le **marquage** : angles nets,
pas de points brûlés, teinte régulière.

### Où le régler

- Pour toute la machine : **Paramètres › Configuration GRBL**, réglage
  *Commande Laser*.
- Pour un calque : colonne **Laser** de l'onglet *Calques (Layers)* :
  - **Auto (global)** reprend le choix de la Configuration GRBL ;
  - **M4 dynamique** ou **M3 fixe** l'impose à ce calque seulement.

Vous pouvez par exemple graver en M4 et découper en M3 dans le même
travail.

> ⚠ **Le mode laser de GRBL ($32) doit être activé.** Sans lui, en M4, le
> laser peut rester allumé pendant les déplacements rapides et laisser des
> traces de brûlure. Laser Studio Pro vérifie ce réglage à la connexion et
> vous prévient s'il est désactivé. Pour l'activer, envoyez `$32=1` dans
> la console, puis `$$` pour vérifier.

### Les niveaux de gris

Le tramage imite les nuances avec des points tout ou rien. L'algorithme
**Niveaux de Gris** (onglet *Graver une image*) fait autrement : chaque
point est gravé avec une **puissance proportionnelle à son gris**. Le
rendu est plus doux, mais dépend beaucoup de la matière : faites un essai.
Le mode M4 est recommandé.

## Le surbalayage (overscan)

### Le problème

En gravure remplie, la tête fait des allers-retours. À chaque bout de
ligne, elle doit **freiner, s'arrêter et repartir**. Pendant ce temps, sa
vitesse n'est pas celle demandée : les bords gauche et droit de la gravure
ressortent plus foncés, ou forment des bandes.

### La solution

Avec le **surbalayage**, la tête **dépasse un peu le dessin** de chaque
côté, laser éteint. Elle a ainsi la place d'accélérer avant d'entrer dans
le dessin et de freiner après en être sortie : toute la surface gravée
l'est à vitesse constante.

```
   laser éteint   laser allumé    laser éteint
  |<---------->|=================|<---------->|
    accélère      vitesse stable     freine
```

### Où le régler

- **Paramètres › Configuration GRBL** : *Activer le Surbalayage*, puis le
  mode (**Distance Fixe** en mm, ou **Pourcentage** de la largeur gravée)
  et la valeur.
- Onglet *Calques (Layers)* : la case **Surbalayage** de chaque calque en
  gravure remplie. Elle ne sert que si le surbalayage est activé dans la
  Configuration GRBL.

Le surbalayage n'a pas d'effet sur la découpe et le marquage, qui suivent
des contours.

Quand il est activé, l'image à graver est décalée vers la droite de la
distance de surbalayage (le décalage du job s'y ajoute), et les dessins
importés dans l'éditeur vectoriel arrivent avec la même marge à gauche :
avec un décalage de 0, la tête part du bord du plateau. Sans surbalayage,
aucune marge n'est ajoutée.

> **Attention** : la tête sort du dessin. Si la gravure commence trop près
> du bord gauche du plateau, le départ tomberait hors de la machine :
> Laser Studio Pro refuse alors de générer le G-code. Décalez le dessin ou
> réduisez le surbalayage.

## Le décalage des lignes retour

Quand la tête grave dans les deux sens, le jeu mécanique et le délai
d'allumage du laser peuvent décaler les lignes de retour : les bords
verticaux ont l'air de dents de scie. Le réglage **Décalage lignes retour**
(Configuration GRBL) corrige ce défaut. Le bouton **Générer le test
aller/retour** grave un motif de colonnes : choisissez la colonne au bord
le plus droit et saisissez la valeur correspondante.
