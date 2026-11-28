Issue #185 — Empêcher la mise en veille pendant une gravure
===========================================================

Page dédiée « Alimentation » dans la fenêtre Paramètres (liste de gauche),
à côté de « Langue et thème » — pas une section à l'intérieur.

NOUVEAUX FICHIERS
  src/laser_studio/core/power.py
  src/laser_studio/controllers/power_inhibit.py
  src/laser_studio/ui/settings/power_page.py
  tests/test_power_inhibit.py

FICHIERS MODIFIÉS (remplacer)
  src/laser_studio/controllers/window.py   (SETTINGS_CATEGORIES + "power")
  src/laser_studio/ui/app/main_window.py
  src/laser_studio/i18n/texts/app.py
  CHANGELOG.md

Intégration depuis la racine du dépôt (Dev-test)
-----------------------------------------------
  cp -a issue-185-prevent-sleep/src/laser_studio/core/power.py src/laser_studio/core/
  cp -a issue-185-prevent-sleep/src/laser_studio/controllers/power_inhibit.py src/laser_studio/controllers/
  cp -a issue-185-prevent-sleep/src/laser_studio/controllers/window.py src/laser_studio/controllers/
  cp -a issue-185-prevent-sleep/src/laser_studio/ui/settings/power_page.py src/laser_studio/ui/settings/
  cp -a issue-185-prevent-sleep/src/laser_studio/ui/app/main_window.py src/laser_studio/ui/app/
  cp -a issue-185-prevent-sleep/src/laser_studio/i18n/texts/app.py src/laser_studio/i18n/texts/
  cp -a issue-185-prevent-sleep/tests/test_power_inhibit.py tests/
  # CHANGELOG : fusionner ou remplacer

Vérification
------------
  PYTHONPATH=src python -m unittest tests.test_power_inhibit -v

Dans l'app : Fichier › Paramètres… › Alimentation (entrée dans la liste de gauche).
