================================================================================
  BOULE DE NOËL - PRÉNOM
  Modèle de la bibliothèque Laser Studio Pro
================================================================================

Technique    : Gravure + découpe laser
Taille       : 80 × 86,7 mm

--------------------------------------------------------------------------------
  PRÉSENTATION
--------------------------------------------------------------------------------

Boule de Noël ajourée d'un flocon, avec une attache pour la suspendre au
sapin. Un prénom est gravé sur le bandeau central.

Le prénom se saisit dans cette fiche (champ « Prénom »), avec sa police et sa
taille. La police par défaut, Dancing Script, est fournie avec Laser Studio
Pro : elle est disponible sur tous les ordinateurs. Le prénom reste centré
sur le bandeau ; pour un prénom long, réduire la taille.


--------------------------------------------------------------------------------
  GRAVER ET DÉCOUPER AVEC LASER STUDIO PRO
--------------------------------------------------------------------------------

  1. Dans cette fiche, saisir le prénom. L'onglet « Aperçu » montre la
     boule telle qu'elle sera importée.

  2. Cliquer sur « Importer dans l'éditeur vectoriel ». La boule arrive sur
     deux calques :
       - Gravure : le prénom (gravure remplie), qui reste un texte
         modifiable dans l'éditeur vectoriel ;
       - Découpe : le contour de la boule, l'attache et les ajours du flocon.

  3. Dans l'onglet « Calques (Layers) », choisir le profil matériau de votre
     planche (ou régler vitesse, puissance et passes de chaque calque).
     Exemples pour du contreplaqué de 3 mm (à tester sur une chute) :
       - Gravure : 2000–3000 mm/min, 30–50 %
       - Découpe : 500–800 mm/min, 80–100 %, passes selon l'épaisseur

  4. Vérifier que « Ordre de découpe sûr » est coché (Paramètres →
     Configuration GRBL) : la gravure est faite avant la découpe, et les
     ajours avant le contour. Ainsi, la boule ne bouge pas avant la fin.

  5. Cliquer sur « GÉNÉRER LE G-CODE », contrôler le parcours dans l'onglet
     « Visualisation 2D G-Code », positionner la planche (« Cadrage »), puis
     « ENVOYER AU LASER ».

  Pour toute la famille : importer la boule une fois par prénom, puis les
  répartir sur la planche (« Imbrication auto » dans l'éditeur vectoriel).


--------------------------------------------------------------------------------
  FINITION
--------------------------------------------------------------------------------

  - Passer un ruban ou une ficelle dans l'attache.
  - Poncer légèrement les bords si besoin ; une couche de vernis ou d'huile
    protège le bois et fait ressortir la gravure.


--------------------------------------------------------------------------------
  POLICE
--------------------------------------------------------------------------------

  Dancing Script, de Impallari Type, sous licence SIL Open Font License 1.1
  (texte dans resources/fonts/OFL-DancingScript.txt).
