"""Filtre des fichiers inutiles de l'exécutable (packaging/pyinstaller/bundle_filter.py)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "packaging", "pyinstaller"))
from bundle_filter import is_unused, prune  # noqa: E402


class BundleFilterTests(unittest.TestCase):
    def test_unused_qt_modules_are_removed_on_every_platform(self):
        for path in ("PyQt6/Qt6/lib/libQt6Quick3DPhysics.so.6",          # Linux
                     "PyQt6\\Qt6\\bin\\Qt6QuickControls2Material.dll",    # Windows
                     "PyQt6/Qt6/lib/QtShaderTools.framework/Versions/A/QtShaderTools",  # macOS
                     "libQt6WebEngineQuick.so.6",                         # lien à la racine du bundle
                     "PyQt6/Qt6/qml/QtQuick/Controls/qmldir",
                     "PyQt6/Qt6/resources/qtwebengine_devtools_resources.pak"):
            self.assertTrue(is_unused(path), path)

    def test_what_the_application_needs_is_kept(self):
        for path in ("PyQt6/Qt6/lib/libQt6Core.so.6", "PyQt6/Qt6/lib/libQt6Quick.so.6",
                     "PyQt6/Qt6/lib/libQt6QuickWidgets.so.6", "PyQt6/Qt6/lib/libQt6Qml.so.6",
                     "PyQt6/Qt6/lib/libQt6WebEngineCore.so.6", "PyQt6/Qt6/lib/libQt6WebEngineWidgets.so.6",
                     "PyQt6/Qt6/bin/Qt6WebChannel.dll", "PyQt6/Qt6/lib/libQt6Positioning.so.6",
                     "PyQt6/Qt6/lib/libQt6Test.so.6", "PyQt6/QtQuick.abi3.so",
                     "PyQt6/Qt6/resources/qtwebengine_resources.pak", "PyQt6/Qt6/resources/icudtl.dat",
                     "resources/icons/breeze/22x22/actions/edit-undo.svg", "stencil_studio/studio.html"):
            self.assertFalse(is_unused(path), path)

    def test_only_our_four_languages_are_kept(self):
        kept = [p for p in ("PyQt6/Qt6/translations/qtbase_fr.qm", "PyQt6/Qt6/translations/qt_help_de.qm",
                            "PyQt6/Qt6/translations/qtwebengine_es.qm", "PyQt6/Qt6/translations/qt_en.qm",
                            "PyQt6/Qt6/translations/qtwebengine_locales/en-US.pak",
                            "PyQt6/Qt6/translations/qtwebengine_locales/fr.pak") if not is_unused(p)]
        self.assertEqual(len(kept), 6)
        for path in ("PyQt6/Qt6/translations/qtbase_ja.qm", "PyQt6/Qt6/translations/qtbase_zh_CN.qm",
                     "PyQt6/Qt6/translations/qtwebengine_locales/fil.pak",
                     "PyQt6/Qt6/translations/qtwebengine_locales/pt-BR.pak"):
            self.assertTrue(is_unused(path), path)

    def test_prune_keeps_the_toc_format(self):
        toc = [("PyQt6/Qt6/lib/libQt6Core.so.6", "/src/a", "BINARY"),
               ("PyQt6/Qt6/lib/libQt6Quick3D.so.6", "/src/b", "BINARY")]
        self.assertEqual(prune(toc), toc[:1])

    def test_build_scripts_use_the_shared_spec(self):
        def read(*parts):
            with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
                return f.read()
        self.assertIn("packaging/pyinstaller/LaserStudioPro.spec", read("packaging", "linux", "build-linux.sh"))
        self.assertIn("packaging\\pyinstaller\\LaserStudioPro.spec", read("packaging", "windows", "build.bat"))
        self.assertIn("from bundle_filter import prune", read("packaging", "macos", "LaserStudioPro.spec"))
        for name in ("requirements-linux.txt", "requirements-windows.txt"):
            self.assertIn("opencv-python-headless", read(name), name)


if __name__ == "__main__":
    unittest.main()
