# Changelog — Laser Studio Pro

Toutes les modifications notables du projet sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/) —
versionnage sémantique (`MAJEUR.MINEUR.CORRECTIF`).

## [Non publié]

### Ajouté
Arrêt d'urgence toujours accessible : pendant une gravure, un homing ou un cadrage, un gros bouton rouge « Arrêt d'urgence » s'affiche dans la barre d'outils, même panneau du graveur replié ; la touche F9 (menu Job) fait de même. Le laser s'éteint et le travail est abandonné.

G-Code à régénérer : quand un réglage change après la génération (calque, taille, position, image, objet du dessin, configuration GRBL), la barre d'état affiche « ⚠ G-Code à régénérer » (un clic régénère), et l'envoi au laser ou l'ajout à la file demande confirmation avant de partir avec l'ancien G-Code. Un G-Code importé n'est pas concerné.

Cadrage visible et au plus près : la tête fait le tour du travail laser allumé à 0,5 % du S-Max (assez pour voir le point sans marquer ; réglable par machine dans Configuration GRBL, « Puissance du cadrage », pour une diode qui ne s'allume qu'à 1 ou 2 %), d'après le G-Code qui sera gravé (image et calques vectoriels). Deux modes : le rectangle qui contient tout le travail (X max, Y max, retour à X0 puis Y0 ; F6), et le tour au plus près de chaque pièce, creux compris (forme en L, étoile), à 1 mm près (nouveau bouton, Maj+F6). Sans G-Code, le rectangle reprend le cadre de l'image.

Reprendre un travail interrompu : après une alarme, un arrêt ou une coupure, le bouton « Reprendre » (⏩, panneau du graveur) relance le travail là où il s'est arrêté. La tête revient laser éteint au point exact où elle s'est arrêtée (position relue au graveur une fois arrêté, avant tout homing), avec la puissance, la vitesse et le mode du G-Code à ce point : seul le reste du trait en cours est gravé, sans décalage ni double passage. Si la position n'a pas pu être lue (coupure de courant), la reprise repart des derniers traits que le graveur avait en mémoire, regravés plutôt que laissés en trou.

Air assist par calque : une colonne « Air » dans le tableau des calques allume le soufflage (M8) pendant le calque et l'éteint (M9) ensuite, pour la gravure d'image comme pour les calques vectoriels. Décochée par défaut ; enregistrée avec le projet et le profil machine.

Simulation dans la Visualisation 2D : le bouton « Simuler » (▶) rejoue le parcours du laser en une quinzaine de secondes, dans l'ordre du G-Code.

Menu Job et raccourcis clavier : F5 générer, F6 cadrer, Maj+F6 cadrer au plus près, Ctrl+Entrée envoyer au laser, F7 pause, F8 reprise.

Durée estimée recalée sur les gravures réelles : après trois gravures terminées sur la même machine, l'estimation est corrigée d'après l'écart entre durées estimées et réelles de l'historique (« recalé sur N gravures »).

Rampe de puissance par passe : une colonne « Rampe (%) » dans le tableau des calques (case à cocher et puissance de la dernière passe, 100 % par défaut), active pour les calques de découpe, de perforation et de marquage. La puissance passe linéairement de celle du calque (première passe) à la puissance finale : 4 passes de 40 % à 100 % donnent 40, 60, 80 et 100 %. Utile pour une première passe douce (carton, mousse, bois fin : moins de flammes et de carbonisation) puis la pleine puissance. Le commentaire de chaque passe du G-Code indique sa puissance. Sans effet avec une seule passe. Case décochée par défaut : un ancien projet ne change pas. Réglages enregistrés avec le projet, le matériau et le profil machine.

Mode de calque « Perforation » (découpe en pointillé) : un nouveau mode dans la liste des modes, et une colonne « Perforation (mm) » (longueur d'un trait | longueur d'un vide, 2,0 et 1,0 mm par défaut) active pour ce mode. Le laser coupe le tracé par traits séparés de vides : ligne de pliage, ligne à déchirer, pièce gardée attachée. Le motif est ajusté à la longueur du tracé pour finir juste : un tracé fermé fait un nombre entier de périodes, un tracé ouvert (ligne de pliage) commence et finit par un trait ; un tracé plus court qu'un trait est coupé en entier. Les passes s'appliquent. Le kerf, les ponts de maintien et les arcs d'entrée et de sortie restent propres au mode Découpe. Un projet enregistré avec ce mode n'est pas relu par une version antérieure (le mode y est inconnu). Réglages enregistrés avec le projet, le matériau et le profil machine.

Entrée et sortie en arc à la découpe : une colonne « Arc (mm) » dans le tableau des calques (case à cocher et rayon, 1,0 mm par défaut), active pour les calques de découpe. Le laser s'allume sur la chute, à côté du contour, le rejoint par un quart de cercle tangent et repart de la même façon à la fin : la marque du perçage et du démarrage tombe dans la chute et non sur le bord de la pièce. La chute est à l'extérieur d'une pièce et à l'intérieur d'un trou. Un arc n'est posé que s'il a la place : sinon le rayon est réduit, le contour est repris du milieu de son plus long côté (coin de trou), puis coupé sans arc et signalé dans le G-Code. Sans effet sur les tracés ouverts ni sur les contours à ponts de maintien. Case décochée par défaut : un ancien projet ne change pas. Réglages enregistrés avec le projet, le matériau et le profil machine. L'aperçu 2D ignore les arcs pour dessiner la matière.

Compensation du kerf à la découpe : une colonne « Kerf (mm) » dans le tableau des calques (case à cocher et largeur de la saignée, 0,15 mm par défaut), active pour les calques de découpe. Les contours extérieurs sont décalés vers l'extérieur et les trous vers l'intérieur de la moitié du kerf, pour que les pièces et les trous gardent les cotes du dessin ; fonctionne pour tout objet (SVG importé, dessin, texte), pas seulement la boîte et le puzzle. Les tracés ouverts ne changent pas. Un contour plus fin que le décalage (petit trou) est coupé tel quel et signalé dans le G-Code. Case décochée par défaut : un ancien projet ne change pas. Réglages enregistrés avec le projet, le matériau et le profil machine.

Ponts de maintien à la découpe : une colonne « Ponts » (case à cocher et nombre par contour, 4 par défaut) et une colonne « Larg. pont (mm) » dans le tableau des calques, actives pour les calques de découpe. Décocher la case désactive les ponts sans perdre le nombre ni la largeur. Le laser laisse non coupés des tronçons répartis à égale distance sur chaque contour extérieur fermé, et la pièce reste attachée à la plaque jusqu'à la fin du job. Pas de pont sur les trous ni sur les tracés ouverts ; un contour trop petit en reçoit moins, ou aucun. Case décochée par défaut : un ancien projet ne change pas. Réglages enregistrés avec le projet, le matériau et le profil machine. L'aperçu 2D garde la matière dessinée à l'intérieur d'un contour à ponts (sauf avec un seul pont).

Barre d'état : à droite, une pastille colorée donne l'état du graveur (comme le panneau machine) avec la position X / Y de la tête, ou « Graveur déconnecté » ; la durée estimée du dernier G-Code généré y reste affichée.

Thème « New Dusk » (Fichier › Paramètres… › Langue et thème) : les couleurs gris-bleu doux de Dusk, modernisées : interface à plat, onglets soulignés par l'accent, coins arrondis, barres de défilement fines, icônes d'une seule couleur et police Inter (ou celle de l'interface du système). Le canevas de l'éditeur vectoriel, l'aperçu de l'image et la visualisation 2D prennent ses couleurs. « New Dusk Blue Petrol » garde les mêmes améliorations sur un bleu pétrole inspiré du Solarized Dark de VS Code. Sa version claire, « New Dawn », reprend les gris doux du thème Clair plutôt qu'un blanc pur, plus reposant pour les yeux, avec les mêmes icônes d'une seule couleur. Les icônes suivent maintenant un changement de thème sans redémarrer.

Import SVG : le dessin arrive tel que votre logiciel de dessin le montre. Les calques et groupes du fichier deviennent des groupes de la liste des objets, avec leur nom ; chaque objet va sur un calque d'après sa couleur (noir : gravure, rouge : découpe, vert : marquage, avec une tolérance sur la teinte) ; un objet blanc arrive sur le calque « Ignoré » (pour évider une forme, on fait une Différence) ; les textes restent modifiables ; ce qui est caché dans le fichier arrive sur le calque « Ignoré », d'où la tête laser de la liste des objets le fait réapparaître. Lecture conforme à la spécification SVG : styles en cascade (feuille `<style>` comprise) et héritage, visibilité, opacité, règle de remplissage, `<use>`, `<symbol>`, `<switch>`, `<svg>` imbriqué, toutes les couleurs CSS, détourages (`clipPath`) et masques (`mask`), traits en pointillés (`stroke-dasharray`, découpés en tirets), longueurs avec unité ou en pourcentage dans les attributs (`10mm`, `50%`, `2em`), propriété CSS `transform` avec `transform-origin`. Les fichiers d'Inkscape antérieurs à 0.92 (90 px par pouce) et d'Adobe Illustrator (72 px par pouce) gardent leur taille réelle.

Liste des objets de l'éditeur vectoriel : un œil devant chaque objet, groupes compris, le masque sur le canevas (il reste gravé), et une tête laser en deuxième colonne le met sur le calque « Ignoré » : plus affiché, ni gravé ni découpé. L'objet retient son calque ; un nouveau clic le lui rend, avec ses réglages. Sur un groupe, chaque objet retrouve son propre calque. Un objet masqué ou ignoré se choisit dans la liste (contour gris en pointillés) pour lui donner un autre calque. Une poubelle au bout de chaque ligne supprime l'objet, ou le retire de son groupe. Clic droit sur plusieurs objets sélectionnés dans la liste : Groupe, Union, Différence, Intersection, Exclusion, Dégrouper.

Éditeur vectoriel : liste des objets à droite du canevas, à la manière de Blender. Elle montre les objets du dessus de la pile vers le dessous, avec leur calque ; un clic sélectionne l'objet (plusieurs avec Maj ou Ctrl), un double-clic le renomme. Ses propriétés (position, rotation, calque, taille) s'affichent juste en dessous, plutôt qu'en bas de la page. Boutons pour monter ou descendre un objet, grouper et dégrouper.

Éditeur vectoriel : les groupes gardent leurs objets entiers. Un objet groupé garde son calque et son remplissage, et un texte redevient un texte modifiable une fois dégroupé (avant, grouper fusionnait tout en un seul tracé sur un seul calque).

Éditeur vectoriel : opérations booléennes **Union**, **Différence**, **Intersection** et **Exclusion** (bouton « Combiner » de la liste des objets, ou clic droit › Combiner). Le groupe ne grave plus qu'une surface, sur le calque de l'objet du dessous : une différence évide l'objet du dessous de la forme de ceux du dessus. L'ordre des objets dans le groupe se change avec Monter et Descendre.

Paramètres du graveur : bouton « Depuis le catalogue… », qui crée le profil d'un graveur GRBL du commerce (Elegoo Phecda, Ortur Laser Master 3, Sculpfun S9 et S30 Pro Max, Creality Falcon, Longer Ray5, xTool D1 Pro, Atomstack A5 Pro). Surface de travail, taille du point et vitesse maximale publiées par le constructeur, avec les liens vers ses documents ; une valeur qu'il ne publie pas n'est pas inventée. Rien n'est envoyé au graveur. On peut ajouter ses propres modèles dans le dossier `machines/` des données (format : `resources/machines/README.md`).

Historique des gravures (**Outils › Historique des gravures…**) : chaque job envoyé au graveur, direct ou depuis la file d'attente, y est noté à sa fin, avec la date, l'issue (terminée, arrêtée, erreur GRBL), la durée réelle et la durée estimée avec leur écart, la distance gravée, le nombre de lignes et la machine. Export CSV pour un tableur. Gardé sur l'ordinateur, dans `historique-gravures.jsonl`.

Graver une image : bouton « Recadrer » dans la barre flottante des aperçus. On trace le cadre à garder sur l'image entière (déplacer, redimensionner par les coins et les bords, proportions gardées au choix, « Toute l'image » pour revenir en arrière) ; la taille gravée suit le cadre, à la même échelle.

Debian et Ubuntu : paquet `.deb` (Debian 13 et plus récentes, Ubuntu 25.04 et plus récentes), avec les bibliothèques Python du système : `sudo apt install ./laser-studio-pro_<version>_all.deb`. Joint à chaque release ; construit par `packaging/debian/build-deb.sh`.

Graver une image et Visualisation 2D G-Code : loupes « Zoom avant » et « Zoom arrière » dans la barre flottante (aussi Ctrl++ et Ctrl+-), zoom centré sur la vue. Dans « Graver une image », l'originale et le rendu tramé zooment ensemble.

Graver une image : liste « Appliquer un filtre » avec un effet bande dessinée, à la manière du filtre « Bande dessinée » de GIMP, qui noircit le bord des traits avant le tramage. Choisir « Effet BD » ouvre une fenêtre avec le rayon du masque (en mm sur la pièce) et le pourcentage de noir : l'aperçu suit les curseurs en direct, « Annuler » remet l'image d'avant. Enregistré dans le projet.

Graver une image : le bouton « Charger Image » est plus grand, avec une image au-dessus du texte, pour être trouvé du premier coup.

Macros : vos propres boutons de commandes G-code, sous les actions de job (décaler la tête, origine machine, pointeur…). **Outils › Macros…** ou le bouton à droite des actions de job ouvre l'éditeur : nom, infobulle, confirmation, profils machine où la macro apparaît, G-code. Une macro part seulement graveur connecté et jamais pendant un job ; si elle allume le laser, elle est marquée d'un ⚠ et toujours confirmée (Non par défaut). Enregistrées dans `macros.yaml`, exportables et importables (nouvelle dépendance : PyYAML).

Caméra, alignement sur le plateau :
- 4 AprilTags de 40 mm aux coins du plateau par défaut (au lieu de 9 de 20 mm), à 20 mm du bord ; l'orientation d'un tag collé n'a plus d'importance. L'homographie utilise les 4 coins de chaque tag.
- Détection renforcée (affinage des coins, contraste renforcé, image agrandie ×2 si des tags manquent) ; les tags gravés sur une matière sombre peinte (en négatif) sont reconnus.
- L'assistant fait 2 à 3 captures et fusionne les tags vus : le portique peut en cacher une partie, il suffit de le déplacer entre deux captures. Il affiche la taille d'une case en pixels (6 px ou plus recommandé) et propose le choix de la résolution de la caméra (la correction de distorsion suit la résolution).
- Gabarit des tags imprimés : un cadre de 40×40 mm (taille du tag) marqué au laser à la position de chaque tag, avec son numéro ; le carré à découper de la feuille imprimée a la même taille. Un alignement incohérent (tag trop grand ou trop petit une fois ramené en mm, erreur supérieure à 5 mm) est refusé.
- Éditeur vectoriel : interrupteur « Fond caméra » et bouton « Actualiser l'image caméra » dans la barre de gauche, sans passer par la fenêtre Caméra.

Éditeur vectoriel : loupes « Zoom avant » et « Zoom arrière » dans la barre d'édition, aussi par Ctrl++ et Ctrl+- (zoom centré sur le milieu de la vue).

Linux : entrée de menu traduite (français, anglais, allemand, espagnol), avec un raccourci vers Stencil Studio (clic droit sur l'icône). Sous Wayland, la fenêtre est rattachée à cette entrée : le dock affiche l'icône de Laser Studio Pro. Fiche AppStream (description, captures d'écran, versions) pour GNOME Logiciels, Discover et les autres logithèques.

Fedora : paquet RPM dans le dépôt Copr `alemorvan/laser-studio-pro` (Fedora 43, 44 et 45, x86_64 et aarch64) : `sudo dnf copr enable alemorvan/laser-studio-pro` puis `sudo dnf install laser-studio-pro`.

Éditeur vectoriel : bouton « Tout supprimer » dans la barre d'édition (après confirmation, annulable par Ctrl+Z).

Bibliothèque de modèles (Outils → Bibliothèque…, icône « Bibliothèque » de la barre de gauche de l'éditeur vectoriel) :
- Modèles prêts à graver ou découper, rangés par catégorie, avec recherche et taille des aperçus réglable (colonnes adaptées à la largeur de la fenêtre).
- Aperçus calculés à partir du SVG, tels que la pièce sortira de la machine (matière, trous, gravure) ; dans la fiche, ils suivent les options et les textes saisis.
- Fiche de chaque modèle : aperçu, fichier SVG et photo éventuelle en grand (zoom à la molette), taille, auteur, licence, notice, choix des variantes (ex. niveau du brevet) et textes à modifier avant l'import (contenu, police et taille ; ex. nom de la régate).
- Import dans l'éditeur vectoriel : découpe, gravure et marquage chacun sur son calque, textes modifiables ; le blanc n'est pas gravé (creusé dans la gravure).
- Convention des modèles (`resources/library/README.md`) : calques `Cut` (rouge), `Engrave` (noir) et `Mark` (bleu, facultatif) ; options en sous-calques d'un groupe, un seul visible, le nom du sous-calque étant celui de l'option.
- Premiers modèles : totems sportifs modèle 1 (pictogrammes Material Symbols) et modèle 2 (pictogrammes OpenMoji, CC BY-SA 4.0), titre et sous-titre à saisir, médailles sportives modèle 1 (aviron, basket-ball ou pictogrammes Material Symbols) et modèle 2 (pictogrammes OpenMoji, CC BY-SA 4.0) — hexagonales ou rondes, 1, 2, 3 ou étoile, nom de la compétition — boule de Noël avec prénom, et porte-clefs sportifs modèle 1 (aviron, basket-ball ou pictogrammes Material Symbols) et modèle 2 (pictogrammes OpenMoji, CC BY-SA 4.0).
- Import : dans `Engrave`, les traits sont gravés avec leur épaisseur (pictogrammes dessinés au trait).
- Polices embarquées (`resources/fonts/`, chargées au démarrage) : Dancing Script (police manuscrite) et Rubik (titres des médailles et des totems), sous licence OFL, disponibles sur tous les systèmes pour les textes des modèles.

Générateur de boîte :
- Aperçu en direct dans la fenêtre : les panneaux tels qu'ils seront découpés, avec les fentes de cloison et la position du décor, mis à jour à chaque réglage.
- Types de couvercle : à doigts (comme avant), posé avec rebord intérieur, coulissant (rainure dans les parois gauche et droite, façade abaissée), ou aucun (boîte ouverte).
- Cloisons : nombre réglable dans la largeur (X) et la profondeur (Y), compartiments égaux, languettes dans des fentes des parois et du fond, emboîtement à mi-hauteur quand elles se croisent.
- Jeu d'ajustement pour les assemblages libres (couvercle, rainure, cloisons), séparé du kerf.

### Modifié
Une seule fenêtre avant de graver : l'avertissement de sécurité, les points à vérifier (G-Code à régénérer, lignes à risque, graveur sans homing) et la question « Lancer la gravure ? » arrivent ensemble, au lieu de plusieurs fenêtres à la suite. Même chose pour « Reprendre ».

Les réussites ne bloquent plus l'écran : projet enregistré ou ouvert, G-Code exporté, SVG ou DXF importé, vectorisation exportée, générateur terminé, matériaux exportés ou importés, configuration GRBL envoyée s'affichent dans la barre d'état, sans fenêtre à fermer. Les erreurs et la fin d'une gravure gardent leur fenêtre.

Libellés harmonisés en français, anglais, allemand et espagnol : majuscule au premier mot seulement (« Temps estimé »), espace avant les deux-points en français (« Largeur (mm) : »), plus de mots anglais dans l'interface française (« Décalage X » au lieu de « Offset X », « Valeur S maximale » au lieu de « S-Max Value »). La fenêtre du générateur de puzzle, le menu de l'aperçu d'image et la commande laser de la matrice de test sont maintenant traduits.

La molette ne change plus une valeur par accident : sur un champ numérique, une liste ou un curseur qu'on n'a pas cliqué, elle fait défiler le panneau au lieu de modifier la puissance ou la vitesse au passage de la souris. Après un clic dans le champ, la molette le règle comme avant.

Visualisation 2D environ cinq fois plus rapide à dessiner sur une grosse image (1,2 s -> 0,23 s pour 500 000 lignes), image identique. La console se remplit d'un gros G-Code en tâche de fond, sans figer l'interface (lecture seule le temps du remplissage). Le panneau du bas démarre toujours replié : au lancement, le graveur n'est pas encore connecté.

Position du job réunie dans un seul cadre : l'ancrage de l'origine et le décalage (Offset X / Y) se règlent ensemble dans « Position du job sur le plateau », à droite de la Visualisation 2D, là où l'on voit le job sur le plateau ; le décalage n'est plus dans « Graver une image ». « Optimiser le chemin » quitte le cadre « Affichage » pour un cadre « Génération » : la case change l'ordre des tracés du G-Code généré, pas l'aperçu.

Visualisation 2D : le plateau de la machine est dessiné en pointillés, et la vue est cadrée dessus tant qu'aucun job n'est généré (au lieu d'axes de -1 à 1). Changer une option d'affichage (inverser, négatif, matière, déplacements rapides) redessine l'aperçu environ deux fois plus vite sur un gros job, et l'aperçu d'un job généré est préparé pendant la génération.

« Graver une image » sans image : une carte au centre invite à glisser-déposer un fichier ou à ouvrir une image, comme le canevas vide de l'éditeur vectoriel. La barre « Gravure : 0 % » du panneau du graveur n'apparaît plus que pendant un envoi. L'onglet « Calques (Layers) » s'appelle « Calques ».

Panneau du graveur : les boutons s'activent d'après l'état du graveur. Pendant une gravure ou un homing, seuls Pause, Reprise, Reset et Arrêt d'urgence restent actifs ; en alarme, le homing, le déverrouillage et la console restent disponibles, mais plus les déplacements ni l'envoi d'un job ; déconnecté, tout est grisé. Le bouton de connexion est grisé pendant une gravure. Un raccourci qui tente quand même une action dit pourquoi elle est refusée (graveur occupé, ou en alarme).

Génération du G-Code d'une image plus rapide : environ deux fois moins de temps pour une image en noir et blanc très détaillée (30 % de moins en niveaux de gris). Le G-Code produit ne change pas.

L'ancienne « découpe SVG » autour de l'image, qui n'était plus proposée mais revenait avec un ancien projet qui l'avait cochée, est supprimée : elle traçait au laser un trait entre deux contours d'un même chemin (un « O », une forme avec un trou). Les calques de découpe font ce travail.

Barre d'outils du haut allégée : les outils de l'éditeur vectoriel (bibliothèque, import, générateurs) restent dans l'éditeur et le menu Outils. « Visualisation 2D G-Code » suit la disposition des autres onglets : ses options d'affichage (matière, miroir, négatif, déplacements rapides, optimisation du chemin) passent dans un cadre « Affichage » de la colonne de droite, les loupes dans une barre verticale ; dans « Calques », la barre des actions devient verticale, à droite du tableau. Les aperçus des générateurs, le recadrage de l'image et le bouton de sortie du plein écran prennent les couleurs du thème.

Éditeur vectoriel : un bouton « Vectoriser une image » à côté d'« Importer SVG / DXF » ouvre l'onglet Vectorisation. Après un import, la vue se cadre sur le dessin importé sans trop zoomer sur un petit dessin ; dans « Graver une image », chaque nouvelle image remplit l'aperçu (rendu tramé comme originale), qui suit la taille de la fenêtre tant qu'on ne zoome pas soi-même.

Onglets à la manière de VS Code (thème New Dusk) : bande d'onglets, séparateurs fins, onglet actif de la couleur de la zone de travail, plus de petites flèches de défilement. « Séparation Couleur / Verre » et « Vectorisation d'image » ont une croix pour se refermer (le menu Outils les rouvre). Les panneaux latéraux (propriétés, listes de catégories) prennent la couleur de la barre latérale de VS Code. L'onglet Graveur du panneau du bas est plus compact (le bouton de connexion rejoint la ligne du port, boutons de déplacement un peu plus petits).

Panneau du bas, comme celui de VS Code : ses onglets Graveur (connexion, déplacements, lancement et suivi), Console G-Code et File d'attente restent sous les onglets de travail, sur tous les onglets. Replié, il ne montre que ses onglets ; il se déplie d'un clic sur l'un d'eux, avec **Ctrl+J**, par un clic sur la pastille du graveur de la barre d'état, et tout seul quand une gravure démarre ou qu'une alarme survient. La console G-Code et la file d'attente quittent les onglets principaux.

Éditeur vectoriel épuré : une seule barre flottante sur le canevas (la sélection en tête, puis créer et dessiner). La barre d'édition (avec l'imbrication automatique) passe à droite du canevas, contre la liste des objets ; l'alignement apparaît sous les propriétés dès que deux objets sont sélectionnés. Un canevas vide propose de gros boutons : importer un fichier, dessiner une forme, ouvrir la bibliothèque, vectoriser une image, et un par générateur (boîte, puzzle, boule de Noël, porte-clés).

Générateurs : la bibliothèque, la boîte, le puzzle, la boule de Noël et le porte-clés partagent une fenêtre, avec leur liste à gauche, les réglages au milieu et l'aperçu à droite. Le menu Outils l'ouvre sur le générateur choisi, l'icône « Générateurs » de la barre d'édition sur le dernier utilisé, Outils › Bibliothèque… et le bouton « Bibliothèque » de l'éditeur sur la bibliothèque. Le menu Affichage disparaît (Ctrl+J reste). Un seul couple de boutons « Importer » / « Annuler » sert aux quatre générateurs.

Thème New Dusk : les cases à cocher deviennent des interrupteurs.

Paramètres : une seule fenêtre pour tous les réglages, avec la liste des catégories à gauche (Paramètres du graveur, Configuration GRBL, Macros, Langue et thème). L'éditeur des macros y devient la page « Macros » (le bouton des actions de job l'ouvre) ; l'historique des gravures passe dans le menu Fichier. Elle s'ouvre par **Fichier › Paramètres…**, juste au-dessus de « Quitter » : le menu Paramètres disparaît.

Onglet « Graver une image » disposé comme l'éditeur vectoriel : le gros bouton vert « Charger Image » en haut (identique à « Importer SVG / DXF », qui annonce lui aussi le glisser-déposer), la barre d'outils verticale à droite de l'aperçu, et les propriétés de l'image à droite, affichées une fois l'image chargée.

Thème New Dusk : icônes d'une seule couleur, comme dans VS Code (les icônes à plusieurs teintes sont redessinées au trait).

Bibliothèque de modèles : les modèles sont importés comme avec le bouton « Importer » (calque d'après la couleur, groupes et textes gardés). Le blanc ne creuse plus la gravure : les pictogrammes en réserve des médailles, totems et porte-clés sont devenus de vraies Différences, et le texte « Compétition de XXXX » des médailles est un masque du bandeau, toujours remplaçable dans la fiche. Les options non choisies n'arrivent plus dans l'éditeur. Le marquage d'un modèle se dessine en vert.

Éditeur vectoriel : « Pivoter 90° » de la barre d'édition fait tourner tous les objets sélectionnés (avant : seulement le premier), comme le clic droit. « Texte le long d'un objet » du clic droit ouvre ensuite les réglages du texte, comme le bouton.

Import SVG : les arcs des tracés sont convertis en courbes exactes ; dans un fichier à petite unité (viewBox de 0 à 1), un cercle devenait un polygone grossier.

Import SVG : le cadrage du `viewBox` respecte `preserveAspectRatio` (centré sans déformation par défaut, comme les navigateurs) ; un document aux proportions différentes de son `viewBox` était étiré.

Opérations booléennes des groupes (union, différence…) : les courbes sont calculées au centième de millimètre (un cercle de 5 mm s'écartait de 0,1 mm).

Éditeur vectoriel : changer le calque d'un groupe le change pour tous les objets du groupe.

Barres d'outils flottantes : partout les mêmes icônes que dans l'éditeur vectoriel (annuler, refaire, pivoter, miroirs, supprimer…), et annuler / refaire puis les loupes toujours au bout, à droite.

Graver une image : « Algorithme de tramage » et « Afficher l'originale » passent dans une barre flottante à gauche de l'aperçu ; le bandeau au-dessus des aperçus disparaît, l'image gagne en hauteur.

Graveur simulé (`LASER_STUDIO_SIMULATION`) : dans l'historique des gravures, la durée réelle est multipliée par le facteur de vitesse de la simulation, pour être comparable à la durée estimée ; la gravure est marquée « simulation ×N ».

Durée estimée des gravures : calculée comme GRBL planifie ses déplacements, au lieu de « distance ÷ vitesse + 15 % ». Elle compte les déplacements rapides G0, l'accélération de chaque déplacement, le ralentissement dans les virages et aux demi-tours, et la limite du tampon de GRBL sur les images très fines. Elle utilise les réglages lus avec « Lire la config » ($110/$111, $120/$121, $11), sinon la vitesse maximale et l'accélération de « Paramètres du graveur ». L'estimation rapide (« Estimer ») compte aussi l'accélération à chaque ligne de l'image.

Marge de l'image et des dessins importés : au lieu de 10 mm fixes en X et en Y, la distance de surbalayage, en X seulement, quand il est activé (aucune marge sinon). Avec un décalage du job à 0, l'image démarre donc au bord gauche du plateau, surbalayage compris. Dans la Visualisation 2D, le fond de la matière ne déborde plus sous l'origine.

Éditeur vectoriel : quand il contient déjà des objets, un import (fichier SVG / DXF, bibliothèque, générateurs de boîte, de puzzle, de boule de Noël et de porte-clés, vectorisation, Stencil Studio) demande quoi faire du nouveau dessin : l'ajouter sans toucher aux objets, supprimer les objets présents, l'ajouter à leur droite ou au-dessus. Le puzzle garde sa position calée sur l'image, sauf à droite ou au-dessus. Ctrl+Z annule le tout d'un coup.

Stencil Studio : quand la détection du sujet par IA manque, le message propose la commande `dnf install` sous Fedora (Python du système), `pip install` ailleurs.

La case « Avec couvercle » devient une liste « Couvercle ». Les anciens réglages mémorisés restent lus.

Profils matériaux : plus de bouton « Enregistrer ». Le matériau choisi reprend aussitôt chaque modification d'un calque.

Modes des calques : enregistrés sous un code indépendant de la langue (`engrave_fill`, `cut`, `mark`) dans les projets, les profils machine et les commentaires du G-Code, au lieu du libellé français. Les anciens projets, profils et G-Code sont relus et convertis. Un projet enregistré avec cette version n'est plus lu correctement par une version antérieure (les modes y reviennent à « Découpe »).

Génération du G-Code : sortie des threads (`workers.py`) et de `vector_layers.py` dans un paquet `gcode/` sans Qt, testé seul. Le G-Code produit est identique, vérifié au caractère près sur 35 jobs (images binaires et en niveaux de gris, M3 / M4, surbalayage, décalage retour, découpe SVG, calques vectoriels, matrices de test, motif aller/retour).

Préparation du job (paramètres, contrôles avant génération, lancement, estimation, export et import du G-Code, matrice de test, motif aller/retour) : sortie de la fenêtre dans un contrôleur `JobController`, testé sans fenêtre. Les boîtes de dialogue passent par `UserDialogs`. Comportement inchangé.

Aperçu 2D : lecture du G-Code, choix image ou traits, fond de matière, image reconstituée et suivi de la gravure en direct dans un modèle sans Qt (`gcode/preview.py`), dessin dans l'onglet Visualisation 2D. La fenêtre perd le mixin `GcodeGenerationMixin`. Dessin identique, vérifié élément par élément sur 47 aperçus.

Graveur : connexion, pilotage, envoi des jobs et configuration GRBL sortis de la fenêtre dans un contrôleur `EngraverController` ; commandes GRBL rassemblées dans `grbl/commands.py` (sans Qt). La fenêtre perd le mixin `LaserControlMixin`. Comportement inchangé ; parcours complet testé avec le graveur simulé.

Contrôleurs (projet, matériaux, profils machine, file d'attente, matrice à partir d'une image, vectorisation, bibliothèque, caméra) : leurs boîtes de dialogue passent par `UserDialogs`, transmis par la fenêtre, au lieu d'ouvrir `QMessageBox` / `QFileDialog` / `QInputDialog` eux-mêmes. Mêmes questions, mêmes boutons ; les contrôleurs se testent sans fenêtre.

Éditeur vectoriel : `vector_layers.py` (4 300 lignes) découpé en modules, sans changer le code : objets du dessin (`models/vector_objects.py`), canevas et boîtes de saisie (`ui/vector_editor/`), tableau des calques (`ui/tabs/layers/layer_table.py`), import SVG classique (`vector/svg_extract.py`), conversion pour le G-Code (`vector/layer_data.py`). `vector_layers.py` réexporte tous les noms pour le code existant.

Éditeur vectoriel : la liste des objets, l'historique d'annulation et le presse-papiers sortent du canevas dans un modèle `VectorDocument` (`models/vector_document.py`), testable sans canevas ; grouper, dégrouper, exploser et convertir en tracé dans `vector/path_ops.py`. Le canevas devient une vue du document. Comportement inchangé.

Éditeur vectoriel : `vector_editing_mixin.py` remplacé par un contrôleur `VectorEditorController` (`controllers/vector_editor.py`) : import SVG / DXF, insertion et modification, alignement, imbrication, série, gabarit et générateurs agissent sur le document, avec des boîtes de dialogue simulables dans les tests. Panneau des propriétés dans `ui/vector_editor/properties_panel.py`, calculs d'alignement, de répartition et d'ancrage dans `vector/arrange.py`. Comportement inchangé, vérifié pas à pas sur 33 actions de l'éditeur.

Séparation couleur / verre : `separation_mixin.py` supprimé. L'ouverture, la rotation et le retrait de l'image, le rafraîchissement des aperçus et l'export passent dans `SeparationController`, avec des boîtes de dialogue simulables dans les tests ; l'onglet `SeparationTab` affiche lui-même aperçus, nom du fichier et résolution ; le test du gain de point rejoint `JobController`, à côté du motif aller/retour. Comportement inchangé, vérifié dans la fenêtre (chargement, aperçus, rotation, test du gain, export, suppression).

Graver une image : `image_processing_mixin.py` supprimé, la fenêtre n'hérite plus que de `WindowControllerMixin`. Le traitement et le tramage sortent de `workers.py` dans `image/dithering.py`, sans Qt (pixels identiques, vérifiés sur 144 traitements et 60 vignettes de comparaison) ; la grille du test du gain de point dans `image/gain_test.py`. Chargement, rotation, retrait, proportions, traitement dans un thread et comparaison des algorithmes passent dans un contrôleur `ImageController` ; la résolution (lignes/mm, DPI, focale) est tenue à jour par le cadre `ResolutionBox` lui-même, qui prend la focale transmise par les Paramètres Machine au lieu de la relire dans le modèle. Comportement inchangé, vérifié dans la fenêtre.

Fenêtre principale : `WindowControllerMixin` remplacé par des objets, la fenêtre n'hérite plus d'aucun mixin. Les onglets (affichage, onglets facultatifs du menu Affichage, plein écran, panneau du bas, séparateurs) passent dans `MainTabs` (`ui/app/tabs.py`), l'affichage des résultats du job et de l'état du graveur dans `JobDisplay` (`ui/app/job_display.py`), « Pivoter », « Supprimer » et les miroirs de la barre d'outils dans `ImageToolbarActions` (`ui/app/image_actions.py`) ; `WindowController` garde les menus, le thème, la langue, l'aide, la caméra, les fenêtres de réglages, la résolution et les outils de dessin. Ce qui s'enregistre et se restaure (réglages machine au démarrage et à la fermeture, champs d'un profil machine, état d'un projet, recopie des calques dans le matériau choisi) passe dans `WindowState` (`ui/app/window_state.py`). Les menus sont abonnés une fois toute la fenêtre construite. Comportement inchangé, vérifié dans la fenêtre (onglets, plein écran, panneau du bas, génération, barre d'outils de l'image, outils de dessin, réglages, focale, thème).

Stencil Studio : découpé comme Laser Studio en modèles (`models/` : photo et repères, réglages enregistrés), contrôleurs (`controllers/` : API de calcul, fenêtre dans Laser Studio) et interface (`ui/` : page web, fenêtre Qt, fenêtre séparée, couleurs) ; le serveur local est dans `server.py`, la police et le modèle de détourage dans `resources/`. Les réponses de l'API sont identiques (vérifié sur 38 requêtes). Le Studio n'importe plus rien de Laser Studio : il reçoit ses couleurs, sa langue et ses messages, et annonce ses exports. Seul, il se lance par `python -m stencil_studio`. Le rangement de ses exports dans les calques passe dans `controllers/stencil_import.py` côté Laser Studio, par le modèle des calques. Copies inutiles des traductions supprimées.

Fenêtre principale : déplacée dans `ui/app/main_window.py` et réduite à l'assemblage (1 077 → 466 lignes). Chaque partie de l'interface a son builder (`ui/…/builder.py`) qui crée la vue et sa logique et les relie, sans connaître la fenêtre. L'onglet de l'éditeur vectoriel devient une vue à part (`ui/vector_editor/tab.py`, `VectorEditorTab`), ses actions et le choix de l'outil de dessin passent par `VectorEditorController`. Les alias historiques des champs (`spin_w`, `chk_homing`, `txt_console`…) sont supprimés : on lit la page ou le modèle (`size_mm()`, `bind_settings()`, `ConsoleTab.gcode()`…). La zone de travail de l'éditeur suit directement le modèle de la machine. Comportement inchangé, vérifié dans la fenêtre.

Préférences : toutes les lectures et écritures des réglages mémorisés (thème, langue, onglets, séparateurs, projets récents, dernier port, profils machine, caméra…) passent par `core/preferences.py`, qui convertit les valeurs relues et écrit tout de suite. Les tests utilisent des préférences en mémoire au lieu de simuler QSettings. `grbl/` n'importe plus Qt, et un test vérifie qu'aucun dossier de calcul n'importe QtWidgets.

Tests : la vraie fenêtre est vérifiée hors écran par `tests/test_main_window.py` (onglets et plein écran, panneau du bas, outils de dessin, barre d'outils de l'image, génération et affichage du G-Code, résolution et focale, thème et langue, fermeture, projet, export de Stencil Studio), avec des préférences en mémoire.

Fondations : `vector_layers.py` (réexportations de l'ancien éditeur vectoriel) supprimé, chacun importe depuis le vrai module ; l'ancien nom `LayerManager` disparaît au profit de `LayersModel`. `workers.py` devient `controllers/workers.py`, sans ses réexportations. `WindowController` ne va plus chercher d'attributs de la fenêtre par leur nom : pages de réglages et onglets du menu Outils lui sont inscrits, la résolution est branchée sur la matrice de test et la Séparation à leur création.

Éditeur vectoriel : le canevas (`canvas.py`, 2 430 → 1 000 lignes) confie ses outils de la souris à des objets à part (`ui/vector_editor/tools/` : accroche, dessin, mesure, nœuds, déplacement, poignée du texte sur contour), qui gardent chacun leur état ; le menu du clic droit, le texte sur contour et les opérations sur une sélection groupée ont aussi leurs fichiers. Comportement inchangé, vérifié pas à pas sur 51 interactions souris et clavier et 30 opérations du document ; nouveaux tests avec de vrais événements souris et clavier.

Robustesse : les erreurs qui disparaissaient sans trace (sauvegarde automatique du projet et de la file d'attente, lecture de `$$`, clic sur la matrice de test, objets illisibles à l'annulation ou au collage, élément SVG illisible à l'import, aperçu de la bibliothèque…) sont écrites dans le journal de débogage ; les autres silences sont expliqués, et un test empêche les nouveaux `except Exception` muets. Les tests qui construisent la fenêtre n'écrivent plus dans les réglages de l'utilisateur.

### Corrigé
« Reprendre » après un arrêt d'urgence : le bouton restait grisé sans explication, car le graveur passe en alarme. Il reste cliquable et explique qu'il faut d'abord faire un homing ou déverrouiller ($X) ; ensuite, la reprise repart au point exact de l'arrêt. Le bouton vert de reprise (F8), qu'on cherche naturellement après un arrêt, relance aussi le travail interrompu (il n'envoyait que la reprise après pause, sans effet). La fenêtre « Job interrompu » l'indique, sans l'icône ⏩ que sa police n'affichait pas. À la reprise, la Visualisation 2D garde le job entier et le tracé rouge déjà gravé, qui continue d'avancer (elle n'affichait plus que le reste du job, mal rendu).

Éditeur vectoriel : changer la taille du plateau (autre profil machine, Paramètres du graveur) laissait les objets dessinés au mauvais endroit, décalés en hauteur, jusqu'au prochain redessin ; ils restent maintenant à leur place sur le plateau.

Sécurité : un G-Code (fichier d'un autre logiciel, console retouchée) qui modifierait la configuration du graveur ($130=…, $RST=*, $N0=…) ou demanderait une puissance au-delà du S-Max n'est envoyé ou ajouté à la file qu'après confirmation, lignes en cause affichées. Un projet dont l'image dépasse 89 millions de pixels est refusé avant d'être décodé, au lieu de saturer la mémoire. F7 et F8 (pause, reprise) sont sans effet graveur déconnecté.

Éditeur vectoriel : le bouton « Fond caméra » a de nouveau son icône (elle manquait dans les icônes livrées avec l'application, comme celle du menu Caméra).

Visualisation 2D pendant une gravure : le tracé « déjà gravé » ne prend plus d'avance sur le laser quand le G-Code (importé ou retouché dans la console) contient des commentaires indentés ou des lignes qui ne sont pas du G-Code ; l'aperçu compte les lignes comme l'envoi au graveur.

Pendant une gravure, plus rien ne peut s'intercaler dans l'envoi : « Envoyer au laser » pendant la file d'attente, « Répéter », les flèches de déplacement, la console, le cadrage, le homing ou la lecture des réglages $$ sont refusés avec le message « Graveur occupé ». Avant, une commande glissée au milieu d'un job pouvait l'arrêter net (position perdue), et un second envoi mélangeait ses lignes avec celles du premier.

Le homing n'est compté comme fait qu'une fois réussi : s'il finit en alarme (fin de course non atteinte), s'il est refusé ou s'il n'a pas pu partir, l'avertissement « machine non référencée » réapparaît avant la gravure.

Éditeur vectoriel : la liste « Calque » des propriétés n'est plus coupée ; le bouton « Connecter GRBL » non plus.

Thème New Dusk : le texte de la barre d'avancement de la gravure (« Gravure : 42 % ») n'est plus rogné.

Thèmes : les flèches des champs numériques s'affichaient en petits carrés ; ce sont maintenant des chevrons à la couleur du thème. Les boutons « Générer le G-code » et « Importer SVG / DXF » prennent les couleurs du thème (le second n'est plus vert).

Gravure saccadée : la tête ne s'arrête plus à chaque allumage du laser. Le G-Code envoyait la puissance sur des lignes à part (« M4 S500 », « S0 », « M5 » autour de chaque segment ou de chaque contour), et GRBL vide son tampon de mouvements à chaque ligne de ce genre : la tête marquait un temps d'arrêt à chaque allumage et à chaque extinction, et la gravure durait bien plus que la durée estimée (calques vectoriels, découpe, matrice de test, image en M3). La puissance voyage maintenant sur chaque mouvement, la commande laser n'est envoyée qu'une fois et M5 à la fin. Le G-Code est aussi plus compact (mots inchangés non répétés, nombres sans zéros inutiles, espaces et commentaires non envoyés) : deux à trois fois moins d'octets sur la liaison série, qui n'est plus en retard sur la gravure dans les zones denses d'une image. Ce qui est gravé ne change pas.

Configuration GRBL : seuls les réglages numériques ($110=6000…) sont importés et envoyés à la carte, sans leur commentaire. Un fichier de réglages ne peut plus effacer la configuration ($RST=*), ajouter une ligne exécutée au démarrage de la carte ($N0=…, qui pouvait allumer le laser), déplacer la tête ($J=…) ni la mettre en veille.

Stencil Studio : son serveur local n'accepte plus que sa propre page (nom d'hôte et jeton vérifiés). Un site web ouvert dans un navigateur pendant que Laser Studio Pro tourne pouvait effacer les préréglages du Studio ou lire l'image chargée.

Récupération après plantage : si la sauvegarde automatique ne peut pas être ouverte, elle est gardée pour un nouvel essai (elle était supprimée).

Générateur de boîte : un décor SVG est lu comme par « Importer » (transformations des groupes, cadrage du `viewBox`, unités ; éléments cachés et contenu de `<defs>` écartés). Un SVG d'Inkscape dont les calques sont décalés arrivait en morceaux mal placés.

Préréglages du générateur de boîte : enregistrés sans risque de perte (un disque plein ou un arrêt en cours d'écriture laisse l'ancien fichier intact).

Stencil Studio : le modèle de détourage téléchargé est vérifié (empreinte SHA-256) ; un fichier corrompu n'est plus gardé en cache, ce qui bloquait la détection du sujet pour de bon.

Durées estimées : une seule présentation partout (« 46 s », « 3 min 12 s », « 2 h 05 min », unités traduites), avec des heures au-delà d'une heure. La matrice de test et le motif aller/retour ajoutent maintenant la même marge de 15 % (accélérations) que les jobs ; l'estimation rapide (« Estimer ») reste sans marge (#119).

Puissance des matrices de test et de la découpe SVG autour de l'image : arrondie au plus proche, comme partout ailleurs. Avec S-Max = 255, une case à 10 % grave en S26, comme un calque réglé à 10 % (elle gravait en S25). La découpe SVG autour de l'image suit la commande laser (M3 / M4) du calque de découpe, sinon celle de la Configuration GRBL, comme les calques vectoriels : elle envoyait toujours M3 (#118).

Macros : le bouton « Macros… » du panneau des actions de job reste actif graveur déconnecté (on prépare ses macros sans graveur branché) ; dans l'éditeur, les boutons de la liste sont en colonne et leurs libellés lisibles en entier.

Envoi d'un job : une réponse « ERROR: » (renvoyée par certains clones de GRBL) arrivant pendant l'attente des derniers « ok » arrête maintenant la machine, comme pendant le reste de l'envoi ; elle était ignorée.

Titre de la fenêtre principale traduit (il restait en anglais quelle que soit la langue).

Stencil Studio : l'autotest (`selftest.py`) échouait. Ses tests de séparation par couleur dataient d'avant le passage automatique aux tons pour les photos ombrées et d'avant la règle « le nombre de plaques demandé est toujours respecté » avec la pipette ; ils utilisent maintenant une image en aplats, comparent les couleurs avec une tolérance, et vérifient aussi ces deux règles. Il est lancé par la suite de tests (`tests/test_stencil_selftest.py`).

Stencil Studio : les calques créés pour un pochoir multicouche (`LAYER_n`) n'apparaissaient pas tout de suite dans l'onglet Calques et n'étaient pas mémorisés dans le profil de la machine : ils passent maintenant par le modèle des calques. Le message « Chargement de Stencil Studio… » suit la langue de l'application (il restait en français). La fenêtre séparée (repli quand le moteur web ne peut pas être chargé) affiche bien la page.

Caméra : le fond de l'éditeur vectoriel est de nouveau redressé sur tout le plateau (l'image apparaissait minuscule et déplacée : la projection `warp_to_bed` utilisait la matrice dans le mauvais sens).

Stencil Studio : quand l'import d'un fichier exporté vers Laser Studio échouait (aucun calque, fichier illisible…), l'import standard prévu en secours plantait lui aussi, et le fichier n'arrivait jamais dans l'éditeur vectoriel. Il passe maintenant par l'import de l'éditeur vectoriel, qui explique le problème.

Gravure remplie des calques vectoriels avec surbalayage : entre deux lettres proches (ou deux objets séparés de moins de deux fois le surbalayage), la tête dépassait la lettre puis revenait en arrière pour reprendre son élan avant la suivante. La ligne est maintenant gravée d'une traite, laser éteint entre les lettres, avec le surbalayage aux deux bouts seulement (comme la gravure d'image). Les zones gravées sont inchangées.
La gravure d'une image utilisait parfois une ancienne puissance (30 %) au lieu de celle du calque de gravure, après un changement de profil machine.

Installation et compilation :
- numpy 2 (au lieu de numpy 1.26) : l'application s'installe avec Python 3.10 à 3.14, donc avec le Python fourni par les distributions récentes (Debian 13, Fedora 41+, Ubuntu 25.04+), sans installer Python 3.12 à côté.
- OpenCV sans interface graphique (`opencv-python-headless`) et fichiers Qt inutilisés retirés de l'exécutable : environ 170 Mo de moins une fois installé.

## [2.5.0] — 2026-11-01

### Ajouté
Stencil Studio : intégration d'un nouvel espace de travail complet dédié à la création et à l'optimisation de pochoirs et de designs vectoriels et matriciels avancés :

Trame par point et par ligne : conversion artistique de vos images en motifs de points ou de lignes tramés prêts pour la gravure.

Effet Low Poly : transformation géométrique automatisée d'images en polygones pour des rendus modernes et stylés.

Générateur de boîte complète avec éclairage : conception automatisée de boîtiers sur mesure intégrant des logements et passages optimisés pour l'éclairage LED, les alimentations et l'assemblage par encoches.

Outils de personnalisation et d'export direct vers le flux de travail de Laser Studio Pro.

Accès direct Stencil Studio : ajout d'un bouton dédié dans la barre de menus principale pour un lancement instantané de l'outil.

### Modifié
Interface et Navigation : réorganisation de la barre de menus pour intégrer harmonieusement les accès rapides aux différents studios et outils de configuration.

## [2.4.0] — 2026-10-20

### Ajouté
- **Imbrication automatique (nesting)** : le bouton « 🧩 Imbrication auto » de l'éditeur vectoriel range les pièces sélectionnées (ou tous les objets des calques actifs) sur une feuille aux dimensions voulues pour gaspiller le moins de matière possible. Les pièces sont placées de la plus grande à la plus petite, en bas à gauche d'abord, avec la forme réelle des contours (une petite pièce se glisse dans le creux d'un « L ») ; rotations au choix (aucune, 0°/90°, par quarts de tour, tous les 45°), écart entre pièces, marge au bord de la feuille et précision de la grille réglables. Un trou ou un détail gravé reste avec sa pièce et tourne avec elle (regroupement par inclusion). Les pièces qui n'ont pas trouvé de place restent où elles sont et sont comptées. Annulable avec Ctrl+Z. Mesuré : 40 pièces sur 400 x 400 mm en moins d'une seconde à la précision normale.
- **Ordre de découpe sûr** (réglage « Configuration GRBL », activé par défaut, enregistré dans le projet) : les calques de gravure et de marquage passent avant les calques de découpe, et dans un calque de découpe les contours intérieurs (trous, détails) sont coupés avant ceux qui les contiennent. La pièce ne bouge ni ne bascule avant que ses détails soient faits. Décoché, le G-Code reste strictement identique à celui des versions précédentes.
- **Netteté dans les réglages photo** (Image / Filtres, après le gamma) : accentuation des contours avant le tramage (0 à 100), proportionnelle à la résolution de gravure, prise en compte par l'annulation, le projet, la comparaison des algorithmes de tramage et l'onglet Séparation. À 0, le résultat est identique à avant.
- **Tests** : ordre de découpe, imbrication (aucune collision, espacement et marges, rotations, emboîtement dans les creux, groupes rigides), netteté, et un contrôle qui détecte tout nom utilisé sans être importé. La suite compte 329 tests.

### Modifié
- **Menus** : « Paramètres Machine », « Machine & Profils », « Configuration GRBL » et « Matrice de test » sont dans la barre de menus, dans cet ordre, entre « Fichier » et « Langue ». Chacun ouvre une fenêtre non modale dont la taille et la position sont mémorisées ; le bouton « Enregistrer comme focale machine » ouvre la fenêtre « Paramètres Machine ». La colonne de gauche ne garde que Image / Filtres, Dimensions & Origine et Calques.
- **Homing automatique** : coché d'office dans « Configuration GRBL ».
- **Image insérée à sa taille d'origine** (et non plus à 100 mm d'office) : d'après la résolution enregistrée dans le fichier (PNG, JPEG...), 96 DPI à défaut ; réduite, proportions conservées, si elle dépasse la zone de travail de la machine (un message l'indique dans la console).
- **Éditeur vectoriel : flèches du clavier** pour déplacer la sélection de 1 mm (Maj : 10 mm ; Alt : 0,1 mm), objets groupés ensemble ; une touche maintenue ne compte que pour un « Annuler ». Sans sélection, les flèches font défiler la vue comme avant.

### Corrigé
- **Gravure vectorielle en remplissage : zones non gravées aux croisements.** Tous les contours d'un calque étaient mélangés dans une seule règle « pair-impair » : deux objets qui se chevauchent (traits qui se croisent, lettres rapprochées, formes superposées) s'annulaient là où ils se recouvrent et laissaient un vide. Chaque objet garde maintenant sa propre règle (ses trous sont conservés), puis les objets sont réunis.
- **Gravure vectorielle en remplissage : contours en escalier et petits traits cassés.** Le décalage aller/retour (Configuration GRBL) ne s'appliquait qu'aux images : les lignes de remplissage parcourues en sens retour restaient décalées de deux fois le retard du laser. Il s'applique maintenant aussi au remplissage vectoriel ; règle-le avec le test aller/retour. À 0, le G-Code est inchangé.

### Migration
- Aucun format n'est cassé : la netteté vaut 0 et l'ordre de découpe sûr est activé par défaut pour les anciens projets (voir la note ci-dessus : décoche-le pour retrouver l'ancien ordre exact).

Fichiers modifiés :
app_utils.py, workers.py, image_processing_mixin.py, ui_setup_mixin.py, project_io_mixin.py, gcode_generation_mixin.py,
vector_layers.py (remplissage, flèches), vector_editing_mixin.py, settings_window.py, i18n.py — nouveaux modules : image_filters.py, image_size.py, vector_order.py, vector_nudge.py, nesting.py,
nesting_apply.py, nesting_dialog.py — nouveaux tests : tests/

## [2.3.0] — 2026-10-11

### Ajouté
- **Import DXF dans l'éditeur vectoriel** : le bouton « Importer SVG / DXF » (et le glisser-déposer d'un fichier `.svg` ou `.dxf` sur la fenêtre) accepte maintenant les DXF texte (ASCII). Lecteur intégré, sans dépendance : lignes, polylignes (avec arrondis), cercles, arcs, ellipses, splines, et blocs (`INSERT`, imbriqués, avec rotation, échelle, symétrie et réseaux). Les unités du fichier (`$INSUNITS`) sont converties en mm. Les lignes séparées qui se touchent sont réunies en contours (fermés si le contour se referme), ce qui permet de graver en remplissage ou de découper proprement. Chaque tracé devient un objet indépendant sur le calque par défaut. Les éléments non gérés (textes, hachures, cotes…) sont ignorés et listés après l'import ; les DXF binaires sont refusés avec un message explicite.
- **Générateur de boîte à encoches** (bouton « 📦 Générateur de boîte » de l'éditeur vectoriel) : dimensions X, Y, Z extérieures ou intérieures, épaisseur du matériau, compensation du trait (kerf), largeur de doigt, couvercle ou boîte ouverte, espace entre les pièces. Crée les panneaux sur le calque de découpe, disposés sur la zone de travail, et un décor optionnel (texte ou fichier SVG, taille, position) gravé sur les faces de ton choix. Les panneaux s'emboîtent sans chevauchement ni trou, vérifié en 3D pour de nombreuses combinaisons de dimensions. Annulable avec Ctrl+Z. La fenêtre défile sur les écrans peu hauts : le résumé et les boutons Valider / Annuler restent toujours visibles en bas.
- **Décalage aller/retour** (Paramètres G-Code, à côté du surbalayage) : la mécanique et le délai d'allumage du laser font que les lignes gravées en balayage retour tombent à côté de celles de l'aller, ce qui rend les contours verticaux flous. Un réglage en mm (-2,00 à +2,00) décale les lignes retour ; il est mémorisé dans le profil de la machine active.
  Le bouton **« Générer le test aller/retour »** crée un motif de 17 colonnes numérotées (de -0,40 à +0,40 mm, par pas de 0,05) : la colonne au bord le plus droit donne la valeur à saisir. Réglé à 0, le G-Code est strictement identique à celui des versions précédentes.
- **Assistant de calibrage du gain de point** (onglet Séparation Couleur / Verre, bouton « Tester le gain de point… ») : génère une grille à graver sur le verre, avec une ligne par valeur du curseur « Gain de point » (0, 5, 10, 15, 20) et 11 colonnes de 0 % (peinture intacte) à 100 % (verre dégagé), à la résolution, vitesse et puissance actuelles et en miroir si le miroir est actif. On repère la ligne dont les cases passent régulièrement du noir au clair et on règle le curseur dessus.
- **Tests automatiques** : fin de job (faux GRBL), moteur de séparation (recadrage, gain de point, calque couleur, simulation du rétro-éclairage, PDF 1:1), écrivain de fichiers en arrière-plan, autosave, décalage aller/retour et motifs de calibrage, registre tu/vous des traductions. La suite compte 245 tests.

- **Outil `tools/check_ui_attributes.py`** : détecte un widget ou une méthode privée utilisé dans un fichier mais construit dans aucun (typiquement un `ui_setup_mixin.py` resté à l'ancienne version alors que `image_processing_mixin.py` a été mis à jour : `AttributeError` au moment où la ligne est atteinte). Un test le lance sur tout le projet.

### Modifié
- **« Machine & Profils » et « Configuration GRBL »** : ces deux réglages, propres à la machine, quittent la colonne de gauche et passent dans la barre de menus, entre « Fichier » et « Langue ». Un clic ouvre une fenêtre non modale (la fenêtre reste ouverte pendant que tu travailles) dont la taille et la position sont mémorisées. Les messages d'avertissement sur le surbalayage parlent désormais du menu « Configuration GRBL » au lieu d'un onglet.
- **Barre d'outils de l'éditeur vectoriel sur deux lignes** : « + Texte », « + Forme », « Importer SVG / DXF », « Générateur de boîte » et « Plein écran » en haut ; « Modifier sélection », « Pivoter », « Dupliquer », « Supprimer », « Annuler » et « Refaire » dessous. Les libellés ne sont plus tronqués (une seule ligne de 11 boutons demandait environ 1 500 px).
- **Bouton « Générer le G-Code »** : hauteur réduite (marge intérieure de 3 px au lieu de 10 px).
- **Fin de job** : l'application n'annonce « terminé » qu'une fois GRBL revenu à l'état Idle (GRBL répond « ok » dès qu'il a accepté une ligne, pas quand le mouvement est fini). Tant que la machine est en mouvement, l'attente n'a pas de limite ; une alarme, une absence de réponse de GRBL (8 s) ou un arrêt demandé la terminent comme non propre. Les erreurs GRBL reçues en fin de job sont consignées dans la console.
- **Sauvegardes hors du fil de l'interface** : l'encodage PNG de l'image, le JSON et l'écriture disque de l'autosave et de la file d'attente se font dans un thread à part (mesuré : environ 0,6 s pour une image de 3000 px et 1,3 s à 5000 px ; jusqu'à 0,4 s à chaque modification d'une file de 60 Mo). L'application attend la fin des écritures à la fermeture, et un échec (disque plein…) est signalé une fois dans la console au lieu d'être ignoré.
- **Traductions** : les boîtes de dialogue de l'éditeur vectoriel (Redimensionner, Modifier le texte, Insérer une forme : 28 textes) suivent maintenant la langue choisie ; le tutoiement est harmonisé en français, allemand et espagnol (38 textes), avec un test qui empêche le retour du vouvoiement.

### Corrigé
- **Largeur de la colonne de gauche** : deux causes empêchaient de régler sa largeur avec le séparateur. (1) La liste « Matière » (Image / Filtres) imposait la largeur de son libellé le plus long (62 caractères en français, 85 en allemand) : elle a maintenant une largeur minimale courte, sa liste ouverte reste assez large pour tout lire, et un test signale toute liste à textes longs sans réglage de taille. (2) Le centre n'avait pas de largeur minimale explicite : la barre d'outils de l'éditeur vectoriel (11 boutons, environ 1 500 px) lui imposait une très grande largeur minimale, et la colonne de gauche ne pouvait plus être élargie. Le centre a maintenant une largeur minimale de 480 px ; plus étroit, il serre simplement ses boutons.
- **Arrêt pendant un job** : un Reset ou un Arrêt d'urgence était rapporté comme une fin normale (message « Terminé », et la file d'attente enchaînait sur le job suivant). C'est désormais une interruption.
- **Port fermé en fin d'envoi** : une liaison perdue pendant l'attente des derniers « ok » n'est plus rapportée comme une fin propre.
- **Surbalayage en pourcentage** : le mode « Pourcentage » n'était pas reconnu en anglais, allemand et espagnol (la distance fixe était utilisée à la place). Il l'est dans toutes les langues.

- **Résolution de gravure de l'onglet Séparation** : le libellé « Résolution de gravure : … DPI » restait figé sur 254 DPI (valeur par défaut) dès qu'on réglait la résolution en DPI ou d'après la focale, car ces deux modes modifient le champ lignes/mm sans émettre de signal. Il suit maintenant toujours Image & Filtres, y compris au démarrage, et la tonalité de l'image chargée est renvoyée quand la résolution change.
- **Changement de machine** : les réglages de calques de la nouvelle machine pouvaient être remplacés par ceux de l'ancienne juste avant d'être appliqués (des signaux émis pendant le changement de focale déclenchaient l'enregistrement). Les calques du profil sont maintenant lus avant tout changement, et l'enregistrement automatique est suspendu pendant l'opération.

### Migration
- Aucun format n'est cassé : le décalage aller/retour vaut 0 par défaut et les anciens profils machine, projets et files d'attente se chargent comme avant.

Fichiers modifiés :
app_utils.py, workers.py, gcode_generation_mixin.py, ui_setup_mixin.py, machine_profiles_mixin.py,
separation_mixin.py, project_io_mixin.py, job_queue_mixin.py, vector_layers.py, vector_editing_mixin.py, i18n.py —
nouveaux modules : dxf_import.py, vector_import.py, box_generator.py, box_dialog.py, settings_window.py — nouveaux tests : tests/

## [2.2.0] — 2026-10-04

### Ajouté
- **Image / Filtres — sélecteur « Matière »** : liste placée juste au-dessus de « Inverser Couleurs ».
  « Fond noir » (aluminium anodisé, verre peint, ardoise, acrylique noir : le laser éclaircit ce qu'il brûle) active l'inversion ; « Fond clair » (bois, carton, cuir : le laser noircit ce qu'il brûle) la désactive.
  Le sélecteur ne fait que cocher/décocher « Inverser Couleurs » : la case reste modifiable à la main et le miroir reste indépendant.
  Le choix est enregistré dans le projet (un ancien projet le déduit de son inversion), pris en compte par Annuler/Rétablir, et remis sur « fond clair » par la réinitialisation des réglages image.
  L'alerte de confirmation avant gravure d'une image rappelle la matière, par exemple « Matière : fond noir (négatif activé) » ; elle reflète l'état réel de la case et signale donc une incohérence. Traduit en FR / EN / DE / ES.
- **Calques — réglages mémorisés par machine** : mode, puissance, vitesse, passes, pas de remplissage (et son lien à la focale) et état actif de chaque calque sont rangés dans le profil de la machine active.
  Enregistrement 0,6 s après chaque modification et à la fermeture (donc aussi après un plantage) ; restauration complète des calques au démarrage (noms, couleurs, calques ajoutés).
  En changeant de machine en cours de session, seuls les réglages de l'autre machine sont appliqués, aux calques existants (par identifiant puis par position) : aucun calque n'est ajouté, supprimé ni renommé, pour que les objets du canevas restent rattachés à leur calque. « Nouvelle machine » et « Mettre à jour » incluent les calques. Les anciens profils sans calques mémorisés ne changent rien.
- **Onglet « Séparation Couleur / Verre »** : à partir d'une image couleur, produit le calque noir à graver (tonalité envoyée à Image / Filtres, qui applique luminosité, contraste, gamma, tramage et résolution), le calque couleur à imprimer à la même taille physique, une simulation du rétro-éclairage, et un PDF A4 à l'échelle 1:1 avec repères de coin. Réglages : recadrage, gain de point, miroir à l'impression.
  À l'import, les réglages « verre » (matière fond noir, négatif, miroir horizontal) sont appliqués puis restitués au chargement d'une image classique.
- **Tests automatiques** (dossier `tests/`, `python -m unittest discover tests -v`) : génération du G-code d'image rejouée comme GRBL, écriture atomique, reset/référencement, mémorisation des calques par machine, contrôle des traductions.
- **Outil `tools/check_translations.py`** : rapport sur les clés jamais utilisées, les textes d'interface écrits en dur, les valeurs identiques entre langues et le mélange tutoiement/vouvoiement.

### Modifié
- **Éditeur vectoriel — vue** : la vue se cadre et se centre automatiquement sur le SVG importé (import SVG et PNG → SVG) ainsi qu'à l'entrée et à la sortie du plein écran. Le zoom s'ajuste à l'objet (plafonné pour les très petits objets).
- **Interface — panneau du bas** : le panneau Position machine / Jog / Commandes / Console GRBL n'est affiché que dans « Visualisation 2D G-Code », « Console / G-Code » et « File d'attente ». Il reste visible tant qu'un job est en cours, quel que soit l'onglet (Pause, Reset et Arrêt d'urgence toujours accessibles). Sa hauteur réglée est mémorisée.
- **RESET / ARRÊT D'URGENCE** : les deux boutons passent par une seule fonction commune.
- **Traductions** : message de fin de file d'attente et description de la fenêtre « À propos » désormais traduits ; deux clés définies en double dans `i18n.py` supprimées.

### Corrigé
- **Gravure d'image — puissance appliquée au mauvais segment** : à chaque changement de puissance, le G-code envoyait le déplacement jusqu'à la frontière avec la puissance du segment *suivant* (GRBL applique le `S` d'une ligne à son propre déplacement). Une ligne sur deux, les zones à conserver étaient gravées et celles à graver épargnées ; en balayage retour (droite → gauche), la frontière était en plus décalée d'un pixel (motif en peigne). Corrigé et couvert par un test qui rejoue le G-code.
- **Reset / Arrêt d'urgence en mouvement** : GRBL perd sa position lorsqu'il est réinitialisé alors que la machine bouge. Le statut « référencé » est maintenant retiré (un message l'indique dans la console) et un nouveau homing est demandé avant le job suivant. Un reset fait machine à l'arrêt ne change rien.
- **Sauvegardes** : l'autosave, la file d'attente et la sauvegarde manuelle du projet s'écrivent maintenant de façon atomique (fichier temporaire puis remplacement) ; un plantage, une coupure ou un disque plein en cours d'écriture ne laisse plus un fichier tronqué.
- **Chargement de projet** : l'état mémorisé par l'onglet Séparation est réinitialisé ; charger ensuite une image dans Images / Tramage ne remet plus à tort l'ancien négatif, miroir et matière par-dessus ceux du projet.
- **Homing (`$H`)** : la réponse n'est plus coupée au bout de 2 s pendant que la machine se déplace (délai porté à 90 s pour les commandes `$H…`).
- **File d'attente** : noms de jobs désormais uniques (deux jobs ajoutés dans la même seconde empêchaient de sauvegarder le nouvel ordre après un glisser-déposer) ; la barre de progression ne divise plus par zéro.
- **Console GRBL** : la flèche Bas n'efface plus ce que tu es en train de taper.
- **Interface** : un libellé à masquage automatique sans parent ne s'affiche plus comme une fenêtre isolée avant sa mise en page.
- **Aperçu 2D** : quand « Aperçu en négatif » est décoché, la gravure noire était illisible sur le fond sombre. Elle est maintenant simulée sur un fond clair (matériau), avec les découpes et contours toujours visibles par-dessus.

### Migration
- Aucun format n'est cassé : les projets, profils machine et files d'attente existants se chargent normalement (les clés ajoutées, `material_bg` et `layers`, ont une valeur de repli).
- Au premier lancement, les calques gardent leurs valeurs par défaut jusqu'à la première fermeture de l'application (les profils existants n'ont pas encore de calques mémorisés).
- Les G-codes d'image générés avec une version antérieure sont à régénérer (voir la correction de la puissance par segment).

Fichiers modifiés :
app_utils.py, workers.py, image_processing_mixin.py, ui_setup_mixin.py, project_io_mixin.py,
gcode_generation_mixin.py, laser_control_mixin.py, job_queue_mixin.py, machine_profiles_mixin.py,
usb_controller.py, widgets_extra.py, separation_mixin.py, i18n.py — nouveaux : tests/, tools/

## [2.1.0] — 2026-09-28

### Ajouté
- **Éditeur vectoriel — sélection multiple** : Ctrl + clic gauche ajoute un objet à la sélection (ou le retire s'il y est déjà). Le déplacement groupé fonctionne ensuite sur tout le groupe.
- **Éditeur vectoriel — regroupement** : clic droit → « Regrouper en un seul objet » (ou Ctrl+G) fusionne les objets sélectionnés en un seul tracé, à leur position exacte, déplaçable et redimensionnable d'un bloc. Annulable avec Ctrl+Z.
- **Calques — ordre modifiable** : boutons « ▲ Monter » / « ▼ Descendre ». L'ordre de la liste est l'ordre d'exécution des calques dans le G-Code (ex. gravure avant découpe).
- **Onglet Machine — aide aux drivers USB** : indication discrète avec liens officiels pour installer le driver du contrôleur (CH340, CP210x, FTDI) et rappel Linux (groupe `dialout`). Traduit en FR / EN / DE / ES.
- **Aperçu 2D — bouton de soutien** : petit bouton (logo) dans la barre d'outils, ouvre la page Ko-fi dans le navigateur. Nouvelle ressource `buy_me_a_coffee.png` à embarquer dans le build (`--add-data`).

### Modifié
- **Matrice de test (gravure)** : le champ « Lignes/mm » reprend automatiquement la valeur de l'onglet Image / Filtres (champ grisé, mise à jour en direct, quel que soit le mode de saisie : lignes/mm, DPI ou focale).
- **Image / Filtres** : la ligne « Écart : … » n'est plus affichée que pour signaler un réglage trop fin (< 0,9× la focale, risque de surgravure) ; masquée quand l'écart est correct ou recommandé.

### Corrigé
- **Matrice de test** : le champ « Puissance Min » (gravure) / « Puissance Unique » (découpe) existait mais n'était jamais affiché dans le formulaire.
- **Éditeur vectoriel** : Ctrl + clic n'ajoutait pas l'objet cliqué à la sélection existante.
- **Interface** : espace vide sous le bouton « Générer le G-Code » (les libellés de progression de génération se masquent maintenant quand ils sont vides ; même correction dans les deux autres onglets concernés).

### Build
- Ajouter `--add-data "buy_me_a_coffee.png;."` (Windows) / `--add-data "buy_me_a_coffee.png:."` (Linux) aux commandes PyInstaller.
- Supprimer `build/`, `dist/` et `LaserStudioPro.spec` avant de rebuilder, pour que le nouveau fichier de ressource soit bien pris en compte.

## [V2.0.0]

feat: Éditeur Vectoriel (redo/alignement/accroche), file d'attente persistante, GRBL complet, matériaux par machine, JPEG (v2.0.0)

## Ajouté :
- Éditeur Vectoriel : vrai Refaire (Ctrl+Y), alignement multi-objets
  (gauche/centre/droite, haut/milieu/bas) et distribution avec espacement
  égal (dès 3 objets, extrémités fixes), accroche à la grille pendant un
  déplacement (pas réglable en mm, préserve l'agencement relatif d'une
  sélection multiple en n'accrochant que l'objet réellement cliqué).
- File d'attente : réordonnancement des jobs par glisser-déposer, et
  persistance complète entre deux sessions (sauvegardée à chaque
  modification, restaurée au démarrage).
- Profils machine : import/export complet des réglages GRBL ($$) —
  lecture depuis la machine, envoi (avec confirmation, écrit en EEPROM),
  export/import en fichier texte ; capturés automatiquement par "Nouvelle
  Machine"/"Mettre à jour" comme le reste du profil.
- Base de matériaux (`materials_db`) propre à chaque profil machine —
  une nouvelle machine hérite de la liste active à sa création,
  personnalisable ensuite sans affecter les autres profils.
- Onglet PNG/JPEG → SVG (renommé) : accepte maintenant le JPEG en plus
  du PNG (le pipeline de conversion le gérait déjà nativement), glisser-
  déposer direct d'un fichier, et collage presse-papiers (Ctrl+V,
  pratique pour une capture d'écran).
- app_utils.py : nouvelle fonction get_autosave_dir() — dossier
  utilisateur toujours accessible en écriture (~/.local/share sous
  Linux, %APPDATA% sous Windows) pour l'autosave de projet et la file
  d'attente, plutôt que le dossier de l'exécutable (pouvait être en
  lecture seule une fois installé).

## Corrigé :
- Plantage au lancement (ImportError: get_autosave_dir) sur une
  installation où project_io_mixin.py avait déjà été mis à jour pour
  utiliser ce nouveau dossier utilisateur, sans que la fonction existe
  encore côté app_utils.py.

Fichiers modifiés :
app_utils.py, vector_layers.py, vector_editing_mixin.py, ui_setup_mixin.py,
i18n.py, job_queue_mixin.py, main_window.py, laser_control_mixin.py,
machine_profiles_mixin.py, png2svg_widget.py, project_io_mixin.py

## [1.7.0] - 2026-09-21

## Ajouté

Puissance minimum réglable dans la matrice de test (le champ existait déjà côté génération, il manquait sa ligne dans le formulaire).
Liaison focale automatique par calque (onglet Calques) : bouton 🔗/🎯 par calque pour lier son pas de remplissage à la taille du spot laser, avec pastille de qualité colorée.
Notification sonore de fin de job (2 bips), en plus du message déjà affiché.
Bouton de déverrouillage GRBL ($X) apparaissant automatiquement en état Alarm, toujours avec confirmation avant envoi.
Cases "Aperçu en négatif" et "Masquer les déplacements rapides G0" cochées par défaut.

## Corrigé

Focale (Paramètres Machine) : Lignes/mm, DPI et pastille de qualité d'Image & Filtres se recalculent systématiquement, quel que soit le mode de résolution actif.
Changement de profil machine : force le même rafraîchissement, qui ne se déclenchait pas si la nouvelle focale coïncidait avec l'ancienne.
Liaison focale par calque : posait le drapeau "lié" sans jamais appliquer la valeur de la focale au pas de remplissage.
Plein écran "Images / Tramage" : superposition visuelle du panneau de réglages par-dessus l'onglet réellement actif à la fermeture.
Aperçu image : régression de lenteur due à un cache de rendu mal adapté à un contenu changeant en permanence.
Windows : texte d'aide de "Paramètres Machine" pouvant dépasser l'espace disponible et bloquer le glisseur des séparateurs.

## [1.6.0]

feat: DRO temps réel, plein écran étendu, corrections rendu 2D (v1.6.0)

### Ajouté :
- Plein écran pour les onglets Images/Tramage, Visualisation 2D G-Code et
  Console/G-Code (même principe que l'Éditeur Vectoriel et PNG -> SVG).
- Plein écran Images/Tramage : panneau de réglages du tramage affiché à
  côté des aperçus, pour un retour en direct sans sortir du plein écran.
- DRO (position machine en temps réel) : état GRBL (Idle/Run/Hold/Alarm)
  et position X/Y/Z en direct, en jog comme en cours de job.
- Marqueur de position en direct sur l'aperçu 2D G-Code pendant le
  streaming.

### Corrigé :
- Éditeur Vectoriel : 3 messages restaient codés en dur en français au
  lieu de suivre la langue choisie.
- Aperçu 2D G-Code : les déplacements G1 à puissance nulle étaient
  affichés dans la couleur de la gravure réelle, rendant les deux
  indiscernables (visible entre les carrés de la matrice de test) ;
  affichés maintenant en gris pointillé, comme les G0.
- Couleur par défaut de la matrice de test / G-code importé : vert plus
  lumineux et contrasté (#00ff88 au lieu de #00cc66).
- Démarrage : la demande de restauration de sauvegarde automatique
  s'affichait avant que la fenêtre soit visible ; différée jusqu'à
  l'affichage réel de la fenêtre (évite un dialogue invisible bloqué en
  arrière-plan).

Fichiers modifiés :
usb_controller.py, workers.py, laser_control_mixin.py, job_queue_mixin.py,
gcode_generation_mixin.py, ui_setup_mixin.py, i18n.py, main_window.py,
vector_editing_mixin.py, app_utils.py

## [1.5.0]

### Ajouté
- **Utilitaire de conversion PNG vers SVG (Vectorisation)** :
  - Outil intégré permettant de transformer directement des images matricielles (PNG) en tracés vectoriels SVG.
  - Réglages fins de vectorisation : ajustement du seuil de tolérance (Noir/Blanc), simplification et lissage des contours, et filtrage du bruit.
  - Aperçu instantané du rendu vectoriel avant insertion dans le projet de découpe ou gravure.

## 🚀 Release v1.4.1

### ✨ Améliorations & Ergonomie

* **Positionnement dynamique à la souris :** Possibilité de sélectionner et de déplacer l'intégralité d'un fichier SVG directement sur le plan de travail.
* **Ajustement de précision (Offset X / Y) :** Ajout des contrôles de décalage X et Y pour affiner la position exacte de vos éléments vectoriels au millimètre près.

---
*Cette version apporte plus de souplesse dans la manipulation des calques vectoriels et accélère la préparation de vos projets.*

## [1.4.0]

### Ajouté
- **Traduction quasi complète de l'application** (Français, Anglais,
  Allemand, Espagnol) : quasiment toutes les boîtes de dialogue, messages
  d'erreur/confirmation et libellés de boutons de l'ensemble des onglets
  utilisent désormais le système `i18n.py` — 319 chaînes traduites au
  total, vérifiées une à une contre le dictionnaire (aucune clé manquante).

### Corrigé
- `1.3.1` : corrections du rendu 2D pour les calques vectoriels/texte/SVG
  (voir détails ci-dessous) et adresse e-mail Support mise à jour
  (`laserstudiopro.support@proton.me`).
- Coquille `QQMessageBox` (au lieu de `QMessageBox`) dans
  `laser_control_mixin.py`, qui aurait fait planter l'appli au clic sur
  "Connecter" sans port COM sélectionné.
- `UnboundLocalError` au démarrage : `legacy_svg_box` était utilisé avant
  sa création dans `ui_setup_mixin.py` (ordre des blocs corrigé).
- Rendu 2D des calques vectoriels/texte/SVG : plusieurs calques classés à
  tort comme "balayage raster" étaient fusionnés dans une seule image,
  produisant un rendu incohérent. Chaque calque raster est maintenant
  reconstruit séparément, teinté avec sa propre couleur.

## [1.3.0]

### Ajouté
- **Vérification du mode laser GRBL ($32)** à la connexion USB : avertit si
  ce réglage n'est pas activé (l'optimisation du G-Code en mode M4 suppose
  ce mode actif pour couper le laser pendant les déplacements rapides).
- **Sauvegarde automatique périodique** du projet en cours (toutes les
  5 minutes), avec proposition de récupération au démarrage suivant en cas
  de fermeture inattendue.
- **Historique des commandes manuelles** dans la console GRBL : flèches
  Haut/Bas pour rappeler les dernières commandes tapées.
- **Projets récents** : nouveau sous-menu dans Fichier pour rouvrir vite un
  projet déjà utilisé.
- **File d'attente de jobs** : empiler plusieurs G-Codes à envoyer au laser
  les uns après les autres, sans reconfigurer manuellement entre chaque.
- **Clic sur une case de la matrice de test** (aperçu 2D) : applique
  directement sa puissance/vitesse (ou nombre de passes) aux réglages de
  gravure/découpe courants.
- **Export/import des profils matériaux** en fichier `.json` séparé,
  partageable entre utilisateurs d'une machine similaire.

### Corrigé
- `load_project` utilisait par erreur la boîte de dialogue "Enregistrer"
  au lieu de "Ouvrir" pour choisir le fichier projet à charger.

## [1.2.0]

### Ajouté
- Début du support multilingue : nouveau menu **Langue** (entre Fichier
  et Aide) permettant de choisir Français ou English. Le changement
  s'applique au prochain démarrage de l'application.
- Nouveau module `i18n.py` : dictionnaire de traduction centralisé et
  fonction `tr()`, sans dépendance externe.
- Traduits pour l'instant : les menus Fichier/Langue/Aide et les 7 noms
  d'onglets du panneau de réglages. Le reste de l'interface (champs,
  boutons, messages) sera traduit progressivement dans les prochaines
  versions.

## [1.1.0]

### Ajouté
- Menu Aide → **Support** : contact par e-mail pour suggestions/problèmes.
- Menu Aide → **Buy me a coffee** : lien vers la page Ko-fi.
- Onglet **Image & Filtres** : valeurs numériques affichées en direct à
  côté des sliders Luminosité / Contraste / Gamma.
- Nouveau sélecteur **Résolution** (Lignes/mm, DPI, ou Focale laser) avec
  synchronisation automatique dans les deux sens entre les trois, plus
  un indicateur de qualité coloré comparant l'écart de lignes réglé à la
  focale du laser configurée.
- Nouveau champ **Taille du spot (focale)** dans Paramètres Machine,
  avec accès rapide depuis l'onglet Image et sauvegarde par profil.
- Bouton **"→ Enregistrer comme focale machine"** pour synchroniser un
  réglage Lignes/mm ou DPI choisi manuellement vers la focale machine
  (avec confirmation).
- Le mode de résolution, la valeur Lignes/mm et la valeur DPI sont
  désormais mémorisés d'une session à l'autre.

### Corrigé
- Bannière et icône introuvables une fois l'application compilée en
  exécutable (`.exe` / binaire Linux) : recherche désormais à la fois à
  côté de l'exécutable et dans le bundle PyInstaller.
- Zones transparentes d'un PNG importé gravées en noir au lieu d'être
  traitées comme du blanc (canal alpha mal géré à la conversion en
  niveaux de gris).
- Surbalayage (overscan) de la gravure d'image gravé à la puissance du
  premier pixel de la ligne au lieu d'une puissance nulle.
- G-Code de gravure allégé en mode laser dynamique (M4) : la commande de
  mode et l'arrêt laser n'étaient plus renvoyés à chaque ligne quand ce
  n'est pas nécessaire (le mode M3 reste inchangé, ligne par ligne).
- Matrice de test : étiquette "VITESSE" tracée à l'envers (bug
  d'orientation du texte vertical), lettres O/M/B/R/D manquantes dans la
  police vectorielle, position en X parfois négative des titres
  "VITESSE"/"PUISSANCE"/"NOMBRE DE PASSES", contour du carré regravé en
  double après le remplissage raster en mode Gravure.
- Arrondi des étiquettes de puissance/vitesse de la matrice de test :
  utilisation d'un arrondi arithmétique standard au lieu de l'arrondi
  bancaire de Python (ex: S625 affichait 62 % au lieu de 63 %).
- Aperçu d'un G-Code importé (ex: depuis LaserGRBL) : rendu en blocs de
  couleur pleins au lieu de l'image réelle, chevauchement/écrasement des
  motifs les uns sur les autres, effet de bandes horizontales, et aperçu
  illisible tant qu'on n'avait pas zoomé fortement.
- Résolution (Lignes/mm, DPI, Focale) pas toujours correctement
  synchronisée avec la focale machine à l'ouverture de l'application.
- Boîte "Buy me a coffee" affichant le code HTML brut au lieu du lien
  cliquable.

## [1.0.0]

### Ajouté
- Version initiale : découpage de `app.py` (fichier unique) en modules
  distincts (mixins par thème, workers, police vectorielle, calques
  vectoriels, etc.) pour faciliter la maintenance et le travail à
  plusieurs, sans changement de fonctionnalité.
