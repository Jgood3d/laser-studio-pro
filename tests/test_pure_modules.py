"""Règles de dépendance des dossiers de calcul (voir ARCHITECTURE.md, section 6) :

- vector/ : géométrie ; QtGui (QPainterPath, QTransform, QFont…) et les valeurs de QtCore
  (QPointF, Qt) sont acceptés comme bibliothèque de géométrie, jamais QtWidgets ;
- gcode/, grbl/, image/, camera/, library/ : aucun import de PyQt6, testables sans Qt (grbl/ mémorise
  le dernier port par core/preferences).

Lu dans le code (imports), sans rien importer."""
import ast
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "laser_studio")
# Dossiers sans aucun Qt.
WITHOUT_QT = ("gcode", "grbl", "image", "camera", "library")
# Modules Qt acceptés dans vector/ (géométrie).
VECTOR_ALLOWED = ("PyQt6.QtCore", "PyQt6.QtGui")


def qt_imports(folder):
    """{fichier relatif: [modules PyQt6 importés]} des fichiers Python de `folder`."""
    found = {}
    for base, _dirs, files in os.walk(os.path.join(ROOT, folder)):
        for name in (n for n in files if n.endswith(".py")):
            path = os.path.join(base, name)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), path)
            modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules += [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module)
                    if node.module == "PyQt6":                       # from PyQt6 import QtWidgets
                        modules += [f"PyQt6.{alias.name}" for alias in node.names]
            qt = [m for m in modules if m == "PyQt6" or m.startswith("PyQt6.")]
            if qt:
                found[os.path.relpath(path, ROOT)] = qt
    return found


class PureModulesTests(unittest.TestCase):
    def test_vector_uses_qt_only_as_a_geometry_library(self):
        for path, modules in qt_imports("vector").items():
            for module in modules:
                if module != "PyQt6":
                    self.assertIn(module, VECTOR_ALLOWED, f"{path} : {module} (pas de QtWidgets dans vector/)")

    def test_computation_folders_do_not_import_qt(self):
        for folder in WITHOUT_QT:
            self.assertEqual(qt_imports(folder), {}, folder)


if __name__ == "__main__":
    unittest.main()
