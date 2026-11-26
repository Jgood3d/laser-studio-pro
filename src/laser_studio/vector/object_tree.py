"""Arbre des objets du dessin, sans Qt : les objets du dessus de la pile et, dans chaque groupe (GroupObject,
attribut `children`), ses objets, imbriqués à volonté. Retrouver les groupes qui contiennent un objet, les
recalculer après un changement d'un de leurs objets, retirer un objet de son groupe.

    chain = ancestors(document.objects, obj)       # [groupe du dessus, …, groupe direct de obj]
    top = refresh_ancestors(document.objects, obj)  # objet du dessus de la pile à redessiner
    remove_from_group(document.objects, obj)        # (objet du dessus modifié, ou objet vidé à retirer)
"""


def ancestors(objects, target):
    """Groupes qui contiennent `target`, du dessus de la pile jusqu'à son groupe direct ; [] si `target` est
    lui-même en haut de la pile (ou absent)."""
    def search(level, chain):
        for obj in level:
            if obj is target:
                return chain
            children = getattr(obj, "children", None)
            if children is not None:
                found = search(children, chain + [obj])
                if found is not None:
                    return found
        return None
    return search(objects, []) or []


def refresh_ancestors(objects, obj):
    """Recalcule les groupes qui contiennent `obj` (calque, tracé, objets ignorés), du plus proche au plus haut ;
    renvoie l'objet du dessus de la pile qui le contient (lui-même s'il est en haut)."""
    chain = ancestors(objects, obj)
    for group in reversed(chain):
        group.child_ignored_changed()
    return chain[0] if chain else obj


def remove_from_group(objects, obj):
    """Retire `obj` de son groupe ; un groupe vidé est retiré à son tour de son propre groupe. Renvoie
    (objet du dessus de la pile modifié, None), ou (None, objet du dessus à retirer du document) quand tout le
    groupe du dessus s'est vidé. `obj` doit être dans un groupe (voir ancestors)."""
    chain = ancestors(objects, obj)
    target = obj
    for level in range(len(chain) - 1, -1, -1):
        parent = chain[level]
        parent.children = [child for child in parent.children if child is not target]
        parent.child_ignored_changed()
        if parent.children:
            for upper in reversed(chain[:level]):
                upper.child_ignored_changed()
            return chain[0], None
        target = parent
    return None, target
