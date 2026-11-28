"""Catalogue et configuration de la barre d'outils principale.

Les actions personnalisables ont un identifiant stable (stocké dans les
préférences). Les widgets fixes (Générer le G-Code, Arrêt d'urgence, ko-fi)
ne figurent pas dans cette liste : ils restent toujours présents selon les
règles de sécurité / lisibilité décrites dans l'issue #190.
"""

from laser_studio.core.preferences import ui_preferences
from laser_studio.i18n import tr

# Clé QSettings (UIConfig).
PREF_KEY = "toolbar/actions"

# Identifiant réservé pour un séparateur dans la barre.
SEPARATOR = "separator"

# Ordre par défaut = comportement actuel de AppToolBar.
DEFAULT_ACTIONS = (
    "quit",
    SEPARATOR,
    "save_project",
    "open_project",
    SEPARATOR,
    "machine_params",
    SEPARATOR,
    "test_matrix",
    "stencil_studio",
    "separation",
    "png2svg",
    SEPARATOR,
    "estimate",
    SEPARATOR,
    "job_queue",
    "fullscreen",
)

# Actions proposées à l'utilisateur, groupées par menu (ordre d'affichage).
# Chaque entrée : (id, clé de traduction du libellé).
# L'icône est lue sur la QAction correspondante au moment de l'affichage.
CATALOG = (
    ("file", "menu.file", (
        ("quit", "menu.file.quit"),
        ("save_project", "menu.file.save_project"),
        ("open_project", "menu.file.open_project"),
    )),
    ("settings", "menu.settings", (
        ("machine_params", "menu.file.settings"),
    )),
    ("tools", "menu.tools", (
        ("test_matrix", "tab.test_matrix"),
        ("stencil_studio", "menu.tools.stencil_studio"),
        ("separation", "sep.tab_title"),
        ("png2svg", "png2svg.tab_title"),
        ("vector_import", "menu.tools.import_vector"),
        ("generator_box", "menu.tools.box"),
        ("generator_puzzle", "menu.tools.puzzle"),
        ("generator_ornament", "menu.tools.ornament"),
        ("generator_keychain", "menu.tools.keychain"),
        ("library", "menu.tools.library"),
        ("camera", "menu.tools.camera"),
        ("history", "menu.tools.history"),
    )),
    ("job", "menu.job", (
        ("estimate", "gcode.estimate"),
        ("gcode_import", "gcode.import"),
    )),
    ("view", "menu.view", (
        ("job_queue", "menu.view.job_queue"),
        ("fullscreen", "ui.vector_fullscreen"),
        ("bottom_panel", "menu.view.bottom_panel"),
    )),
)

# Ensemble de tous les identifiants d'actions valides (hors séparateur).
KNOWN_ACTION_IDS = frozenset(
    action_id
    for _group, _title, actions in CATALOG
    for action_id, _label in actions
)


def catalog_label(action_id):
    """Libellé traduit d'une action du catalogue, ou None si inconnu."""
    if action_id == SEPARATOR:
        return tr("toolbar.separator")
    for _group, _title, actions in CATALOG:
        for aid, key in actions:
            if aid == action_id:
                return tr(key)
    return None


def action_for_id(actions, action_id):
    """Retourne la QAction d'AppActions correspondant à `action_id`, ou None."""
    mapping = {
        "quit": actions.quit,
        "save_project": actions.save_project,
        "open_project": actions.open_project,
        "machine_params": actions.machine_params_window,
        "test_matrix": actions.test_matrix_window,
        "stencil_studio": actions.stencil_studio,
        "separation": actions.separation_tab,
        "png2svg": actions.png2svg_tab,
        "vector_import": actions.vector_import,
        "generator_box": actions.generator_actions.get("box"),
        "generator_puzzle": actions.generator_actions.get("puzzle"),
        "generator_ornament": actions.generator_actions.get("ornament"),
        "generator_keychain": actions.generator_actions.get("keychain"),
        "library": getattr(actions, "library", None),
        "camera": actions.camera,
        "history": actions.history,
        "estimate": actions.estimate,
        "gcode_import": actions.gcode_import,
        "job_queue": actions.job_queue,
        "fullscreen": actions.fullscreen,
        "bottom_panel": actions.bottom_panel,
    }
    return mapping.get(action_id)


def load_toolbar_actions():
    """Liste ordonnée d'identifiants (actions + 'separator') lue dans les préférences.

    Filtre les identifiants inconnus (versions futures ou anciennes) et
    retombe sur la configuration par défaut si la liste est vide ou absente.
    """
    raw = ui_preferences().get_list(PREF_KEY)
    if not raw:
        return list(DEFAULT_ACTIONS)
    cleaned = []
    for item in raw:
        item = str(item)
        if item == SEPARATOR or item in KNOWN_ACTION_IDS:
            cleaned.append(item)
    return cleaned if cleaned else list(DEFAULT_ACTIONS)


def save_toolbar_actions(action_ids):
    """Enregistre la configuration de la barre (liste d'identifiants)."""
    cleaned = [
        item for item in action_ids
        if item == SEPARATOR or item in KNOWN_ACTION_IDS
    ]
    ui_preferences().set(PREF_KEY, cleaned)
    return cleaned


def reset_toolbar_actions():
    """Rétablit la barre par défaut et la sauvegarde."""
    default = list(DEFAULT_ACTIONS)
    ui_preferences().set(PREF_KEY, default)
    return default
