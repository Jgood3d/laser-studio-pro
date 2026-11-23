"""Message traduit d'une erreur de générateur (boîte, puzzle, boule de Noël, porte-clés, gabarit).

Chaque générateur lève une exception qui porte un `code` et un dictionnaire `info` ; le texte est la clé
`<préfixe>.err.<code>` remplie avec `info`. Clé inconnue : `generic_key` si elle est donnée, sinon
`<préfixe>.error` suivi du code entre parenthèses."""
from laser_studio.i18n import tr


def generator_error_text(prefix, error, generic_key=None):
    key = f"{prefix}.err.{error.code}"
    text = tr(key)
    if text == key:
        if generic_key is None:
            return tr(f"{prefix}.error") + f" ({error.code})"
        text = tr(generic_key)
    try:
        return text.format(**(error.info or {}))
    except (KeyError, IndexError, ValueError):     # traduction sans les bons champs
        return text
