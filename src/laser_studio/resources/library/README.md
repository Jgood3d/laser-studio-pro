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

Le modèle est importé comme avec le bouton « Importer » de l'éditeur : **la couleur de chaque tracé décide de son calque**.

| Calque (ou groupe) Inkscape | Contenu | Couleur | Calque de l'éditeur |
| --- | --- | --- | --- |
| `Cut` | Tracés de découpe (contour, trous) | rouge, contour sans remplissage | Découpe |
| `Engrave` | Ce qui est gravé, en remplissage | noir | Gravure |
| `Mark` (facultatif) | Contours gravés, sans remplissage | vert | Marquage |

- Ranger le dessin dans ces calques (nom exact, majuscules indifférentes) : les textes à proposer dans la fiche doivent s'y trouver, et les fichiers de la bibliothèque restent lisibles d'un modèle à l'autre.
- **Ce qui est caché n'est pas importé** : options non choisies, calque de construction (« sources » par exemple).
- Le calque `Cut` doit être visible dans le fichier enregistré.
- **Traits** : un trait (stroke) noir est gravé avec son épaisseur, comme Inkscape le dessine (bouts et angles compris) ; un pictogramme dessiné au trait s'utilise donc tel quel.
- **Pas de blanc pour creuser** : le blanc n'est pas une couleur de laser, un objet blanc n'est pas gravé (il arriverait sur le calque « Ignoré ») et ne creuse rien. Pour évider une forme (pictogramme en réserve dans un rond noir), faire une **Différence** dans Inkscape (Chemin › Différence) : un seul chemin noir, déjà évidé. Si le pictogramme change selon l'option, chaque option porte son propre rond évidé.
- **Texte en réserve** (texte remplaçable découpé dans un bandeau noir) : une Différence le figerait en chemin. On le met dans un **masque** du bandeau (Objet › Masque › Définir dans Inkscape, le texte en noir sur un rectangle blanc) : la fiche le propose toujours, et ce qui est saisi est découpé dans le bandeau (la médaille sportive : « Compétition de XXXX »).

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
    Motif                   (groupe : libellé du choix)
        Kayak               (sous-calque caché : une option, rond noir évidé du kayak)
        Natation            (sous-calque caché)
        Course              (sous-calque visible : l'option par défaut)
sources                     (calque caché : ignoré)
```

Un élément nommé seul (un texte, un chemin) n'est pas une option : le mettre dans son sous-calque.

### Textes

- Chaque texte importé apparaît dans la fiche du modèle, où l'utilisateur peut changer, avant l'import, son contenu (nom de la régate, du club…), sa police et sa taille (en mm). Le nom du champ est le nom (ou l'id) du texte dans Inkscape ; la police et la taille proposées au départ sont celles du fichier.
- Un texte noir devient un texte modifiable de l'éditeur (police, taille, gras) ; un texte dans un masque est découpé dans ce qu'il masque, il devient donc un tracé.
- **Police** : utiliser une police fournie avec Laser Studio Pro (dossier `resources/fonts/`, chargé au démarrage, donc disponible sur tous les systèmes) : **Dancing Script** pour une écriture manuscrite, **Rubik** en gras pour des titres. **Arial** convient aussi (sous Linux, Liberation Sans la remplace avec les mêmes dimensions). Une autre police n'est pas forcément installée chez l'utilisateur : une police de remplacement, souvent plus large, est alors utilisée. L'éditeur ne distingue que normal et gras : un `font-weight` de 600 ou plus donne le gras de la police. N'ajouter une police au dossier qu'en dernier recours : elle doit avoir une licence libre compatible avec la GPL (OFL par exemple), avec son texte joint, et exister en paquet dans les distributions Linux (le paquet Fedora utilise les polices du système à la place des copies embarquées). Le test `tests/test_bundled_fonts.py` refuse un modèle qui cite une autre police. Pour un rendu exact avec une police non fournie, convertir le texte en chemin dans Inkscape (Chemin → Objet en chemin), mais il ne sera plus remplaçable.

### Le reste

- **Transformations** (`translate`, `scale`, `matrix`…) : prises en compte.
- **Images bitmap** (`<image>`) : non importées.

Les modèles ajoutés doivent pouvoir être redistribués avec Laser Studio Pro : indiquer leur auteur et leur licence dans `info.json`.
