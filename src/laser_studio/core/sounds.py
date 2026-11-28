"""Sons de l'application, fabriqués à la volée : une note douce de carillon (attaque rapide, extinction
progressive, légère harmonique d'octave) plutôt qu'un bip strident. Aucun fichier livré, aucune dépendance :
le son est joué par le système (winsound sous Windows, pw-play / paplay / aplay sous Linux, afplay sous macOS).

    play(TICK)          # « tic » du compte à rebours avant la gravure
    play(GO)            # la gravure démarre
    if not play(TICK):  # aucun lecteur audio : à l'appelant de faire un bip système
        ...
"""
import io
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

RATE = 44100
# Lecteurs audio essayés dans l'ordre (Linux : PipeWire, PulseAudio, ALSA ; macOS).
PLAYERS = (("pw-play",), ("paplay",), ("aplay", "-q"), ("afplay",))


def chime(notes, duration, volume=0.35):
    """WAV (octets, mono 16 bits) : les fréquences `notes` (Hz) jouées ensemble pendant `duration` secondes,
    attaque de 5 ms (pas de clic) puis extinction exponentielle, chaque note avec son octave à 25 %."""
    frames = bytearray()
    for i in range(int(RATE * duration)):
        t = i / RATE
        envelope = min(1.0, t / 0.005) * math.exp(-5.0 * t / duration)
        sample = sum(math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t) for f in notes)
        frames += struct.pack("<h", int(32767 * volume * envelope * sample / (1.25 * len(notes))))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(bytes(frames))
    return buffer.getvalue()


TICK = "tick"       # La 5, court : une seconde de moins
GO = "go"           # Mi 5 + Si 5 (une quinte), plus long : la gravure démarre
SOUNDS = {TICK: lambda: chime((880.0,), 0.18), GO: lambda: chime((659.25, 987.77), 0.7)}


def sound_file(name):
    """Fichier WAV du son `name`, écrit une fois dans le dossier temporaire (les lecteurs lisent un fichier)."""
    path = os.path.join(tempfile.gettempdir(), f"laser-studio-pro-{name}.wav")
    if not os.path.isfile(path):
        with open(path, "wb") as f:
            f.write(SOUNDS[name]())
    return path


def play(name):
    """Joue le son `name` sans attendre la fin. False si aucun lecteur audio n'est disponible ou si la lecture
    échoue (le son n'est qu'un confort : jamais d'exception)."""
    try:
        path = sound_file(name)
        if sys.platform == "win32":
            import winsound      # module standard, Windows seulement
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        for player in PLAYERS:
            if shutil.which(player[0]):
                subprocess.Popen([*player, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
    except (OSError, RuntimeError):
        pass
    return False
