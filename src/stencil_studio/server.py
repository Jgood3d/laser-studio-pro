"""Serveur local de Stencil Studio : sert la page (ui/studio.html) et son
API (controllers/api.py), sur 127.0.0.1 seulement.

    python -m stencil_studio                  -> ouvre http://127.0.0.1:8765
    python -m stencil_studio --port 9000 --no-browser
    srv, port = start_server(8765)            # dans une autre application (fenêtre Qt de LSP)

Rien n'est envoyé sur Internet. Un seul serveur par processus : la session
de travail (image, repères, cache) est partagée par ses requêtes.
"""
import argparse
import json
import os
import re
import secrets
import socket
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from . import core
from .controllers.api import StudioApi
from .i18n import available_languages, detect_language, load_catalog
from .models.presets import PresetsStore
from .models.session import StudioSession

HERE = os.path.dirname(os.path.abspath(__file__))
UI_FILE = os.path.join(HERE, "ui", "studio.html")
# Jeton tiré à chaque lancement, glissé dans la page servie et exigé sur les routes /api/ (voir Handler._refused).
TOKEN = secrets.token_urlsafe(24)
DEFAULT_PORT = 8765

API = StudioApi(StudioSession())
PRESETS = PresetsStore()


def check_versions():
    """Affiche les versions des fichiers et signale un mélange (ex. paquet core ancien)."""
    ui_ver = "?"
    if os.path.isfile(UI_FILE):
        with open(UI_FILE, encoding="utf-8") as f:
            m = re.search(r'UI_VERSION = "([^"]+)"', f.read())
        ui_ver = m.group(1) if m else "ancienne version / old version"
    print(f"Versions : core {core.VERSION} | studio.html {ui_ver}")
    if ui_ver != core.VERSION:
        return [f"Fichiers de versions différentes / mixed versions : core={core.VERSION}, studio.html={ui_ver}."]
    return []


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # silence
        pass

    # -- helpers
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass  # le navigateur a annulé la requête (aperçu périmé)

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def _refused(self, u):
        """Vrai (et réponse 403 envoyée) pour une requête qui ne vient pas de la page du Studio : nom d'hôte
        autre que 127.0.0.1 / localhost (un site qui ferait pointer son nom vers 127.0.0.1), ou route /api/
        sans le jeton de la page (en-tête X-Stencil-Token, ou paramètre t pour une image)."""
        port = self.server.server_address[1]
        host_ok = self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")
        token = self.headers.get("X-Stencil-Token") or parse_qs(u.query).get("t", [""])[0]
        if host_ok and (not u.path.startswith("/api/") or secrets.compare_digest(token, TOKEN)):
            return False
        self._send(403, {"error": "forbidden"})
        return True

    # -- routes
    def do_GET(self):
        u = urlparse(self.path)
        session = API.session
        if self._refused(u):
            return
        try:
            if u.path in ("/", "/index.html", "/studio.html"):
                if not os.path.isfile(UI_FILE):
                    self._send(404, "studio.html introuvable / not found", "text/plain; charset=utf-8")
                else:
                    with open(UI_FILE, encoding="utf-8") as f:
                        page = f.read().replace("__STENCIL_TOKEN__", TOKEN)
                    self._send(200, page, "text/html; charset=utf-8")
            elif u.path == "/api/langs":
                self._send(200, {"langs": available_languages() or ["en"], "default": detect_language()})
            elif u.path == "/api/catalog":
                lang = parse_qs(u.query).get("lang", ["en"])[0]
                self._send(200, load_catalog(lang))
            elif u.path == "/api/presets":
                self._send(200, PRESETS.load())
            elif u.path == "/api/image":
                if not session.has_image():
                    self._send(404, {"error": "no image"})
                else:
                    self._send(200, session.disp_jpeg, "image/jpeg")
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        session = API.session
        if self._refused(u):
            return
        try:
            data = self._body()
            if u.path == "/api/upload":
                name = unquote(self.headers.get("X-Filename", "image"))
                with API.lock:
                    API.load_image(data, name)
                W, H = session.img.size
                self._send(200, {"width": W, "height": H, "v": session.img_id})
            elif u.path == "/api/hints":
                if not session.has_image():
                    self._send(400, {"error": "no image"})
                else:
                    with API.lock:
                        API.set_hints(data)
                    self._send(200, {"ok": True})
            elif u.path == "/api/presets":
                obj = json.loads(data.decode("utf-8"))
                if not isinstance(obj, dict):
                    self._send(400, {"error": "bad presets"})
                else:
                    PRESETS.save(obj)
                    self._send(200, {"ok": True})
            elif u.path == "/api/face":
                self._send(200, API.face() if session.has_image() else {"error": "no image"})
            elif u.path in ("/api/preview", "/api/export"):
                if not session.has_image():
                    self._send(400, {"error": "no image"})
                else:
                    req = json.loads(data.decode("utf-8"))
                    self._send(200, API.preview(req) if u.path == "/api/preview" else API.export(req))
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": str(e)})


def free_port(preferred):
    for port in (preferred, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def start_server(port=0):
    """Démarre le serveur dans un thread (sans navigateur). Retourne (serveur, port) : pour l'intégrer dans une
    autre application (fenêtre Qt de Laser Studio Pro). Arrêt : serveur.shutdown(); serveur.server_close()."""
    port = free_port(port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, name="stencil-studio", daemon=True).start()
    return srv, port


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m stencil_studio")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    problems = check_versions()
    if not os.path.isfile(UI_FILE):
        problems.append(f"Fichier manquant / missing file : {UI_FILE}")
    if problems:
        print("\n".join(["ATTENTION :"] + ["  - " + m for m in problems]))
        if not os.path.isfile(UI_FILE):
            return 1
    port = free_port(args.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print(f"Laser Stencil Studio : {url}   (Ctrl+C pour quitter / to quit)")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
