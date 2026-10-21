"""Garde-fou : aucun nom utilisé sans avoir été importé ou défini (Python ne le voit qu'à l'exécution,
au moment où la ligne est atteinte : un import oublié dans un code d'interface plante le programme)."""
import ast
import builtins
import glob
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__class__"}


def bound_names(tree):
    """Tous les noms liés quelque part dans le fichier (portée ignorée : contrôle volontairement indulgent)."""
    names = set()

    def add_args(a):
        for arg in a.posonlyargs + a.args + a.kwonlyargs + ([a.vararg] if a.vararg else []) + ([a.kwarg] if a.kwarg else []):
            names.add(arg.arg)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            if not isinstance(node, ast.ClassDef):
                add_args(node.args)
        elif isinstance(node, ast.Lambda):
            add_args(node.args)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
    return names


def undefined_in(path):
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    if any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in ast.walk(tree)):
        return []                                      # « import * » : impossible à contrôler
    known = bound_names(tree) | _BUILTINS
    return sorted({(n.id, n.lineno) for n in ast.walk(tree)
                   if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in known})


class UndefinedNamesTests(unittest.TestCase):
    def test_no_project_file_uses_an_undefined_name(self):
        problems = []
        for path in sorted(glob.glob(os.path.join(ROOT, "*.py"))):
            for name, line in undefined_in(path):
                problems.append(f"{os.path.basename(path)}:{line} {name}")
        self.assertEqual(problems, [], "Noms utilisés mais jamais définis ni importés :\n" + "\n".join(problems))

    def test_the_checker_detects_a_missing_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write("from os import path\n\ndef f(a):\n    b = a + 1\n    return QApplication.instance(), path, b, undefined_thing\n")
            self.assertEqual([n for n, _ in undefined_in(path)], ["QApplication", "undefined_thing"])


if __name__ == "__main__":
    unittest.main()
