# Bibliothèque de modèles

Les modèles de ce dossier sont proposés dans **Outils → Bibliothèque…** (et le bouton « Modèles » de l'éditeur vectoriel), puis importés dans l'éditeur vectoriel. Ils sont embarqués dans les exécutables avec le reste de `resources/`.

On peut aussi en ajouter sans recompiler : un dossier `resources/library/` placé à côté de l'exécutable est lu en plus de celui-ci.

## Organisation

```
library/
    trophees/                      une catégorie par dossier
        _category.json             facultatif : nom de la catégorie dans chaque langue
        totem-brevet-aviron/       un modèle par dossier
            totem-brevet-aviron.svg            le modèle (le premier .svg du dossier)
            totem-brevet-aviron_preview.png    facultatif : aperçu (nom contenant « preview »)
            readme.txt                         facultatif : texte affiché dans la fiche
            info.json                          facultatif : titre, auteur, licence, description
```

Sans `_category.json`, le nom de la catégorie vient du nom du dossier (`medailles` donne « Medailles »). Sans aperçu, le SVG est dessiné à la place.

### `_category.json`

```json
{"title": {"fr": "Trophées et récompenses", "en": "Trophies and awards"}}
```

### `info.json`

Tous les champs sont facultatifs. Chaque texte peut être une simple chaîne, ou une traduction par langue (`fr`, `en`, `de`, `es` ; à défaut, le français est affiché).

```json
{
  "title": {"fr": "Totem brevet d'aviron", "en": "Rowing award totem"},
  "author": "Nom de l'auteur",
  "license": "Libre d'utilisation pour usage personnel et associatif",
  "description": {"fr": "Totem en 3 pièces…", "en": "3-piece totem…"},
  "tags": ["aviron", "trophée"],
  "svg": "fichier.svg"
}
```

`tags` sert à la recherche ; `svg` choisit le fichier quand le dossier en contient plusieurs.

## Préparer le SVG

Le fichier est importé tel qu'il est dessiné, en millimètres (unités du document : `width`, `height`, `viewBox`).

- **Calques** : les tracés sont répartis sur les calques de l'éditeur d'après le nom du calque (ou du groupe) Inkscape qui les contient :
  - « Découpe », « Découpes », « Cut » → calque **Découpe** ;
  - « Gravure », « Engrave », « Remplissage » → calque **Gravure** ;
  - « Marquage », « Mark », « Trait » → calque **Marquage**.

  Sans calque ni groupe nommé ainsi, c'est le nom de l'élément qui compte : un chemin nommé « Découpe » ou un cercle nommé « Trou » (« Hole ») va en découpe. Sinon, un tracé rempli va en gravure, un contour seul en découpe. « Contour » n'est pas un nom reconnu : selon les fichiers, il désigne un cadre gravé ou une découpe.
- **Calques cachés** : ils ne sont pas importés. Pratique pour garder des éléments de construction (« sources ») dans le fichier. **Le calque « Découpe » doit donc être visible** dans le fichier enregistré.
- **Noir et blanc** : sur la gravure, une forme foncée est gravée, une forme blanche (ou très claire) ne l'est pas : elle est creusée dans ce qui est gravé en dessous (un texte blanc sur un bandeau noir reste en réserve). La gravure importée est l'union des formes foncées, moins les formes claires, dans l'ordre du dessin.
- **Variantes** : un groupe (ou calque) dont les éléments nommés sont tous cachés sauf un devient un choix dans la fiche du modèle. Exemple : le calque « Niveau du brevet » du totem contient « Niveau 1 », « Niveau 2 », « Niveau 3 », « Bronze », « Argent », « Or » ; seul le texte choisi est importé. L'élément visible dans le fichier est le choix par défaut. Le groupe doit avoir un parent : des éléments posés directement à la racine du document ne forment pas un choix (les regrouper, comme « Orientation du bateau » du porte-clef).
- **Textes** : chaque texte visible apparaît dans la fiche du modèle, où l'utilisateur peut le remplacer avant l'import (nom de la régate, du club…) ; le nom du champ est le nom (ou l'id) du texte dans Inkscape. Un texte foncé devient ensuite un texte modifiable de l'éditeur (police, taille, gras) ; un texte blanc est creusé dans la gravure, il devient donc un tracé. Si la police n'est pas installée chez l'utilisateur, une police de remplacement est utilisée : pour un rendu exact, convertir le texte en chemin dans Inkscape (Chemin → Objet en chemin), mais il ne sera plus remplaçable.
- **Transformations** (`translate`, `scale`, `matrix`…) : prises en compte.
- **Images bitmap** (`<image>`) : non importées.

Les modèles ajoutés doivent pouvoir être redistribués avec Laser Studio Pro : indiquer leur auteur et leur licence dans `info.json`.
