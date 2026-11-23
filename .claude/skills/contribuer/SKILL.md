---
name: contribuer
description: Règles pour modifier Laser Studio Pro (code, traductions, documentation, ressources) - mettre le dépôt à jour avant tout changement (gh repo sync ou git pull), coder dans src/, respecter modèle / vue / contrôleur, suivre PEP 8, mettre la documentation à jour, vérifier avant de commiter. À suivre dès qu'une demande touche un fichier du dépôt, même petite (« corrige », « ajoute », « change le texte », « fais un commit »), et surtout quand Julien, qui débute avec git, travaille sur le dépôt.
---

# Contribuer à Laser Studio Pro

Julien, propriétaire du dépôt (Jgood3d sur GitHub), n'est pas développeur et
apprend git. Parle-lui simplement, en français, sans jargon, et explique en une
phrase ce que fait chaque commande git avant de la lancer. Quand quelque chose
cloche (retard, conflit, fichier écrasé), corrige-le calmement, sans reproche.

Le dépôt de référence est `Jgood3d/laser-studio-pro`. Les branches de travail
partent de `Dev` et y reviennent par une pull request.

## 1. Mettre le dépôt à jour, avant tout changement

Pourquoi : un commit fait depuis une copie trop ancienne remet en place des
fichiers que d'autres ont déplacés ou supprimés, et efface leur travail sans
que personne ne s'en aperçoive. Un hook (`.claude/hooks/verifier-depot-a-jour.sh`)
refuse d'ailleurs toute modification tant que la branche est en retard.

À faire au début de chaque tâche, avant de toucher un fichier :

1. **Repérer les remotes.** `git remote -v` : le dépôt principal est celui dont
   l'adresse contient `Jgood3d/laser-studio-pro` (souvent `origin`, parfois
   `upstream` chez un contributeur). On l'appelle `<principal>` ci-dessous.
2. **Vérifier qu'il n'y a pas de travail en cours.** `git status`. S'il y a des
   fichiers modifiés et pas encore commités, montre-les à Julien et demande-lui
   ce qu'il veut en faire (les commiter d'abord, en général). Ne lance jamais
   `git stash`, `git reset`, `git checkout -- <fichier>` ni `git clean` sans son
   accord : ces commandes peuvent faire disparaître son travail.
3. **Récupérer la branche distante.**
   - Si `gh` est installé et connecté (`gh auth status` répond sans erreur) :
     `gh repo sync --source Jgood3d/laser-studio-pro --branch <branche>`.
     Jamais `--force` : il écraserait les commits locaux.
   - Sinon : `git pull --ff-only <principal> <branche>`.
   - Si la commande refuse parce que les deux côtés ont avancé (« diverging »,
     « not possible to fast-forward ») : explique la situation à Julien, puis,
     avec son accord, `git pull --no-rebase <principal> <branche>`.
4. **Récupérer Dev.** Si la branche n'est pas `Dev` (ni `main`) :
   `git fetch <principal>` puis `git merge <principal>/Dev`. En cas de conflit,
   montre les fichiers concernés, explique les deux versions et choisis avec
   Julien ; pour un fichier que `Dev` a découpé ou supprimé, c'est presque
   toujours la version de `Dev` qu'il faut garder, en y reportant ses ajouts.
5. **Si sa pull request est déjà fusionnée** (`gh pr list --head <branche>
   --state merged`), propose plutôt une branche neuve :
   `git switch -c <nouvelle-branche> <principal>/Dev`.

Sans réseau, le hook laisse passer : préviens Julien que le dépôt n'a pas pu
être vérifié. S'il demande explicitement de travailler sans mise à jour, tu
peux écrire `date +%s > .git/claude-verif-a-jour` (valable 15 minutes).

## 2. Coder dans `src/`

- Le code de l'application vit dans `src/laser_studio/`, celui de Stencil
  Studio dans `src/stencil_studio/`, et ce qu'ils partagent dans
  `src/laser_common/`. Tout nouveau fichier Python va là, dans le dossier qui
  correspond à son rôle (voir la section 3).
- À la racine, seuls restent `main.py` (qui ajoute `src/` au chemin), les
  `tests/`, les `tools/`, le `packaging/` et la documentation : pas de code
  de l'application à la racine, sinon il manque dans les paquets (RPM, pip).
- Ressources (images, polices, icônes, bibliothèque de modèles) :
  `src/laser_studio/resources/`, chargées avec `find_resource`.
- Ne recrée pas un fichier supprimé et ne copie pas un fichier depuis une autre
  copie du projet (archive, autre dossier, ancienne version) : repars du
  fichier actuel et applique-lui la modification.

## 3. Modèle / vue / contrôleur

Le projet quitte progressivement les mixins (classes qui partagent toutes le
`self` de la fenêtre) pour séparer trois rôles. Tout nouveau code suit ce
découpage ; on n'ajoute pas de nouveau mixin ni de logique dans `main_window.py`.

| Rôle | Où | Ce qu'il fait | Ce qu'il ne fait pas |
|---|---|---|---|
| Calcul pur | `gcode/`, `grbl/`, `image/`, `vector/`, `camera/`, `library/` | géométrie, G-Code, traitement d'image, commandes GRBL | aucun import de PyQt6 (sauf exceptions déjà notées dans ARCHITECTURE.md) ; testable sans écran |
| Modèle | `models/` | les données et leur état (`QObject` qui émet un signal quand elles changent : `VectorDocument`, `LayersModel`, `MachineConfig`…) | pas de widget, pas de boîte de dialogue |
| Vue | `ui/` (onglets `ui/tabs/`, dialogues `ui/dialogs/`, widgets `ui/widgets/`, éditeur `ui/vector_editor/`) | affiche le modèle, émet des signaux quand l'utilisateur agit | pas de calcul métier, pas d'accès au port série ni aux fichiers du projet |
| Contrôleur | `controllers/` | reçoit les signaux de la vue, agit sur le modèle et les services (graveur, job, projet) | ne construit pas de widget ; les questions à l'utilisateur passent par `self.dialogs` (`UserDialogs`) |

En pratique :
- Un contrôleur est un objet ordinaire qui reçoit ce dont il a besoin à sa
  création (modèle, vue, fonctions) ; il ne va pas chercher des attributs de la
  fenêtre principale au hasard.
- La vue et le contrôleur se parlent par signaux Qt (`pyqtSignal`), branchés là
  où ils sont créés.
- Toute modification de géométrie sur le canevas appelle `push_undo_snapshot()`
  avant de changer quoi que ce soit (annuler / refaire).
- Tout texte affiché passe par `tr("clé")`, avec la clé dans les quatre langues
  de `src/laser_studio/i18n/translations.py` (fr, en, de, es).
- Avant d'ajouter une méthode, cherche si elle existe déjà ailleurs
  (`git grep "def nom_de_la_methode"`) : pas de doublon entre l'ancien et le
  nouveau code.

`ARCHITECTURE.md` décrit le rôle de chaque dossier et de chaque fichier :
lis la partie concernée avant de créer un fichier.

## 4. PEP 8, autant que possible

- Noms : `snake_case` pour les fonctions, méthodes et variables,
  `CamelCase` pour les classes, `MAJUSCULES` pour les constantes.
- Lignes de 120 caractères au plus (la règle du projet, plus souple que les 79
  de PEP 8), indentation de 4 espaces, deux lignes vides entre les fonctions
  de premier niveau.
- Imports en tête de fichier, un par ligne, sans `import *` ; un import placé
  dans une fonction (pour accélérer le démarrage, ou éviter une boucle) porte
  un commentaire qui dit pourquoi.
- Pas de `except:` nu : attraper une exception précise.
- Docstrings et commentaires en français, qui expliquent pourquoi plutôt que
  ce que fait la ligne.
- N'en profite pas pour reformater des fichiers entiers : seul le code que tu
  touches suit ces règles, pour que les changements restent lisibles.

Si `ruff` ou `pycodestyle` est installé, lance-le sur les fichiers modifiés
(`ruff check --line-length 120 <fichiers>` ou
`pycodestyle --max-line-length=120 <fichiers>`) et corrige ce qui concerne
tes lignes.

## 5. Mettre la documentation à jour

Dans le même commit que le code, selon ce qui change :

| Changement | Fichier |
|---|---|
| Nouveauté ou correction visible par l'utilisateur | `CHANGELOG.md`, section `[Non publié]` (Ajouté / Modifié / Corrigé) |
| Nouveau fichier, fichier déplacé ou rôle changé | `ARCHITECTURE.md` (arborescence et tableau des rôles) et la liste « Structure du projet » de `README.md` |
| Nouvelle fonction ou fonction modifiée dans l'interface | aide intégrée `src/laser_studio/resources/doc/fr/*.md` (F1 dans l'application ; voir le `README.md` de ce dossier) |
| Nouveau texte d'interface | clés dans `i18n/translations.py`, dans les quatre langues |
| Signaux de l'interface modifiés | `python tools/signal_map.py` régénère la carte des signaux |

Écris pour l'utilisateur dans le CHANGELOG et l'aide (ce qu'il voit et ce
qu'il peut faire), pour le développeur dans ARCHITECTURE.md.

## 6. Vérifier avant de commiter

1. Tests : `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests`
   (sous Windows : `set QT_QPA_PLATFORM=offscreen` puis
   `py -m unittest discover -s tests`). Ajoute un test pour ce que tu as
   corrigé ou ajouté, dans `tests/`.
2. `python tools/check_ui_attributes.py` (attributs utilisés mais jamais créés)
   et `python tools/check_translations.py` (clés manquantes).
3. **Rien de supprimé n'est revenu.** Compare ce qui va être commité aux
   fichiers supprimés auparavant :
   ```bash
   git diff --cached --name-only --diff-filter=A > /tmp/ajoutes.txt
   git log --diff-filter=D --name-only --format= | sort -u | grep -Fxf /tmp/ajoutes.txt
   ```
   Une ligne affichée = un fichier supprimé qui revient : demande à Julien si
   c'est voulu avant de continuer.
4. **Pas de grosse suppression inattendue.** `git diff --cached --numstat` : un
   fichier avec beaucoup de lignes supprimées alors que la demande ne le
   justifie pas signale souvent une ancienne version qui en écrase une
   récente. Regarde le diff de ce fichier avant de commiter.
5. Commit : message en français, au format `type(zone): résumé`
   (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`), avec un corps qui
   explique pourquoi. Pousse seulement si Julien le demande, puis propose la
   pull request vers `Dev` (`gh pr create --base Dev`).
