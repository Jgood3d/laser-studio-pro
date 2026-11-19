# Documentation intégrée

Pages affichées dans l'application par **Aide › Documentation** (touche F1).

- Une langue par dossier : `fr/`, `en/`, `de/`, `es/`. Une page absente
  dans la langue de l'interface est affichée en français.
- Le point d'entrée est `index.md`.
- Liens entre pages : `[Les outils](outils.md)`.
- Images dans `images/`, en JPEG (~700 px de large) ou PNG pour les
  schémas : c'est ce qui pèse le plus dans l'exécutable.

Pas de compilation : Qt lit le Markdown directement (CommonMark et
tableaux à la GitHub). Le HTML brut dans le Markdown n'est pas interprété.
Pour vérifier une page, ouvrez-la dans l'application.
