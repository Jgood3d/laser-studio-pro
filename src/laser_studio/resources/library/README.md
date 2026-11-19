# Bibliothèque de modèles

Les modèles de ce dossier sont proposés dans **Outils → Bibliothèque…** (et l'icône « Bibliothèque » de la barre de gauche de l'éditeur vectoriel), puis importés dans l'éditeur vectoriel. Ils sont embarqués dans les exécutables avec le reste de `resources/`.

On peut aussi en ajouter sans recompiler : un dossier `resources/library/` placé à côté de l'exécutable est lu en plus de celui-ci.

## Organisation

```
library/
    trophees/                      une catégorie par dossier
        _category.json             facultatif : nom de la catégorie dans chaque langue
        totem-sportif-modele-1/    un modèle par dossier
            totem-sportif-modele-1.svg         le modèle (le premier .svg du dossier)
            totem-sportif-modele-1_photo.jpg   facultatif : photo de la pièce réalisée
            readme.txt                         facultatif : texte affiché dans la fiche
            info.json                          facultatif : titre, auteur, licence, description
```

Sans `_category.json`, le nom de la catégorie vient du nom du dossier (`medailles` donne « Medailles »).

L'**aperçu** (grille et fiche) est calculé à partir du SVG, tel qu'il sera importé : la matière (bois clair) à l'intérieur des découpes, les trous transparents, la gravure en brun foncé. Dans la fiche, il suit les options et les textes saisis. Il n'y a donc pas d'image d'aperçu à fournir. Une **photo** de la pièce réalisée (image dont le nom contient « photo », PNG, JPEG ou WebP) peut être ajoutée : elle s'affiche dans l'onglet « Photo » de la fiche.

### `_category.json`

```json
{"title": {"fr": "Trophées et récompenses", "en": "Trophies and awards"}}
```

### `info.json`

Tous les champs sont facultatifs. Chaque texte peut être une simple chaîne, ou une traduction par langue (`fr`, `en`, `de`, `es` ; à défaut, le français est affiché).

```json
{
  "title": {"fr": "Totem sportif - modèle 1", "en": "Sports totem - model 1"},
  "author": "Nom de l'auteur",
  "license": "Libre d'utilisation pour usage personnel et associatif",
  "description": {"fr": "Totem en 3 pièces…", "en": "3-piece totem…"},
  "tags": ["aviron", "trophée"],
  "svg": "fichier.svg"
}
```

`tags` sert à la recherche ; `svg` choisit le fichier quand le dossier en contient plusieurs.

## Préparer le SVG : la convention

Le fichier est importé tel qu'il est dessiné, en millimètres (unités du document : `width`, `height`, `viewBox`). Seul ce qui suit la convention est importé.

### Calques

| Calque (ou groupe) Inkscape | Contenu | Couleur | Calque de l'éditeur |
| --- | --- | --- | --- |
| `Cut` | Tracés de découpe (contour, trous) | rouge, contour sans remplissage | Découpe |
| `Engrave` | Ce qui est gravé, en remplissage | noir | Gravure |
| `Mark` (facultatif) | Contours gravés, sans remplissage | bleu | Marquage |

- Le nom doit être exactement `Cut`, `Engrave` ou `Mark` (majuscules indifférentes).
- **Tout le reste est ignoré** : un élément hors de ces calques, un calque caché, un calque d'un autre nom (pratique pour garder des éléments de construction, « sources » par exemple, dans le fichier).
- Le calque `Cut` doit être visible dans le fichier enregistré.
- **Traits** : dans `Engrave`, un trait (stroke) est gravé avec son épaisseur, comme Inkscape le dessine (bouts et angles compris) ; un pictogramme dessiné au trait s'utilise donc tel quel.
- La couleur sert à l'auteur et à l'aperçu de la fiche ; c'est le nom du calque qui décide.
- **Noir et blanc dans `Engrave`** : le noir est gravé ; le blanc (ou une couleur très claire) n'est pas gravé, il est creusé dans ce qui est gravé en dessous. Un texte blanc sur un bandeau noir reste ainsi en réserve. La gravure importée est l'union des formes foncées, moins les formes claires, dans l'ordre du dessin.

### Options

Quand le modèle se décline (niveau, résultat, orientation…) :

- les options sont des **sous-calques**, réunis dans un groupe (ou un calque) ;
- **un seul sous-calque est visible** : l'option par défaut ;
- le **nom du groupe** est le libellé du choix dans la fiche, le **nom de chaque sous-calque** celui d'une option.

Une option peut ne toucher que la gravure (groupe placé dans `Engrave`), que la découpe (dans `Cut`), ou les deux. Pour les deux, le plus simple : **un groupe du même nom dans `Cut` et dans `Engrave`**, avec les mêmes noms d'options. Ils forment un seul choix dans la fiche, appliqué aux deux (la médaille sportive : « Forme », hexagonale ou ronde). On peut aussi placer le groupe à la racine, chaque option contenant ses propres calques `Cut` et `Engrave`.

Chaque groupe doit avoir **exactement un** sous-calque visible : si tous sont cachés, ce n'est plus un choix (et rien n'en est importé).

```
Cut                         (calque, rouge)
Engrave                     (calque, noir)
    Fond logo               (rond noir)
    Motif                   (groupe : libellé du choix)
        Kayak               (sous-calque caché : une option, dessiné en blanc)
        Natation            (sous-calque caché)
        Course              (sous-calque visible : l'option par défaut)
sources                     (calque caché : ignoré)
```

Un élément nommé seul (un texte, un chemin) n'est pas une option : le mettre dans son sous-calque.

### Textes

- Chaque texte importé apparaît dans la fiche du modèle, où l'utilisateur peut changer, avant l'import, son contenu (nom de la régate, du club…), sa police et sa taille (en mm). Le nom du champ est le nom (ou l'id) du texte dans Inkscape ; la police et la taille proposées au départ sont celles du fichier.
- Dans `Engrave`, un texte noir devient un texte modifiable de l'éditeur (police, taille, gras) ; un texte blanc est creusé dans la gravure, il devient donc un tracé.
- **Police** : choisir de préférence une police fournie avec Laser Studio Pro (dossier `resources/fonts/`, chargé au démarrage, donc disponible sur tous les systèmes), par exemple **Dancing Script** pour une écriture manuscrite ou **Yantramanav** (gras et extra-gras) pour des titres. Une autre police n'est pas forcément installée chez l'utilisateur : une police de remplacement est alors utilisée. Pour ajouter une police au dossier, choisir une licence libre compatible avec la GPL (OFL par exemple) et joindre son texte. Pour un rendu exact avec une police non fournie, convertir le texte en chemin dans Inkscape (Chemin → Objet en chemin), mais il ne sera plus remplaçable.

### Le reste

- **Transformations** (`translate`, `scale`, `matrix`…) : prises en compte.
- **Images bitmap** (`<image>`) : non importées.

Les modèles ajoutés doivent pouvoir être redistribués avec Laser Studio Pro : indiquer leur auteur et leur licence dans `info.json`.
