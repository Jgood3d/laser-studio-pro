"""Robustesse : dans Laser Studio, un « except Exception » ne fait pas disparaître une erreur sans le
dire. Il la journalise (log), la signale (dialogue, signal, barre d'état), la relance, ou un
commentaire explique pourquoi le silence est voulu (événement très fréquent, repli sans conséquence).
Lu dans le code, sans rien importer."""
import ast
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "laser_studio")
# Mots qui montrent que l'erreur est journalisée, signalée ou relancée.
HANDLED = ("log", "print", "dialogs", "emit", "_say", "status", "warning", "error", "QMessageBox", "raise",
           "traceback", "_log")


class SilentExceptionsTests(unittest.TestCase):
    def test_every_silent_except_exception_says_why(self):
        silent = []
        for base, _dirs, files in os.walk(ROOT):
            for name in (n for n in files if n.endswith(".py")):
                path = os.path.join(base, name)
                with open(path, encoding="utf-8") as f:
                    src = f.read()
                lines = src.split("\n")
                for node in ast.walk(ast.parse(src, path)):
                    if not (isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name)
                            and node.type.id == "Exception"):
                        continue
                    body = " ".join(ast.unparse(b) for b in node.body)
                    if any(word in body for word in HANDLED):
                        continue
                    text = "\n".join(lines[node.lineno - 1:node.end_lineno])
                    if "#" not in text:
                        silent.append(f"{os.path.relpath(path, ROOT)}:{node.lineno}")
        self.assertEqual(silent, [], "except Exception muet, sans commentaire : journaliser ou expliquer")


if __name__ == "__main__":
    unittest.main()
