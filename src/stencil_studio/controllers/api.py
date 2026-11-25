"""API de calcul de Stencil Studio pour la page web : ce que la page demande au serveur (aperçu,
détection du visage, export), sur l'image de la session. Le calcul est dans StudioService
(controllers/service.py, commun avec la fenêtre Qt) ; ici, les résultats sont mis en forme pour la page :
image d'aperçu en PNG « data: », fichiers binaires en base64.

    api = StudioApi(StudioSession())
    api.session.load_image(data, "photo.jpg")
    api.preview({"params": {...}, "frame": {...}, "seq": 1, "view": "result"})
    api.export({"params": {...}, "frame": {...}, "what": "box"})
"""
import base64
import io

from PIL import Image

from .service import GRAB_SIZE, StudioService, parse_guides, parse_manual, parse_sbox, version_info  # noqa: F401


def png_data_url(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class StudioApi(StudioService):
    """StudioService, réponses au format de la page web."""

    def preview(self, req):
        out = self.preview_result(req)
        if "image" in out:
            out["image"] = png_data_url(out["image"])
        return out

    def export(self, req):
        out = self.export_result(req)
        for raw, encoded in (("png", "png_b64"), ("diffuser_pdf", "diffuser_pdf_b64")):
            if raw in out:
                out[encoded] = base64.b64encode(out.pop(raw)).decode()
        return out
