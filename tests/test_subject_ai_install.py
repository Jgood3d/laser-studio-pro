"""Commande proposée pour installer onnxruntime (détection du sujet par IA de Stencil Studio)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from stencil_studio import subject_ai  # noqa: E402


def _os_release(content):
    f = tempfile.NamedTemporaryFile("w", suffix="os-release", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


class InstallCommandTest(unittest.TestCase):
    def setUp(self):
        self.files = []
        # Python du système, appli non compilée.
        patcher = mock.patch.multiple(sys, prefix="/usr", base_prefix="/usr", create=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        frozen = mock.patch.object(sys, "frozen", False, create=True)
        frozen.start()
        self.addCleanup(frozen.stop)

    def tearDown(self):
        for f in self.files:
            os.unlink(f)

    def release(self, content):
        path = _os_release(content)
        self.files.append(path)
        return path

    def test_fedora(self):
        path = self.release('NAME="Fedora Linux"\nID=fedora\nVERSION_ID=44\n')
        self.assertEqual(subject_ai.install_command(path), subject_ai.FEDORA_INSTALL)

    def test_derivee_de_fedora(self):
        path = self.release('ID=nobara\nID_LIKE="rhel centos fedora"\n')
        self.assertEqual(subject_ai.install_command(path), subject_ai.FEDORA_INSTALL)

    def test_autre_distribution(self):
        path = self.release('ID=ubuntu\nID_LIKE=debian\n')
        self.assertEqual(subject_ai.install_command(path), subject_ai.PIP_INSTALL)

    def test_sans_os_release(self):
        self.assertEqual(subject_ai.install_command("/nexiste/pas"), subject_ai.PIP_INSTALL)

    def test_environnement_virtuel_sous_fedora(self):
        path = self.release("ID=fedora\n")
        with mock.patch.object(sys, "prefix", "/home/u/projet/.venv"):
            self.assertEqual(subject_ai.install_command(path), subject_ai.PIP_INSTALL)

    def test_appli_compilee_sous_fedora(self):
        path = self.release("ID=fedora\n")
        with mock.patch.object(sys, "frozen", True, create=True):
            self.assertEqual(subject_ai.install_command(path), subject_ai.PIP_INSTALL)


class ModelChecksumTest(unittest.TestCase):
    """Le modèle livré correspond à l'empreinte attendue : un modèle remplacé sans mettre à jour
    MODEL_SHA256 serait refusé (et retéléchargé) à chaque lancement."""

    def test_bundled_model_matches(self):
        bundled = os.path.join(REPO, "src", "stencil_studio", "resources", "models", "u2netp.onnx")
        if not os.path.isfile(bundled):
            self.skipTest("modèle non livré dans cette copie")
        self.assertEqual(subject_ai._sha256(bundled), subject_ai.MODEL_SHA256)

    def test_corrupt_download_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "u2netp.onnx")
            body = mock.MagicMock()
            body.__enter__.return_value.read.side_effect = [b"pas un modele", b""]
            with mock.patch.object(subject_ai, "MODEL_DIR", folder), \
                    mock.patch.object(subject_ai, "MODEL_FILE", target), \
                    mock.patch.object(subject_ai, "_SESS", [None]), mock.patch.object(subject_ai, "_RETRY_AT", [0.0]), \
                    mock.patch.object(subject_ai, "_ERR", [""]), \
                    mock.patch.object(subject_ai.urllib.request, "urlopen", return_value=body), \
                    mock.patch.dict(sys.modules, {"onnxruntime": mock.MagicMock()}):
                self.assertIsNone(subject_ai._session())
                self.assertIn("corrompu", subject_ai.last_error())
            self.assertFalse(os.path.exists(target))
            self.assertFalse(os.path.exists(target + ".part"))


if __name__ == "__main__":
    unittest.main()
