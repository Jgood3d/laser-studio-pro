Mise a jour LSP — Puzzle (kerf/validation) + ARCHITECTURE + build.bat
======================================================================

Copier en conservant les chemins (depuis la racine du depot) :

  ARCHITECTURE.md
  build.bat
  packaging/windows/build.bat
  src/laser_studio/vector/puzzle_generator.py
  src/laser_studio/vector/__init__.py          (nouveau, optionnel mais recommande)
  src/laser_studio/vector_editing_mixin.py
  src/laser_studio/i18n/translations.py

Deja presents dans ton LSP.zip (ne pas ecraser sans diff) :
  ui/dialogs/puzzle/*
  main_window.py (bouton puzzle)
  vector/importers.py (puzzle_to_objects)

Problemes corriges / notes
--------------------------
1. puzzle_generator : validation + kerf (kerf/2 interieur) + contours fermes
2. translations : cles puzzle.err.*
3. mixin : capture PuzzleError avec message traduit
4. build.bat racine :
   - plus de chemin absolu utilisateur
   - --paths src
   - hidden-import puzzle / dialogs
   - i18n embarque sous laser_studio/i18n
5. packaging/windows/build.bat : delegue au build.bat racine
6. ARCHITECTURE : section puzzle detaillee + lsp_bridge LAYER_n

Ne pas versionner les __pycache__ ni stencil_studio.zip si redondant avec stencil_studio/.
