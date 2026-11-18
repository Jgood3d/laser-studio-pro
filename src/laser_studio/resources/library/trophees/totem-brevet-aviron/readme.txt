================================================================================
  TOTEM AVIRON - NIVEAUX 1 / 2 / 3
  (anciennement Or / Argent / Bronze)
  Fichiers de gravure et découpe laser
================================================================================

Auteur       : Antoine Le Morvan
Technique    : Gravure + découpe laser (fichiers séparés PNG / SVG)
Licence      : Libre d'utilisation pour usage personnel et associatif

--------------------------------------------------------------------------------
  PRÉSENTATION
--------------------------------------------------------------------------------

Ce totem est un trophée ou récompense destiné aux rameurs, décliné en trois
niveaux de distinction :

  Niveau 1  →  anciennement Bronze
  Niveau 2  →  anciennement Argent
  Niveau 3  →  anciennement Or

Le design est entièrement personnalisable (nom du rameur, club, année, etc.)
directement dans le fichier SVG source.

Le totem est un objet en volume, assemblé à partir de trois pièces découpées
au laser et collées entre elles. Pour une visualisation du résultat final,
se référer au fichier "preview" fourni avec le projet.


--------------------------------------------------------------------------------
  FICHIERS INCLUS
--------------------------------------------------------------------------------

  totem aviron niveau 3.png
    → Image raster pour la phase de GRAVURE
    → Contient les détails graphiques du motif (à graver sur la pièce principale)
    → À importer en premier dans votre logiciel laser

  totem aviron niveau 1-2-3-or-argent-bronze.svg
    → Fichier vectoriel unique contenant les tracés de DÉCOUPE pour les 3 niveaux
    → Les tracés de découpe sont exclusivement en couleur BLEUE
    → Fichier source modifiable pour la personnalisation
    → Contient les 3 pièces du totem : socle, partie principale, retour

  preview.*
    → Aperçu du rendu final assemblé
    → Sert de guide pour le montage des trois pièces


--------------------------------------------------------------------------------
  STRUCTURE DU TOTEM (3 PIÈCES)
--------------------------------------------------------------------------------

  Le totem est composé de trois éléments distincts à découper et assembler :

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  1. LE SOCLE                                                            │
  │     Base du totem, assure la stabilité de l'ensemble.                   │
  │     Reçoit la partie principale en son centre.                          │
  │                                                                         │
  │  2. LA PARTIE PRINCIPALE                                                │
  │     Pièce centrale et la plus grande.                                   │
  │     C'est sur cette pièce qu'est réalisée la gravure du motif.          │
  │     Elle s'encastre dans le socle et reçoit le retour sur l'avant.      │
  │                                                                         │
  │  3. LE RETOUR                                                           │
  │     Pièce décorative qui vient se coller à l'avant de la partie         │
  │     principale, créant un effet de relief et d'épaisseur.               │
  └─────────────────────────────────────────────────────────────────────────┘

  → Voir le fichier "preview" pour une illustration du montage.


--------------------------------------------------------------------------------
  PERSONNALISATION
--------------------------------------------------------------------------------

  Le fichier SVG est conçu pour être modifié avant découpe.
  Vous pouvez y personnaliser :

    - Le niveau (1 / 2 / 3)
    - Tout autre texte ou élément graphique souhaité

  Logiciels recommandés pour la modification :
    - Inkscape (gratuit, recommandé) : https://inkscape.org

  /!\ Après modification, vérifiez que les tracés de découpe (couleur bleue)
  n'ont pas été déplacés ou redimensionnés involontairement.


--------------------------------------------------------------------------------
  UTILISATION AVEC LASERGRBL (ou logiciel compatible GRBL)
--------------------------------------------------------------------------------

  LaserGRBL est un logiciel gratuit et open-source, disponible sur :
  https://lasergrbl.com

  L'ordre des opérations est important : graver D'ABORD, découper ENSUITE.
  Cela évite que la pièce découpée bouge avant la fin de la gravure.


  ── ÉTAPE 1 : Gravure du motif ───────────────────────────────────────────────

  1. Ouvrir LaserGRBL
  2. Importer le fichier :  totem aviron niveau 3.png
  3. Dans l'assistant d'import, configurer :
       - Mode         : Gravure (raster / ligne par ligne)
       - Résolution   : 300 DPI
       - Luminosité / Contraste : ajuster selon votre matériau
  4. Régler les paramètres laser selon votre machine et votre matériau :
       - Vitesse      : ex. 2000–3000 mm/min pour du bois (à tester)
       - Puissance    : ex. 30–50 % pour une gravure fine (à tester)
  5. Positionner l'origine (point de départ) sur votre matériau

  ── ÉTAPE 2 : Découpe des pièces ─────────────────────────────────────────────

  6. Ajouter le fichier :  totem aviron niveau 1-2-3-or-argent-bronze.svg
  7. Dans l'assistant d'import, configurer :
       - Mode         : Vecteur / Découpe (ligne)
       - Sélection    : Ne traiter QUE la couleur BLEUE
         (tous les tracés de découpe sont sur ce calque couleur)
  8. Régler les paramètres laser pour la découpe :
       - Vitesse      : ex. 500–800 mm/min pour du bois 3 mm (à tester)
       - Puissance    : ex. 80–100 % pour une découpe traversante (à tester)
       - Passes       : augmenter si nécessaire selon l'épaisseur du matériau
  9. Vérifier le positionnement (doit correspondre à la gravure)
  10. Lancer la découpe

  À l'issue de cette étape, vous obtenez les 3 pièces prêtes à assembler.


--------------------------------------------------------------------------------
  MONTAGE
--------------------------------------------------------------------------------

  Matériel nécessaire :
    - Colle à bois ou colle cyanoacrylate (super glue)
    - Pinces ou serre-joints le temps du séchage (optionnel mais recommandé)

  Procédure :

  1. Identifier les trois pièces : socle, partie principale, retour
     (se référer au fichier "preview" en cas de doute)

  2. Encastrer / coller la PARTIE PRINCIPALE dans le SOCLE
     → Vérifier l'aplomb avant que la colle ne prenne

  3. Coller le RETOUR à l'avant de la PARTIE PRINCIPALE
     → Le retour vient se plaquer contre la face gravée
     → Maintenir quelques minutes le temps de prise

  4. Laisser sécher complètement avant manipulation


--------------------------------------------------------------------------------
  CONSEILS MATÉRIAUX
--------------------------------------------------------------------------------

  Contreplaqué tilleul ou peuplier (3 mm)
    → Rendu chaud et naturel, découpe nette, gravure très contrastée
    → Recommandé pour un rendu artisanal et sobre

  Contreplaqué bouleau (3–4 mm)
    → Plus résistant, légèrement plus dense
    → Idéal si le totem est destiné à être manipulé fréquemment

  /!\ Éviter l'acrylique pour ce projet : le collage et l'assemblage en
  volume sont moins adaptés à ce matériau.

--------------------------------------------------------------------------------
  NOTES TECHNIQUES
--------------------------------------------------------------------------------

  - La résolution de 300 DPI du PNG garantit un détail suffisant pour la
    majorité des machines laser grand public.
  - Le SVG contient les 3 niveaux dans un seul fichier ; veillez à n'activer
    que les tracés correspondant au niveau souhaité lors de la découpe.
  - Si votre logiciel supporte les calques (LightBurn, Inkscape), vous pouvez
    isoler facilement les éléments par niveau avant d'envoyer le job laser.


--------------------------------------------------------------------------------
  COMPATIBILITÉ LOGICIELLE
--------------------------------------------------------------------------------

  Testé avec :
    - LaserGRBL 5.x et supérieur

  Compatible en principe avec :
    - LightBurn (gestion des couleurs et calques encore plus aisée)


--------------------------------------------------------------------------------
  CONTACT & PARTAGE
--------------------------------------------------------------------------------

  Si vous réalisez ce totem pour votre club ou vos athlètes, n'hésitez pas
  à partager vos résultats et vos paramètres laser !
  Tout retour sur le montage ou les matériaux utilisés est le bienvenu.

