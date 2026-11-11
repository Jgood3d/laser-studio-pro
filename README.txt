Fix ModuleNotFoundError: No module named 'i18n'
================================================

Cause:
  window_controller.py importait encore:
    from i18n import ...
    from ui.xxx import ...
  alors que le package est laser_studio.* (layout src/).

Fichiers a remplacer:
  src/laser_studio/ui/app/window_controller.py
  build.bat

Puis relancer:
  build.bat

Note: i18n est un MODULE Python (translations.py), pas une ressource --add-data.
PyInstaller le prend via --paths src + hidden-import laser_studio.i18n*.
