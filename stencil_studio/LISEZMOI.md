# Laser Stencil Studio (prototype)

Photo -> silhouette de découpe laser (pochoir avec ponts), export SVG / DXF en mm.

## Lancer
Double-clic sur `lancer_studio.bat` (installe les dépendances la première fois), ou :

    py -m pip install -r requirements.txt
    py studio.py

Le navigateur s'ouvre sur http://127.0.0.1:8765 (tout reste sur ton PC).

## Utiliser
1. **Ouvrir une image** (ou la déposer sur la fenêtre).
2. **Cadre** : glisser pour déplacer, molette pour redimensionner. Forme : cercle / rectangle / sans cadre.
3. **Sujet** : outil **Rectangle sujet** (trace un rectangle autour des personnes/de l'objet), puis, si besoin,
   quelques traits **verts** sur le sujet et **rouges** sur le fond. Le calcul se relance quand tu relâches la souris.
4. **Tons** : régler le rendu. Pour un visage, le mode *Local* garde les traits fins.
5. **Nettoyage et ponts** : plus petit détail, ponts, pièces à supprimer.
6. **Exporter** en SVG ou DXF. Les réglages peuvent être enregistrés / rechargés (JSON).

## Fichiers
- `core.py` : traitement (indépendant de l'interface, réutilisable dans le logiciel)
- `studio.py` + `studio.html` : interface (les deux doivent être dans le même dossier)
- `lasercut_stencil.py` : version ligne de commande
- `i18n.py` + `locales/*.json` : traductions (`tr("English text")`). Ajouter une langue = ajouter un `xx.json`.

## Démarrage rapide
Ouvrir l'image, choisir un **style** (menu « Partir d'un style »), puis corriger le sujet avec le pinceau
(rouge sur le fond mal détecté, vert sur le sujet) et ajuster le cadre.

## Conseils pour un bon résultat
- **Cadre serré** : têtes et épaules, visages grands dans le cadre. Un corps entier donne des visages illisibles.
- **Isoler le sujet** : peindre quelques traits verts (sujet) et rouges (fond, banc, décor).
- **Contour plein du sujet** : garde la silhouette lisible quand les vêtements sont clairs.
- **Simplifier les textures** : lisse feuillage, tricot, enseignes.
- Visage trop chargé : monter *Seuil de détail*. Trop vide : le baisser. Trop de gris-noir : baisser *Zones sombres pleines*.
- Photo nette, d'au moins 1500 px de large.
- Si le fond mal détecté laisse des formes parasites (sol, ombre) : peindre un trait rouge dessus.
- *Canal le plus sombre* : utile pour les objets colorés (casquette rouge, t-shirt bleu) afin qu'ils deviennent pleins.
- **Dessins au trait / cartoon** (traits noirs, couleurs unies) : style *Dessin au trait*. Les traits plus fins que le détail minimal sont épaissis (case « Épaissir les traits fins »).
- Le curseur *Décalage* décide si une zone sombre (ex. un nez violet) est pleine ou seulement contournée.
- Si le personnage dépasse du cercle : choisir la forme *Rectangle* (proportions 3:4 par exemple) ou *Sans cadre extérieur*.
- **Photo avec décor chargé** : tracer d'abord le *Rectangle sujet*, puis resserrer le cadre sur le sujet.
- *Épaisseur des traits* : plus de matière = découpe plus robuste, moins de ponts nécessaires.
- *Résolution de l'aperçu* : monter à 900 ou 1200 pour voir des bords lisses (plus lent).

## Vérifier que tous les fichiers sont à jour
Au lancement, la console affiche : `Versions : core.py 2026.10.27 | studio.html 2026.10.27`.
Les deux numéros doivent être **identiques**. Sinon (ou si l'interface affiche un bandeau rouge « ATTENTION »),
remplacer **tous** les fichiers : `core.py`, `studio.py`, `studio.html`, `i18n.py`, `lasercut_stencil.py`, `locales/`.

## Autotest
`py selftest.py` vérifie que OpenCV / numpy / scipy de ce PC donnent les résultats attendus (image synthétique).
Si une ligne affiche `DIFF`, envoyer la sortie complète.

## Résolution de calcul
Le résultat dépend de la résolution de calcul : à 640 px, les traits fins se dégradent (beaucoup de ponts, pièces supprimées).
Garder l'aperçu à **1200 px** (défaut, identique à l'export). Le bandeau indique « Calculé à … px ».

## Dessins au trait : mode local
Le style *Dessin au trait* utilise le mode **Local** (détecte les traits plus sombres que leur voisinage), pas un seuil fixe :
les traits fins et flous des images web ne sont pas assez sombres pour un seuil global. Si trop de détails : monter *Seuil de détail* (14 -> 20).
Résolution d'export conseillée : 1200 à 1600 px (2400 px prend ~15 s et n'apporte pas plus de précision utile).

## Photos en noir et blanc
GrabCut (isolation du sujet) ne fonctionne pas sur une image strictement grise : le programme lui fournit
désormais 3 canaux utiles (gris, flou, texture). Le bandeau affiche « Sujet : xx % » ; si la détection échoue
(sujet quasi vide), le masque est ignoré et un avertissement s'affiche. Pour une photo : tracer un *Rectangle sujet*,
resserrer le cadre sur le sujet, puis choisir le style *Photo de portrait*.

## Photos : trame de points (halftone)
Une photo ne se réduit pas en pochoir noir et blanc lisible. Pour les photos, choisir le style **Photo en trame de points** :
la plaque est percée de trous dont la taille suit la clarté de l'image (clair = gros trou, sombre = petit trou ou rien).
Tout reste attaché par la matière entre les trous : aucun pont nécessaire.
- Cadre serré sur le visage ; gros plan = meilleur rendu.
- *Pas de la trame* : 1,2 à 2,0 mm (plus petit = plus de détail, mais plus de trous à découper).
- *Matière minimale entre les trous* et *Plus petit trou* : à régler selon le matériau et le laser (tester sur une chute).
- *Courbe des tons* : monter pour plus de matière (image plus sombre), descendre pour plus de trous.
- Chaque trou est découpé : compter ~1 min par 2000 trous selon la vitesse.
- Meilleur enchaînement pour une photo de personnes : style *Photo en trame de points* -> outil *Rectangle sujet*
  autour des personnes (têtes comprises) -> cadre resserré -> pas 1,2 à 1,4 mm. Hors du sujet, la plaque reste pleine.
- *Contraste* : 0 = tons naturels, 1 = histogramme égalisé (utilise toute la plage de tailles de trous).
- **Lisibilité à taille réelle** : *Détail local* (1,5 par défaut, jusqu'à 2-3) accentue les traits du visage ;
  *Contraste* 0,8 à 1 utilise toute la plage de tailles de trous ; un pas plus fin (1,1 à 1,4 mm) rend plus photographique
  (mais plus de trous à découper : ~3400 trous = ~7,7 m de découpe à 1,4 mm).

## Combien de points sur un visage ? (trame)
Il faut au moins 15 à 20 points de large sur un visage pour qu'il soit lisible. Largeur d'un visage = (largeur du visage / largeur du cadre) x taille finale.
Exemple (visage = 12 % du cadre, pas 1,4 mm) : 100 mm -> 8 points ; 150 mm -> 13 points ; 200 mm -> 17 points (~8800 trous, ~30 m de découpe).
Le bandeau affiche « Trame : N points de large » pour toute l'image.
Pour une photo de personnes : *Rectangle sujet* serré autour d'elles -> le cadre se règle tout seul (bouton *Cadrer sur le sujet* pour le refaire) ->
forme *Rectangle* (les proportions se choisissent automatiquement) -> taille finale 150 à 200 mm. Vérifier le masque dans la vue *Original* (zones sombres = rejetées).

## Rendu réaliste et rétroéclairage
Onglet **Rendu** (à droite ; il s'affiche tout seul dès que tu changes le matériau ou la lumière) : aperçu de la plaque dans le matériau choisi (bois clair, bois foncé, noir, gris, ardoise, blanc), avec ou sans
rétroéclairage (LED derrière un diffuseur) et une couleur de lumière (blanc chaud/froid/neutre, rouge, vert, bleu, ambre). Couleurs indicatives.
- Rétroéclairée, l'image se lit très bien. Éteinte sur un matériau clair, elle est presque invisible ; sur un matériau foncé avec diffuseur, elle reste lisible.
- Un diffuseur (papier calque, acrylique opale) derrière la plaque est nécessaire pour que les trous forment une image uniforme.

## Sans cadre
Forme **Sans cadre extérieur** : ni plaque, ni anneau. En trame, l'export ne contient que les trous (pour personnaliser un objet existant).
- Le rendu démarre en **bois foncé, rétroéclairage allumé** (la combinaison où l'image se lit le mieux). Le bouton **Rétroéclairage** à côté des onglets allume/éteint la lumière en un clic.

## Dimensions : image complète ou largeur x hauteur
Pour les formes *Rectangle* et *Sans cadre extérieur*, le menu **Proportions** propose :
- **Image complète (ratio d'origine)** : prend toute la photo, à son format ; *Taille finale* = le plus grand côté.
- **Personnalisé (largeur x hauteur)** : on saisit la largeur et la hauteur en mm. Si le ratio diffère de celui de la photo, la photo est **recadrée** (jamais déformée) ; déplacer / redimensionner le cadre pour choisir la zone.
Le bandeau affiche les dimensions finales (ex. « Taille : 150.0 x 100.0 mm »), identiques à celles du SVG/DXF exporté.

## Photos sombres (noir et blanc)
En mode Local, les zones « pleines » sont celles plus sombres que le seuil automatique moins *Zones sombres pleines*.
Sur une image globalement sombre ce niveau devenait négatif et rien n'était rempli (cheveux dessinés par leur seul contour) :
dans ce cas, les 22 % de pixels les plus sombres sont maintenant remplis automatiquement.
L'isolation du sujet n'est plus cochée par défaut (elle rejette les zones sombres proches du fond) : utiliser *Rectangle sujet*, qui l'active.

## Formes, accroche et texte (version 2026.10.33)
- **Formes** : cercle, ovale, rectangle, rectangle arrondi, cœur, étoile, ou sans cadre. L'anneau suit la forme.
- **Accroche** (groupe *Accroche*) : œillet en haut (boule de Noël), coin haut gauche ou droit, ou deux trous gauche et droite. Forme ronde ou en goutte, diamètre du trou et matière autour réglables (3 mm de trou et 2,5 mm de matière : passe un fil ou un petit crochet).
  L'œillet dépasse du cadre : les dimensions finales affichées et exportées l'incluent. Sans cadre extérieur, il est relié à la matière la plus proche.
- **Texte dans l'anneau** : texte en haut et/ou en bas, courbé le long de l'anneau, découpé en lettres. Les centres des lettres (A, O, B, D, P, R...) sont retenus par un petit pont.
  L'anneau s'élargit tout seul pour contenir le texte (hauteur de lettres + 3 mm). Un texte trop long est réduit automatiquement.
  Le texte fonctionne sur cercle, ovale, rectangle et rectangle arrondi (pas sur cœur ni étoile).
- Valable en pochoir comme en trame de points.
- Ligne de commande : `--shape`, `--hang`, `--hang-style`, `--hang-hole`, `--text-top`, `--text-bottom`, `--text-size`.
- La police fournie est DejaVu Sans Bold (dossier `fonts/`, licence libre). Une autre police .ttf peut être indiquée avec le réglage `font` (fichier de réglages JSON).

## Placement libre de l'image sur l'objet (version 2026.10.33)
Dans le groupe *Cadre*, cocher **Placement libre** : le cadre (la forme de l'objet, dessinée avec son vrai contour : cœur, étoile, ovale...) peut sortir de la photo.
- **Glisser** dans la vue de gauche déplace l'objet par rapport à la photo, **molette** ou curseur *Taille du cadre* (jusqu'à 400 %) change l'échelle. Les bords de la photo sont en pointillés blancs.
- Les marges hors photo restent vides en pochoir, et pleines (sans trou) en trame de points.
- L'aperçu de droite se met à jour à chaque déplacement.
- Sans cette case, le cadre reste dans la photo comme avant.

## Gravure : photo tramée pour porte-clés, plaques (version 2026.10.33)
*Type de sortie* → **Gravure**, ou le style « Photo pour gravure ». Le programme produit :
- une **image tramée à la résolution de la machine** (réglage *Résolution* : 195 DPI pour votre Phecda 20W), à la bonne taille en mm ;
- le **contour de découpe** de la pièce (forme choisie, œillet d'accroche, texte).
Réglages : méthode de tramage (Stucki conseillé pour les photos ; Atkinson donne plus de contraste ; Bayer un motif régulier ; Seuil = noir et blanc pur), niveaux de gris (3 et plus : plusieurs puissances de gravure), luminosité, contraste, tons moyens, netteté, négatif (graver les zones claires, pour une matière sombre qui s'éclaircit), marge non gravée au bord.
L'aperçu affiche le nombre de points, le pourcentage brûlé et une **durée estimée** (selon la vitesse indiquée).
Onglet **Rendu** : la pièce est simulée dans le matériau choisi, gravure foncée sur bois, claire sur matière sombre.
Exports (boutons en haut) :
- **Exporter la gravure (PNG)** : image à importer dans LightBurn / le logiciel du graveur (la résolution est inscrite dans le fichier) ;
- **Exporter SVG avec image** : image + contour de découpe au même endroit, à l'échelle ;
- **Exporter SVG / DXF** : le contour de découpe seul.
Conseil : réglages du graveur = ceux de vos essais (mode tramage désactivé dans le logiciel du graveur : l'image est déjà tramée).

## Caisson lumineux (version 2026.10.33)
Onglet **Caisson** : mise en page des pièces à découper pour une boîte à LED derrière votre façade (pochoir, trame de points ou gravure, avec n'importe quelle forme).
Principe par couches collées : **façade** (votre plaque) + **diffuseur** (plaque opaline ou papier calque épais) + **cadres** (même silhouette, évidée ; ils forment les parois et portent la bande LED) + **fond** démontable.
- Nombre de cadres = profondeur / épaisseur (25 mm de profondeur en 3 mm : 9 cadres).
- Les 3 cadres du fond ont des avant-trous pour les vis ; le fond a les trous de passage et un trou pour le câble.
- L'œillet d'accroche traverse toutes les couches. Sans vis (réglage 0) : tout se colle.
- Réglages : profondeur, épaisseur, largeur de paroi (10 mm minimum pour des vis M3), nombre et diamètre des vis, trou de câble, diffuseur, largeur de la plaque à découper, espace entre pièces.
- **Exporter le caisson (SVG / DXF)** : toutes les pièces rangées sur une plaque, prêtes à découper.
Conseils : au moins 20 mm de profondeur pour que les LED ne se voient pas en points ; coller la bande LED sur la paroi intérieure des cadres.

## Caisson à encoches, paroi flexible (version 2026.10.33)
Réglage *Système du caisson* → **Parois à encoches** (assemblage à doigts, comme une boîte en MDF), à la place des cadres empilés.
- **Façade et fond** : votre plaque et son fond, percés de fentes le long du bord ; les parois y entrent par des **languettes** et se collent. La plaque dépasse de 1,5 mm autour de la paroi ; l'anneau extérieur s'élargit tout seul pour porter les fentes.
- **Parois droites** (rectangle) : 4 pièces assemblées aux angles par des **doigts** (assemblage à 90 degrés).
- **Parois courbes** (cercle, ovale, rectangle arrondi) : une bande qui se referme, **flexible là où le contour n'est pas droit** : des fentes verticales (traits rouges dans l'aperçu) permettent de courber le contreplaqué. Les parties droites restent pleines. Les deux extrémités s'emboîtent en peigne.
- **Diffuseur** : plaque plus petite qui se pose derrière la façade, à l'intérieur des parois. **Fond** : même contour que la façade, avec le trou de câble.
- Réglages : profondeur (hauteur de la paroi), épaisseur du matériau, écart des fentes de flexion (3 mm : plus serré = plus souple, mais plus fragile), jeu des fentes pour la colle.
- Avertissements : angles vifs (cœur, étoile : la paroi flexible risquerait de casser, préférer les cadres empilés), rayons inférieurs à 15 mm.
- Matériau : contreplaqué 3 mm (peuplier ou bouleau) ou MDF fin : faire d'abord un essai de courbure sur une chute.
- Le fond n'est pas vissé : il tient par ses languettes, collées ou non (pour pouvoir changer la LED, ne pas coller le fond).
- Épaisseur totale = profondeur + 2 épaisseurs.

## Mode lignes, bordure réglable (version 2026.10.33)
- **Type de sortie : Lignes** (ou style « Photo en lignes »). La photo devient des **fentes parallèles de largeur variable** : plus la zone est claire, plus la fente est large. C'est une variante de la trame de points, avec les mêmes réglages de tons (contraste, courbe, détail locaux, plus matière minimale entre fentes et plus petite fente).
  Réglages propres : *Écart entre les lignes*, *Angle des lignes*, *Longueur maximale d'une fente avant un pont* (30 mm par défaut : de petits ponts de matière évitent que les fines bandes entre les fentes plient ou cassent ; 0 = fentes continues).
  Fonctionne avec toutes les formes, le texte, l'œillet et le caisson.
- **Bordure autour de l'image** : le réglage *Largeur de la bordure autour de l'image* va maintenant jusqu'à 30 mm (anneau plein autour de l'image, en pochoir, points ou lignes). Il n'est plus modifié en douce : en passant au caisson à encoches, il est relevé une fois au minimum utile, puis vous le réglez librement (un avertissement s'affiche s'il est trop étroit pour les fentes des parois).
- **Débord de la façade et du fond** autour de la paroi (caisson à encoches) : réglable de 0,5 à 6 mm (1,5 par défaut).

## Paroi flexible « en briques », paroi en 2 ou 3 morceaux (version 2026.10.33)
- Les fentes de flexion sont maintenant de longues fentes parallèles à l'axe de pliage, en colonnes, coupées par de petits ponts de matière décalés d'une colonne à l'autre (comme sur du contreplaqué flexible du commerce). Réglages : écart des colonnes, longueur d'une fente, pont entre fentes.
- « Paroi flexible : nombre de morceaux » (1 à 3) découpe la bande en plusieurs pièces assemblées par des encoches de jonction, pour mieux remplir la plaque. Les coupes sont placées de préférence sur un tronçon droit.

## Diffuseur en PDF taille réelle (version 2026.10.35)
Bouton « Diffuseur (PDF, taille réelle) » : PDF vectoriel du contour de la plaque diffusante, sur page A4 ou A3 (ou format sur mesure si plus grand). Imprimer à 100 % (« taille réelle », sans « ajuster à la page ») ; une règle de 50 mm en bas permet de vérifier l'échelle.

## Mode lignes : ponts décalés (version 2026.10.35)
Les coupures qui limitent la longueur des fentes étaient alignées d'une ligne à l'autre et dessinaient un gros trait à travers le visage. Elles sont maintenant décalées ligne par ligne.

## Réglages masqués selon le type de sortie (version 2026.10.36)
Les réglages inutiles pour la sortie choisie sont masqués (et les groupes entièrement inutiles disparaissent) : seuils, ponts et nettoyage pour le pochoir ; trame pour les points et les lignes ; groupe Gravure seulement en gravure ; réglages de paroi selon le système de caisson.

## Paroi flexible à fentes en fuseau (version 2026.10.37)
Les fentes de flexion ne sont plus de simples traits de scie (la paroi cassait) mais de vraies ouvertures en fuseau, étroites aux extrémités et larges au milieu, en colonnes décalées avec petits ponts, comme sur les parois « kerf bending » du commerce. Les nervures entre fentes travaillent en torsion et plient sans casser. Réglages : largeur de fente (2 mm), longueur (14 mm), pont (3 mm), écart des colonnes (4 mm). Pour une courbe serrée, augmenter la largeur de fente ou rapprocher les colonnes ; sur du contreplaqué épais, allonger les fentes.

## Paroi flexible « à boucles » d'après ton essai (version 2026.10.38)
Le motif des fentes reproduit ton test qui fonctionne (fichier « Test charnière ») : lignes de coupe espacées de 2,54 mm, alternativement une fente de bord (du bord jusqu'au milieu, avec un pont de matière de 6 mm au milieu) et une fente centrale fermée aux deux bouts (marge de 2,7 mm). Chaque cellule est une boucle de deux nervures reliée aux voisines par le pont du milieu : la bande s'étire et se courbe comme un ressort au lieu de casser. Réglages : largeur de nervure, marge des fentes centrales, pont du milieu.

## Fentes de flexion jusqu'au bord réel (version 2026.10.39)
Sous une languette de fixation, les fentes de bord la traversent maintenant jusqu'à son extrémité : toutes les fentes touchent le vrai bord de la paroi, comme sur ton dessin, et la languette ne rigidifie plus la bande.

## Réglages de paroi flexible renommés (version 2026.10.40)
Les trois réglages de la paroi flexible ont changé de sens ; ils portent maintenant de nouveaux noms (box_rib_mm, box_end_mm, box_mid_mm) pour que d'anciennes valeurs mémorisées par le navigateur ou dans un fichier de réglages (par exemple « longueur de fente 14 mm ») ne faussent plus le motif : elles faisaient disparaître les fentes centrales et réduisaient le pont du milieu. Garde-fous : marge limitée à 30 % de la hauteur, pont à 50 %.

## Languettes pleines, recadrage sur le visage (version 2026.10.41)
- Case « Languettes pleines » (caisson à encoches) : les languettes de fixation ne sont plus traversées par les fentes de flexion, pour les comparer à la version traversée.
- Bouton « Cadrer sur le visage » : détecte le visage et place le cadre dessus (cheveux compris). Utilise le détecteur d'OpenCV s'il est disponible avec ses données ; sinon, repli sur la teinte chair, qui ne marche que sur les photos en couleur. Si rien n'est trouvé, un message l'indique.

## Valeurs saisissables au clavier (version 2026.10.42)
Chaque réglage à curseur a maintenant un champ numérique à côté de son nom : tape la valeur exacte (virgule ou point) puis Entrée, ou utilise les petites flèches. Le curseur suit, et la valeur est limitée aux bornes du curseur.

## Jeu des languettes selon la courbure, rotation du cadre (version 2026.10.43)
- Caisson à encoches, case « Jeu des fentes ajusté à la courbure » (activée par défaut) : pour une languette pleine, la fente de la façade et du fond est élargie de la flèche de la languette sur la courbure locale (longueur² × courbure / 8). Les languettes découpées en nervures épousent la courbe : on les autorise plus longues (flèche tolérée 1 mm au lieu de 0,25 mm).
- Rotation du cadre : réglage « Rotation du cadre (degrés) » de −180 à 180, poignée ronde au-dessus du cadre à tirer à la souris (Maj = crans de 15°), ou Alt + molette pour tourner de 1° en 1°. Un cadre tourné se place librement : il peut déborder de la photo (marges vides remplies comme en placement libre). Le contenu du cadre est remis droit dans le résultat.

## Supports du caisson : pied et fixation murale (version 2026.10.44)
Groupe Caisson, réglage « Support » :
- **Fixation murale** : deux trous de serrure sont percés dans le fond (grand cercle pour la tête de vis, fente étroite qui monte pour la tige). Réglages : diamètre de la tête et de la tige. Tu visses deux vis dans le mur, tête dépassant d'environ 3 mm, tu passes les têtes dans les cercles puis tu fais glisser le caisson vers le bas. Les trous sont placés dans le tiers haut, loin du bord et des encoches ; si la forme est trop petite, un message l'indique.
- **Pied** : une base pleine et plusieurs couches à rainure à coller dessus. La rainure a la largeur de l'épaisseur totale du caisson (plus un petit jeu) et la longueur du bas de la forme sur la profondeur choisie (9 mm par défaut) ; le caisson se pose dans la rainure, qui le tient droit. Le nombre de couches s'ajuste à la profondeur de rainure.
- **Les deux** sont possibles en même temps.
Les pièces du pied rejoignent la mise en page de découpe du caisson.

## Aperçu avant l'export, vue du caisson assemblé (version 2026.10.45)
- **Aperçu avant l'export** (case « Aperçu avant l'export » dans « Aperçu et export », activée par défaut) : chaque bouton d'export ouvre d'abord une fenêtre qui montre le fichier tel qu'il sera coupé (SVG ou DXF, gravure PNG, caisson, diffuseur PDF), avec les dimensions, le nombre de pièces et les avertissements. « Télécharger » enregistre le fichier, « Retour aux réglages » (ou Échap) permet de corriger.
- **Vue « Assemblé »** : dessin du caisson monté, vu de l'avant-gauche : façade (avec le rendu du matériau et du rétroéclairage), profondeur, fond, et pied s'il est activé. Dessin approximatif pour contrôler les proportions avant de découper ; les trous de serrure se voient dans la vue « Caisson » (fond).

## Œillet d'accroche : même tracé que sans œillet (version 2026.10.46)
Le corps du caisson (paroi, diffuseur, fentes) est maintenant calculé sur la forme seule, sans la languette de l'œillet : le tracé est identique avec ou sans accroche (avant, la zone sous l'œillet creusait la paroi et le diffuseur). Les languettes d'assemblage qui tomberaient contre l'œillet sont simplement omises (pas de fente à cet endroit).

## Étoile : un morceau de paroi par côté de branche, nouvelle forme « Sapin » (version 2026.10.47)
- **Caisson à encoches** : la paroi est maintenant séparée à chaque angle de 35 à 150 degrés (avant : angles droits seulement). Une étoile donne 10 morceaux, soit 2 par branche. Les morceaux s'assemblent par des doigts d'angle dont la saillie dépend de l'angle entre les deux parois (t/2 à 90°, plus grande pour les angles aigus). Aux angles très aigus les faces ne sont pas planes l'une contre l'autre : un peu de colle et un léger ponçage sont nécessaires. Plus d'avertissement « angles vifs » pour ces formes.
- L'avertissement « courbes serrées » ne compte plus les zones de bout de morceau (sans fentes).
- **Forme « Sapin »** : trois étages et un tronc, œillet à la pointe. Disponible dans le sélecteur de forme, en ligne de commande (`--shape tree`) et dans le caisson. Comme le cœur et l'étoile, le texte dans l'anneau n'est pas géré.

## Suite de la version 2026.10.47
Angles très aigus (jusqu'à 178°) : la paroi est séparée à chaque sommet, y compris aux pointes fines d'étoile (toujours 10 morceaux, 2 par branche). Trous de serrure : la recherche de place va maintenant jusqu'à 70 % de la hauteur, ce qui permet de les placer sur un sapin dont le haut est étroit.

## Image entière dans le cadre, test de flexibilité (version 2026.10.48)
- **« Faire rentrer l'image dans le cadre »** (à côté de « Cadrer sur le sujet ») : agrandit le cadre autour de l'image pour qu'elle y tienne en entier, en tenant compte de la forme (sapin, étoile, cœur, cercle...), de la rotation et de la bordure. Si un rectangle sujet est tracé, c'est lui qui doit rentrer ; sinon toute la photo. Le placement libre est activé (marges vides autour de l'image).
- **Test de flexibilité** (boutons « Test de flexibilité (SVG) » et « (DXF) » dans l'en-tête) : une plaque de 12 bandes de 70 mm, à la hauteur de paroi du caisson. Chaque ligne a une largeur de nervure différente (2 ; 2,54 ; 3 ; 3,5 mm), chaque colonne un pont du milieu différent (4 ; 6 ; 8 mm) ; la marge des fentes centrales est celle du réglage. Chaque bande est numérotée dans le fichier (texte hors découpe). Découpe-la dans ton vrai matériau, plie les bandes sur le rayon voulu et note le numéro de la meilleure, puis règle la largeur de nervure et le pont du milieu en conséquence.

## v2026.10.49
- Nouveau réglage « Largeur de l'image sur la plaque (mm) » : saisissez directement la taille réelle de l'image. En dessous de la taille du cadre, le mode libre s'active (marges vides). Le curseur « Taille du cadre » et la molette restent synchronisés.

## v2026.10.50
- Infobulles : en laissant la souris sur un réglage (libellé ou curseur), une courte explication s'affiche (rôle du réglage, effet d'une valeur plus grande ou plus petite). Traduites en français.

## v2026.10.51
- Bouton ↺ à côté de chaque réglage modifié : remet ce réglage à sa valeur d'origine. Un petit point • apparaît à côté du nom des groupes contenant des réglages modifiés. Le bouton du haut devient « Tout réinitialiser ».

## v2026.10.52
- En haut du panneau : champ de recherche (filtre les réglages par nom ou par explication), case « Afficher les réglages avancés », boutons Tout déplier / Tout replier.
- Mode avancé : les réglages de finesse sont masqués par défaut ; un réglage avancé que vous avez modifié reste visible. Les groupes se souviennent de leur état (ouvert/replié).
- Réglages enregistrés : « Enregistrer sous... » mémorise tous les réglages (matière, épaisseur, tailles, boîte, etc., sauf la position du cadre et le détourage), « Supprimer », « Exporter » / « Importer » (fichier JSON pour les transférer). Ils sont sauvegardés dans `presets.json` à côté de `studio.py`.

## v2026.10.53
- Annuler / Rétablir (boutons ↶ ↷ au-dessus de l'image, ou Ctrl+Z / Ctrl+Y) : fonctionne sur le cadre (déplacement, taille, rotation) et sur tous les réglages, jusqu'à 100 étapes ; l'historique repart à zéro à l'ouverture d'une nouvelle image.
- Rappel des raccourcis sous l'image.

## v2026.10.54
- Langues : allemand (Deutsch) et espagnol (Español) ajoutés, pour l'interface et les messages en ligne de commande (`--lang de` / `--lang es`). Les fichiers sont `locales/de.json` et `locales/es.json` (aussi intégrés dans `i18n.py`).

## v2026.10.55
- Par défaut, tous les réglages sont visibles et tous les groupes ouverts (comme avant). Le masquage des réglages avancés reste possible en décochant « Afficher les réglages avancés ».

## v2026.10.56
- Barre du haut allégée : « Ouvrir une image », un menu « Exporter » (Plaque / Caisson / Outils, avec le test de flexibilité) et un menu « Fichier » (enregistrer, charger, tout réinitialiser).
- Au-dessus de l'image : les cadrages sont regroupés dans un menu « Cadrage » ; les outils Sujet (vert), Fond (rouge), Gomme et « Effacer les repères » n'apparaissent que lorsque « Isoler le sujet » est actif (dessiner un rectangle sujet l'active).

## v2026.10.57 — intégration à Laser Studio Pro
- Le dossier devient un paquet Python (imports relatifs avec repli) : à copier dans LSP sous le nom `stencil_studio/` ; il ne se mélange plus avec les `i18n.py` / `core.py` de LSP. L'usage seul (`python studio.py`) est inchangé.
- `studio.start_server(port)` : serveur dans un thread, sans navigateur.
- `studio_dialog.py` : fenêtre PyQt6 + QtWebEngine ; `open_stencil_studio(fenetre_principale)` à brancher sur un menu de LSP. Les exports SVG/DXF sont importés directement dans l'éditeur vectoriel. Prérequis : `pip install PyQt6-WebEngine`.
- `lsp_bridge.py` : range un DXF dans les calques de LSP (CUT -> Découpe, FRAME -> Marquage/« Cadrage », ENGRAVE -> Gravure Remplie).
- Nouveau réglage « Ajouter un rectangle de cadrage (calque de marquage) » : ajoute un rectangle autour de la pièce (calque FRAME, vert) aux exports SVG et DXF, plaque et caisson.

## v2026.10.58 — Low poly
- Nouveau type de sortie « Low poly (maillage de triangles) » : la photo devient un maillage de triangles (Delaunay) dont les sommets suivent les contours de l'image ; les arêtes forment des poutres de matière, d'un seul tenant (pas de ponts à ajouter).
- Rendu des facettes : « Maillage seul » (triangles ajourés, style décor mural), « Taille du trou selon le ton » (aspect photo), « Facettes les plus sombres pleines ».
- Réglages : nombre de sommets, largeur des arêtes, suivi des détails, % de facettes pleines, variante (autre semis). Style de départ « Décor mural low poly » (avec isolation du sujet). Pour une silhouette découpée, choisir la forme « Sans cadre extérieur ».
- Ligne de commande : `--style lowpoly --lp-points 120 --lp-beam 1.5 --lp-render wire`.

## Dépendances
- `requirements.txt` / `requirements-windows.txt` / `requirements-linux.txt` : Studio utilisé seul (numpy, opencv, Pillow, scipy). `lancer_studio.bat` (Windows) et `lancer_studio.sh` (Linux) installent puis lancent.
- `requirements-lsp-ajouts.txt` : lignes à ajouter aux requirements de Laser Studio Pro pour la fenêtre intégrée (`PyQt6-WebEngine`, `scipy`).

## v2026.10.59
- Correction : en mode low poly, les réglages disparaissaient à chaque changement d'un paramètre (l'affichage était inversé au lieu d'être recalculé).

## v2026.10.60 — couleurs de LSP
- La page expose `window.setTheme({bg, panel, panel2, line, fg, mut, acc, acc2, onacc})`. Dans la fenêtre intégrée, `studio_dialog.py` l'appelle avec les couleurs de la palette Qt de LSP (`theme_from_palette()`), ou avec un dictionnaire passé à `open_stencil_studio(fenetre, theme={...})`. Le Studio seul garde son thème sombre/orange.

## v2026.10.61
- Le style de départ « Décor mural low poly » n'active plus l'isolation du sujet : sur les dessins à aplats clairs, la détection automatique du sujet rejetait les zones claires (message « Le masque ne couvre que x % du cadre »). À activer à la main (avec un Rectangle sujet) si besoin.

## v2026.10.61
- Low poly : le rendu par défaut devient « Facettes sombres pleines (tons de l'image) » : chaque triangle est plein s'il est plus sombre que le seuil (Otsu automatique, réglable avec « Seuil sombre / clair »), ajouré sinon. L'image reste donc reconnaissable. Le « % de facettes pleines » est remplacé par ce seuil. Le mode « Maillage seul » reste disponible pour un décor sans image.
- Valeurs par défaut : 400 sommets, arêtes de 1 mm, suivi des détails 0,9 ; le style « Décor mural low poly » active l'isolation du sujet (tracer un « Rectangle sujet »).
- Astuce : plus la pièce est grande (taille finale), plus on peut mettre de sommets sans que les arêtes bouchent les triangles.


## v2026.10.62 — Low poly : détection du sujet
- Sur fond uni, le maillage est limité à la silhouette du sujet (option « Détecter le sujet automatiquement »).
- Sujet d'un seul ton (silhouette) : maillage seul, sans facettes pleines.
- Préréglage : 150 sommets, arêtes de 1,8 mm. Pour le rendu « art mural » : plaque ≥ 200 mm, peu de sommets, arêtes épaisses.
- Les dessins au trait (type Père Noël) s'y prêtent mal.


## v2026.10.73 — Low poly géométrique
- Case « Style géométrique » : contour en polygone à angles vifs, taches sombres (yeux, nez, oreilles) en facettes pleines, peu de sommets (30 à 100). Réglage « Simplification du contour ».
- C'est le préréglage Low poly par défaut (120 sommets, arêtes 1,8 mm). Idéal : un animal sur fond uni, plaque ≥ 200 mm.
- v.64 : la détection du sujet fonctionne aussi quand le cadre est rond ; préréglage plus détaillé (yeux, casquette, short, chaussures en facettes pleines).


## v2026.10.73 — Ponts manuels
- Bouton « Pont manuel » (vue Résultat) : trace un trait en travers d'une découpe pour la maintenir ; un clic sur un pont manuel le supprime ; « Effacer les ponts manuels ».
- Les ponts manuels sont inclus dans l'export SVG/DXF et suivent Annuler/Rétablir. Ils sont positionnés par rapport au résultat : place-les en dernier (si tu déplaces le cadre, ils ne suivent pas l'image).


## v2026.10.73 — Couleurs de LSP
- `studio_dialog.py` : `LSP_THEME` (fond #232323, panneaux #303030, boutons #3b3b3b, accent bleu #3a5b89, curseurs/coches #6dbef9). Modifiable à un seul endroit.
- v.67 : les couleurs de LSP sont aussi le thème par défaut du Studio lancé seul (plus de flash orange au démarrage dans LSP).


## v2026.10.73 — Trou central dans le fond
- Réglage « Trou au centre du fond (mm) » (groupe Caisson) : trou rond au milieu du fond, diamètre au choix, 0 = aucun. Fonctionne pour les deux styles de caisson.


## v2026.10.73 — Détection IA du sujet + guides low poly
- **Détection IA** (réglage « Détecter le sujet par IA », groupe Sujet) : petit réseau U2-Net (4,5 Mo) via `onnxruntime`. Le modèle est téléchargé une seule fois dans le dossier `models/` (accès à github.com nécessaire au premier usage ; sinon copie `u2netp.onnx` à la main dans `models/`). Sans onnxruntime ou sans réseau, la méthode classique est utilisée et un message l'indique. Installation : `pip install onnxruntime`. Un rectangle sujet ou des traits verts/rouges reviennent à la méthode classique (GrabCut).
- **Guides low poly** (bouton « Guides low poly », affiché en mode Low poly) : clic = sommet imposé (yeux, nez, pointes d'oreilles) ; glisser = arête imposée ; clic sur un guide = le supprime. Utilisable dans les vues Résultat, Superposition et Original. Les guides sont placés par rapport à l'image du résultat : pose-les une fois le cadrage définitif.
- Facettes pleines : seuil à deux niveaux (seules les vraies zones sombres sont remplies). Réglage « seuil sombre / clair » à 0 par défaut.
- Low poly : les poutres ne dépassent jamais 30 % d'une facette (le maillage reste ajouré sur les petites plaques) ; le préréglage autorise un pont jusqu'à 30 mm pour relier le sujet à l'anneau. Conseil : ≥ 150 mm de plaque pour 120 sommets.


## v2026.10.73 — Générateur de code QR
- Type de sortie « Code QR » (ou bouton « Ou créer un code QR » sur l'écran vide, ou style « Plaque avec code QR ») : aucune photo nécessaire. Aucune dépendance en plus (encodeur QR d'OpenCV).
- Contenu : lien / texte libre, ou réseau Wi-Fi (nom, mot de passe, sécurité).
- **Gravure** : plaque découpée (forme, bordure, œillet, texte courbe comme d'habitude) + modules gravés en calque `ENGRAVE` (→ « Gravure Remplie » dans LSP avec l'export DXF).
- **Découpe** : le code est ajouré dans la plaque ; marge claire de 2 modules ajourée, petits ponts (réglage « Largeur des ponts dans le code ») pour retenir les modules isolés et les carrés des repères.
- Le Studio **relit** le code produit (comme un téléphone) et avertit s'il est illisible ou à l'envers, et si les modules sont trop petits (< 0,8 mm gravure, < 1,5 mm découpe). Niveau de correction L/M/Q/H ; « H » conseillé pour la découpe.
- Polarité inversée : pour une matière claire devant un fond sombre.


## v2026.10.73 — Relief en couches (multicouche)
- Type de sortie « Relief en couches » (style « Relief en couches » dans le menu) : l'image devient 2 à 8 **plaques empilées**. La plaque 1 (au fond) est pleine ; chaque plaque suivante est percée là où l'image est assez sombre (ou claire avec « Les zones claires sont les plus profondes »), avec des ouvertures de plus en plus grandes vers l'avant : les zones sombres sont les plus profondes, les ombres font le relief.
- Le sujet est détecté (IA / fond uni) : le fond reste plein. Chaque plaque garde la forme, la bordure, l'œillet et les ponts habituels, plus 3 trous de repérage identiques (tourillons / vis).
- La vue Résultat montre la planche de découpe (une plaque par case) ; la vue **Assemblé** montre l'empilement avec ombres portées.
- Export : SVG avec **une couleur par plaque** (LSP crée un calque par couleur) ; DXF avec des calques LAYER_1…LAYER_n. Colle les plaques dans l'ordre (1 au fond), avec des entretoises si tu veux plus de profondeur.


## v2026.10.73 — Relief en couches : séparation par couleurs
- Réglage « Séparer les plaques par » : **Tons** (luminosité, une seule matière) ou **Couleurs dominantes** (k-means : une plaque par couleur principale, à découper dans une matière de cette couleur).
- Mode couleurs : la palette s'affiche du fond vers l'avant (du plus sombre au plus clair par défaut) ; les flèches ◀ ▶ réordonnent les plaques. Chaque plaque est pleine là où sa couleur est au même niveau ou devant, percée ailleurs ; le fond de la photo prend la couleur de la plaque de devant.
- Le Résultat est coloré, l'export SVG utilise la vraie couleur de chaque plaque (un calque par couleur dans LSP).


## v2026.10.73 — Relief en couches : fond et gravure
- **Fond** : « Couleur de la plaque de devant » (comme avant) ou « Plaque à part » : une plaque pleine en plus tout au fond, dans la couleur choisie ; les autres plaques sont alors percées autour du sujet.
- **Gravure des détails** : option « Graver les détails sur la plaque de devant » (yeux, nez, bouche, lacets...) dans le calque ENGRAVE (« Gravure Remplie » dans LSP avec le DXF). Réglage « Niveau de détail de la gravure ».


## v2026.10.74 — Séparation par couleurs : logos et images simples
- **Nombre de couleurs automatique** (case cochée par défaut) : « Nombre de plaques » devient un maximum ; les couleurs proches sont fusionnées et les teintes intermédiaires de l'anti-crénelage (mélanges rouge/blanc par exemple) ne créent plus de plaques inutiles. Un logo rouge et blanc donne 2 plaques.
- **Images à aplats** détectées automatiquement : classement au plus proche avec bords nets (angles et lettres non arrondis).
- **Pièces libres à coller** : les plaques de devant sont découpées sans ponts (le fond reste avec sa bordure) ; à coller sur la plaque derrière.


## v2026.10.75 — Séparation par couleurs : logos qui remplissent le cadre
- Correctif : pour un logo ou une image à aplats (quelques couleurs seulement) dont la couleur dominante touche les bords du cadre (disque bleu qui remplit le cercle, par exemple), le Studio prenait cette couleur pour un « fond » à retirer : toutes les plaques devenaient pleines. Désormais une image à aplats est traitée en entier (sauf si tu choisis « Plaque à part » pour le fond, ou si tu as tracé un sujet).


## v2026.10.76 — Séparation par couleurs : plus aucune pièce perdue
- Correctif : en mode couleurs, les petites formes éloignées du corps principal (bandes rouges, « ® », lettres fines de « Enjoy your work ») étaient supprimées silencieusement (« Pièces supprimées »), surtout avec « Image complète » sans cadre. Elles sont maintenant **conservées comme pièces libres** à coller ; le nombre apparaît dans les statistiques. Avec « Pièces libres à coller (sans ponts) », aucun pont n'est ajouté.


## v2026.10.77 — Cadre à taille personnalisée : on tire dessus
- Avec les proportions « Personnalisé (largeur × hauteur) », le cadre a **8 poignées** (4 coins, 4 côtés) : tire pour le redimensionner librement, le côté opposé reste fixe, la largeur et la hauteur en mm se mettent à jour. Maj + coin conserve les proportions. Fonctionne aussi avec un cadre tourné. **Double-clic** : le cadre couvre toute l'image à l'échelle actuelle.
- **L'échelle de l'image est conservée** : « Largeur de l'image sur la plaque (mm) » fixe la taille réelle de l'image ; modifier la largeur ou la hauteur du cadre ne change plus cette échelle (avant, l'image se retrouvait à 2000 mm). Règle d'abord la largeur de l'image, puis découpe la fenêtre voulue. Plage de la largeur de l'image portée à 4000 mm.


## v2026.10.78 — Relief en couches : fond de la couleur de l'image
- Nouveau choix de fond : « Plaque à part (couleur du fond de l'image) » : la plaque du fond prend la couleur réelle du fond de la photo (médiane hors sujet, p. ex. blanc). Avec « Couleur de la plaque de devant », le fond prend la couleur de la plaque la plus claire (ex. beige de la peau), c'est voulu : c'est la même matière.


## v2026.10.79 — Intégration LSP : message d'erreur QtWebEngine précis
- Le message « PyQt6-WebEngine n'est pas installé » masquait la vraie cause. Il affiche maintenant la **raison exacte** de l'échec et la solution adaptée : soit installer avec le Python qui lance LSP (chemin affiché), soit — cas fréquent même quand le paquet est installé — ajouter tout en haut du fichier principal de LSP, **avant** la création de QApplication : `from PyQt6 import QtWebEngineWidgets  # noqa`.


## v2026.10.80 — Intégration LSP : repli en fenêtre séparée
- Si Qt refuse QtWebEngine dans LSP (« QtWebEngineWidgets must be imported… before a QCoreApplication »), le Studio s'ouvre désormais dans **sa propre fenêtre** (nouveau fichier `studio_window.py`, processus séparé avec son propre Qt). Les exports SVG / DXF reviennent dans LSP comme d'habitude (la fenêtre se ferme après l'export). Aucune modification du fichier principal de LSP n'est nécessaire.
- Cette fenêtre ne partage pas les réglages mémorisés de la fenêtre intégrée ; ils sont conservés entre deux ouvertures dans le dossier de données de l'application.


## v2026.10.81 — Version compilée (PyInstaller)
- Les réglages mémorisés (`presets.json`) et le modèle IA (`models`) sont écrits dans `%LOCALAPPDATA%\StencilStudio` quand LSP est compilé (ou quand le dossier du Studio n'est pas modifiable), au lieu du dossier de l'application.
- Le repli « fenêtre séparée » est désactivé dans une version compilée (le programme à relancer serait LSP lui-même).
- `build.bat` fourni : ajoute les `--hidden-import` nécessaires (modules du Studio, QtWebEngine, scipy) à la commande PyInstaller.


## v2026.10.82 — Diagnostic QtWebEngine
- Le message d'erreur QtWebEngine ajoute un bloc « Diagnostic » : version du Studio, version compilée ou non, fichier principal réellement exécuté, et si QtWebEngineWidgets était déjà importé au moment où le Studio s'ouvre.


## v2026.10.83 — Fenêtre séparée aussi pour LSP compilé
- Si QtWebEngine ne peut pas être chargé dans LSP, le Studio se relance dans sa propre fenêtre, **y compris pour la version compilée** (`LaserStudioPro.exe --stencil-studio`). Il faut pour cela ces 4 lignes **tout en haut de `main.py`** (avant les imports PyQt6) :

```python
import sys
if "--stencil-studio" in sys.argv:
    from stencil_studio.studio_window import main as _stencil_main
    sys.exit(_stencil_main())
```


## v2026.10.84 — Pipette de couleurs (relief en couches par couleurs)
- Dans « Couches » > « Séparer les plaques par : Couleurs dominantes », bouton **Pipette** : clique sur l'image d'origine pour choisir les couleurs (moyenne 5×5 pixels, jusqu'à 8). **Chaque couleur choisie = une plaque** ; clique une pastille pour la retirer, « Effacer les couleurs choisies » pour recommencer, Échap pour quitter la pipette. Sans pipette (ou avec une seule couleur), les couleurs sont trouvées automatiquement comme avant.
- Avec la pipette, « Nombre de plaques » et la détection automatique sont désactivés ; chaque pixel prend la couleur choisie la plus proche. Avec le fond « Couleur de la plaque de devant », toute l'image est utilisée (tu peux donc choisir le blanc du fond comme une couleur). Les plaques sont triées du plus sombre au plus clair ; les flèches ◀ ▶ les réordonnent.
