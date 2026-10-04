"""Contrôle automatique des traductions (i18n.py) et de leur usage dans le code.

Échoue si :
  - une clé est définie deux fois dans TRANSLATIONS ;
  - une langue manque ou est vide pour une clé ;
  - les {placeholders} diffèrent d'une langue à l'autre (KeyError à l'affichage) ;
  - le nombre de retours à la ligne ou de %s diffère d'une langue à l'autre ;
  - le code appelle tr("clé") avec une clé absente de i18n.py ;
  - un appel tr("clé").format(...) ne fournit pas tous les {placeholders} d'une langue.

Pour un rapport plus complet (textes en dur, mélange tu/vous, valeurs identiques
entre langues) : python tools/check_translations.py

Lancer :  python -m unittest discover tests -v
"""
import ast
import collections
import glob
import os
import string
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    import i18n
except ImportError:  # PyQt6 absent
    i18n = None

_FMT = string.Formatter()


def placeholders(text):
    return {name for _, name, _, _ in _FMT.parse(text) if name is not None}


def project_files():
    return [f for f in glob.glob(os.path.join(ROOT, "*.py"))
            if os.path.basename(f) not in ("i18n.py",)]


def tr_calls():
    """(fichier, ligne, clé ou None) pour chaque tr(...) ; et les .format(...) associés."""
    calls, formats = [], []
    for path in project_files():
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "tr" and node.args:
                a = node.args[0]
                key = a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else None
                calls.append((os.path.basename(path), node.lineno, key))
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "format" and isinstance(node.func.value, ast.Call)
                    and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == "tr"
                    and node.func.value.args and isinstance(node.func.value.args[0], ast.Constant)):
                kws = {k.arg for k in node.keywords if k.arg}
                star = any(k.arg is None for k in node.keywords) or any(
                    isinstance(a, ast.Starred) for a in node.args)
                formats.append((os.path.basename(path), node.lineno,
                                node.func.value.args[0].value, kws, star))
    return calls, formats


@unittest.skipIf(i18n is None, "i18n non importable ici")
class TranslationTests(unittest.TestCase):
    def test_no_duplicate_keys(self):
        with open(os.path.join(ROOT, "i18n.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "TRANSLATIONS":
                counts = collections.Counter(
                    k.value for k in node.value.keys if isinstance(k, ast.Constant))
                dup = sorted(k for k, c in counts.items() if c > 1)
                self.assertEqual(dup, [], f"Clés définies plusieurs fois (la dernière écrase les autres) : {dup}")

    def test_every_key_has_every_language(self):
        langs = list(i18n.SUPPORTED_LANGUAGES)
        problems = []
        for key, values in i18n.TRANSLATIONS.items():
            for lang in langs:
                text = values.get(lang)
                if not isinstance(text, str) or not text.strip():
                    problems.append(f"{key} [{lang}]")
            problems += [f"{key} [langue inconnue {l}]" for l in values if l not in langs]
        self.assertEqual(problems, [], "Traductions manquantes ou vides : " + ", ".join(problems))

    def test_same_placeholders_in_all_languages(self):
        langs = list(i18n.SUPPORTED_LANGUAGES)
        problems = []
        for key, values in i18n.TRANSLATIONS.items():
            sets = {l: placeholders(values[l]) for l in langs if l in values}
            if len({frozenset(s) for s in sets.values()}) > 1:
                problems.append(f"{key}: " + ", ".join(f"{l}={sorted(s)}" for l, s in sets.items()))
        self.assertEqual(problems, [], "Placeholders différents selon la langue :\n" + "\n".join(problems))

    def test_same_newlines_and_printf_codes(self):
        import re
        langs = list(i18n.SUPPORTED_LANGUAGES)
        problems = []
        for key, values in i18n.TRANSLATIONS.items():
            nl = {l: values[l].count("\n") for l in langs if l in values}
            pc = {l: len(re.findall(r"%[sdif]", values[l])) for l in langs if l in values}
            if len(set(nl.values())) > 1:
                problems.append(f"{key}: retours à la ligne {nl}")
            if len(set(pc.values())) > 1:
                problems.append(f"{key}: codes %s/%d {pc}")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_every_literal_key_used_in_code_exists(self):
        calls, _ = tr_calls()
        missing = sorted({(f, ln, k) for f, ln, k in calls
                          if k is not None and k not in i18n.TRANSLATIONS})
        self.assertEqual(missing, [], "tr() avec une clé absente de i18n.py :\n"
                         + "\n".join(f"{f}:{ln} {k}" for f, ln, k in missing))

    def test_format_calls_provide_all_placeholders(self):
        _, formats = tr_calls()
        problems = []
        for f, ln, key, kws, star in formats:
            if star or key not in i18n.TRANSLATIONS:
                continue
            for lang, text in i18n.TRANSLATIONS[key].items():
                missing = placeholders(text) - kws
                if missing:
                    problems.append(f"{f}:{ln} {key} [{lang}] manque {sorted(missing)}")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
