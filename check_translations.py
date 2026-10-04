#!/usr/bin/env python3
"""Rapport complet sur les traductions (en plus de tests/test_translations.py).

    python tools/check_translations.py

Sections :
  A. Clés définies mais jamais référencées (même indirectement).
  B. Textes d'interface écrits en dur dans le code (non traduits).
  C. Valeurs identiques entre deux langues (traduction oubliée ?).
  D. Mélange tutoiement / vouvoiement par langue.
Ce rapport est INFORMATIF (code de sortie 0) : certains résultats sont voulus
(termes techniques, noms d'algorithmes, suffixes d'unités...).
"""
import ast
import collections
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import i18n  # noqa: E402

T = i18n.TRANSLATIONS
LANGS = list(i18n.SUPPORTED_LANGUAGES)
FILES = sorted(f for f in glob.glob(os.path.join(ROOT, "*.py")) if os.path.basename(f) != "i18n.py")


def parse(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), path)


def section_a():
    referenced = set()
    for path in FILES:
        for n in ast.walk(parse(path)):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in T:
                referenced.add(n.value)
    orphans = sorted(k for k in T if k not in referenced)
    print(f"\n== A. Clés jamais référencées dans le code : {len(orphans)} ==")
    for k in orphans:
        print(f"  {k}  |  {T[k]['fr'][:60]!r}")


UI_CTORS = {"QLabel", "QPushButton", "QCheckBox", "QGroupBox", "QRadioButton", "QAction",
            "QToolButton", "AutoHideLabel"}
UI_METHODS = {"setText", "setToolTip", "setWindowTitle", "setPlaceholderText", "addItem", "addItems",
              "addTab", "setTitle", "setStatusTip", "setLabelText", "setInformativeText", "addAction",
              "addMenu", "showMessage"}
MSGBOX = {"warning", "critical", "information", "question", "about"}


def _texty(s):
    s = s.strip()
    if not re.search(r"[A-Za-zÀ-ÿ]{3,}", s):
        return False
    return not s.startswith(("#", "background", "color", "font", "border", "QWidget"))


def section_b():
    found = collections.defaultdict(set)
    for path in FILES:
        tree = parse(path)
        parent = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}

        def inside_tr(node):
            while node in parent:
                node = parent[node]
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr":
                    return True
            return False

        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            name = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", None)
            args = None
            if name in UI_CTORS or name in UI_METHODS or (name in MSGBOX and isinstance(n.func, ast.Attribute)):
                args = n.args
            elif name == "append" and isinstance(n.func, ast.Attribute) and "console" in ast.unparse(n.func.value):
                args = n.args
            elif name == "addRow":
                args = n.args[:1]
            for a in args or []:
                for c in ast.walk(a):
                    if (isinstance(c, ast.Constant) and isinstance(c.value, str) and _texty(c.value)
                            and not inside_tr(c) and not re.fullmatch(r"[a-z_]+", c.value)):
                        found[os.path.basename(path)].add((c.lineno, name, c.value.replace("\n", "\\n")[:80]))
    total = sum(len(v) for v in found.values())
    print(f"\n== B. Textes d'interface probablement en dur : {total} ==")
    for f, items in found.items():
        print(f"  -- {f} ({len(items)})")
        for ln, name, s in sorted(items):
            print(f"     {ln}: {name}({s!r})")


def section_c():
    print("\n== C. Valeurs identiques entre langues (≥ 5 lettres) ==")
    for a, b in (("fr", "en"), ("en", "de"), ("en", "es"), ("fr", "es"), ("fr", "de")):
        same = [k for k, v in T.items() if v[a].strip() == v[b].strip()
                and len(re.sub(r"[^A-Za-zÀ-ÿ]", "", v[a])) >= 5]
        print(f"  {a}={b} : {len(same)}  {same}")


def section_d():
    R = {
        "fr": (r"\b(tu|ton|ta|tes|toi)\b|\bt'\w|-toi\b|\b(préfère|contacte|choisis|clique|sélectionne|vérifie|assure-toi)\b",
               r"\b(vous|votre|vos)\b|-vous\b|\b\w+ez\b"),
        "de": (r"\b(du|dein\w*|dich|dir)\b", r"\b(Sie|Ihr\w*|Ihnen)\b"),
        "es": (r"\b(tú|tu|tus|te|puedes|quieres|tienes|selecciona|elige|comprueba|asegúrate)\b",
               r"\b(usted|su|sus|puede|quiere|tiene|seleccione|elija|compruebe|asegúrese|imprima|pegue)\b"),
    }
    print("\n== D. Registre : informel (tu/du/tú) ou formel (vous/Sie/usted) ==")
    for lang, (inf, form) in R.items():
        flags = 0 if lang == "de" else re.I
        ki = sorted(k for k, v in T.items() if re.search(inf, v[lang], flags))
        kf = sorted(k for k, v in T.items() if re.search(form, v[lang], flags))
        print(f"  {lang}: informel={len(ki)}  formel={len(kf)}")
        print(f"     informel : {ki}")
        print(f"     formel   : {kf}")


if __name__ == "__main__":
    section_a()
    section_b()
    section_c()
    section_d()
