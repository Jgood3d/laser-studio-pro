#!/usr/bin/env python3
"""Détecte les attributs d'interface utilisés mais jamais construits.

    python tools/check_ui_attributes.py

Le programme est découpé en mixins qui partagent le même `self` : un mixin peut
lire `self.combo_material_bg` alors que le fichier qui le construit
(ui_setup_mixin.py) n'a pas été mis à jour. Python ne s'en aperçoit qu'à
l'exécution, au moment précis où la ligne est atteinte (AttributeError).

Ce contrôle statique relève, dans tous les fichiers du projet :
  - les attributs de type widget (combo_*, spin_*, chk_*, btn_*, lbl_*, txt_*,
    slider_*, list_*, edit_*, tab_*, ...) et les méthodes privées (_xxx) lus
    ou appelés sur `self` mais qui ne sont ni affectés (`self.x = ...`), ni
    définis (`def x`), ni créés par setattr, dans AUCUN fichier ;
  - en ignorant les usages protégés par un `hasattr(self, "x")` dans la même fonction.
Code de sortie 1 s'il en trouve (utile avant de pousser sur GitHub).
"""
import ast
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDGET_PREFIXES = ("combo", "spin", "chk", "btn", "lbl", "txt", "slider", "list", "edit", "radio",
                   "tab", "tabs", "progress", "stack", "menu", "action", "group", "box", "canvas",
                   "view", "widget", "dial", "table", "tree", "check", "button", "label", "text")
_WIDGET_RE = re.compile(r"^(?:%s)_\w+$" % "|".join(WIDGET_PREFIXES))


def checked(name):
    """Seuls les noms de widgets et les méthodes privées sont contrôlés : les autres
    peuvent venir de Qt (setWindowTitle, statusBar...), qu'on ne peut pas lister ici."""
    if name.startswith("__"):
        return False
    return bool(_WIDGET_RE.match(name)) or name.startswith("_")


def project_files(root=ROOT):
    return sorted(f for f in glob.glob(os.path.join(root, "*.py")))


def analyse(files):
    defined, uses = set(), []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), path)
        base = os.path.basename(path)
        for node in ast.walk(tree):
            # self.x = ..., self.x += ..., self.x: T = ..., for self.x in ..., with ... as self.x
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                targets = [node.target]
            elif isinstance(node, ast.With):
                targets = [i.optional_vars for i in node.items if i.optional_vars is not None]
            for t in targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                        defined.add(sub.attr)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)
            if isinstance(node, ast.ClassDef):
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for t in stmt.targets:
                            if isinstance(t, ast.Name):
                                defined.add(t.id)
                    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        defined.add(stmt.target.id)
            # setattr(self, "x", ...) : construction dynamique
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr"
                    and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)):
                defined.add(node.args[1].value)
        # usages, avec la fonction qui les contient (pour repérer les hasattr)
        for func in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            guarded = set()
            for n in ast.walk(func):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("hasattr", "getattr")
                        and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant)):
                    guarded.add(n.args[1].value)
            for n in ast.walk(func):
                if (isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)
                        and isinstance(n.value, ast.Name) and n.value.id == "self"):
                    uses.append((n.attr, base, n.lineno, n.attr in guarded))
    return defined, uses


def find_problems(files):
    defined, uses = analyse(files)
    problems = {}
    for name, base, line, guarded in uses:
        if name in defined or guarded or not checked(name):
            continue
        problems.setdefault(name, set()).add((base, line))
    return problems


def main():
    problems = find_problems(project_files())
    if not problems:
        print("OK : tous les widgets et méthodes privées utilisés sont construits quelque part.")
        return 0
    print("ATTRIBUTS UTILISÉS MAIS JAMAIS CONSTRUITS :")
    for name in sorted(problems):
        places = sorted(problems[name])
        shown = ", ".join(f"{b}:{l}" for b, l in places[:4]) + (" ..." if len(places) > 4 else "")
        print(f"  self.{name}   <- {shown}")
    print("\nUn fichier est probablement une ancienne version : vérifie que tous les fichiers livrés ensemble"
          "\nsont bien remplacés (typiquement ui_setup_mixin.py pour les widgets).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
