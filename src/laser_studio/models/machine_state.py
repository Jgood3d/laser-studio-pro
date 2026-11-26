"""État du graveur vu par l'application, et ce qu'on a le droit de lui envoyer dans chaque état. Une seule
table décide pour tous : les contrôleurs y demandent la permission avant d'envoyer, et les boutons s'activent
ou se grisent d'après elle. Sans Qt, testable seul.

L'état n'est jamais enregistré à part : il se déduit de ce qui est vrai à l'instant (port ouvert, activité en
cours, dernier état rapporté par GRBL), il ne peut donc pas diverger de la réalité.

    state = machine_state(connected=True, activity=None, grbl_state="Idle")    # READY
    allowed(state, JOG)                                                          # True
"""

# États
DISCONNECTED = "disconnected"     # port fermé
RECONNECTING = "reconnecting"     # coupure USB pendant un job : réouverture du port en cours
READY = "ready"                   # connecté, rien en cours
ALARM = "alarm"                   # GRBL en alarme (fin de course, reset en mouvement…) : déverrouiller ou homing
COMMANDS = "commands"             # commandes courtes en cours (déplacement, cadrage, console…)
HOMING = "homing"                 # cycle de homing ($H), jusqu'à 90 s
STREAMING = "streaming"           # job en cours d'envoi

# Activités lancées par l'application (MachineConnection les note au départ et les efface à la fin).
ACTIVITY_COMMANDS = "commands"
ACTIVITY_HOMING = "homing"
ACTIVITY_STREAMING = "streaming"

# Actions
CONNECT = "connect"               # ouvrir le port
DISCONNECT = "disconnect"         # fermer le port
JOG = "jog"                       # déplacements, cadrage, zéro, retour au zéro
CONSOLE = "console"               # commande tapée dans la console directe
HOME = "home"                     # homing
UNLOCK = "unlock"                 # $X
MACRO = "macro"                   # macro de l'utilisateur
SEND_JOB = "send_job"             # « Envoyer au laser », « Répéter », file d'attente
SETTINGS = "settings"             # lire ou écrire les réglages $$
REALTIME = "realtime"             # pause, reprise, reset, arrêt d'urgence

# Ce qui est permis dans chaque état.
# - COMMANDS garde déplacements et console actifs : une commande courte (un déplacement) dure quelques
#   millisecondes, les boutons ne clignotent pas ; la suivante attend simplement la fin de la précédente.
# - Pendant un homing ou un job, seules les commandes temps réel passent : tout le reste se glisserait
#   entre les lignes du job, ou fausserait la prise d'origine.
# - En alarme, GRBL refuse les mouvements : seuls le déverrouillage, le homing, la console (pour taper $X ou
#   $H) et la lecture des réglages restent utiles.
ALLOWED = {
    DISCONNECTED: {CONNECT},
    RECONNECTING: set(),
    READY: {DISCONNECT, JOG, CONSOLE, HOME, UNLOCK, MACRO, SEND_JOB, SETTINGS, REALTIME},
    ALARM: {DISCONNECT, CONSOLE, HOME, UNLOCK, SETTINGS, REALTIME},
    COMMANDS: {DISCONNECT, JOG, CONSOLE, REALTIME},
    HOMING: {REALTIME},
    STREAMING: {REALTIME},
}

# États où l'on attend la fin d'une activité (message « Graveur occupé »), par opposition à l'alarme.
BUSY = {COMMANDS, HOMING, STREAMING, RECONNECTING}


def machine_state(connected, activity=None, grbl_state=None, reconnecting=False):
    """État du graveur : `connected` (port ouvert), `activity` (ACTIVITY_*, ou None), `grbl_state` (dernier
    état rapporté par GRBL : « Idle », « Run », « Alarm »…), `reconnecting` (réouverture du port en cours)."""
    if reconnecting:
        return RECONNECTING
    if not connected:
        return DISCONNECTED
    if activity == ACTIVITY_STREAMING:
        return STREAMING
    if activity == ACTIVITY_HOMING:
        return HOMING
    if activity == ACTIVITY_COMMANDS:
        return COMMANDS
    if grbl_state == "Alarm":
        return ALARM
    return READY


def allowed(state, action):
    """Vrai si `action` est permise dans l'état `state`."""
    return action in ALLOWED.get(state, ())
