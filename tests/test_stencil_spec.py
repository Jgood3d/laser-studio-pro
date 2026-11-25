"""Stencil Studio préparé pour une seconde interface : réglages lus dans la page web (spec.py), cadre
(models/frame.py) et calcul commun aux deux interfaces (controllers/service.py)."""
import os
import re
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from stencil_studio import spec  # noqa: E402
from stencil_studio.models.frame import centered_frame  # noqa: E402

try:
    import cv2  # noqa: F401
    from stencil_studio.controllers.service import StudioService
    from stencil_studio.models.session import StudioSession
except ImportError:          # OpenCV ou PyQt6 absents
    StudioService = None

IMAGE = os.path.join(REPO, "src", "stencil_studio", "exemple", "girl1.png")


class SpecTests(unittest.TestCase):
    """La page reste la seule source des réglages : la fenêtre Qt les lit tous, avec les mêmes valeurs."""

    def test_every_setting_of_the_page_is_read(self):
        with open(spec.UI_FILE, encoding="utf-8") as f:
            html = f.read()
        block = html[html.index("const SPEC = ["):]
        block = block[:block.index("\n];")]
        in_page = re.findall(r'\{k:"(\w+)"', block)
        self.assertEqual([item["k"] for item in spec.load().items()], in_page)

    def test_defaults_are_those_of_the_page_not_of_params(self):
        defaults = spec.load().defaults()
        self.assertEqual((defaults["dot_gamma"], defaults["min_dot_mm"]), (1.2, 0.4))   # core.Params : 1.0, 0.35

    def test_request_params_leave_out_the_interface_settings(self):
        s = spec.load()
        params = s.request_params(s.defaults())
        self.assertIn("size_mm", params)
        self.assertNotIn("previewRes", params)                   # réglage de l'interface (ui:1)
        self.assertEqual(set(params), {i["k"] for i in s.items() if not i.get("ui")})

    def test_groups_follow_the_mode(self):
        s = spec.load()
        halftone = [g["g"] for g in s.groups_for("halftone")]
        self.assertIn("Halftone dots", halftone)
        self.assertNotIn("Cleanup and bridges", halftone)
        self.assertNotIn("Subject", [g["g"] for g in s.groups_for("qr")])          # MODE_NOT
        self.assertFalse(s.row_shown("output", "stencil"))

    def test_js_literals(self):
        self.assertEqual(spec.js_to_json("{k:'a\"b', n:-1.5, ok:true, fmt:v => v + ' mm', l:[1,2,],}"),
                         {"k": 'a"b', "n": -1.5, "ok": True, "fmt": "custom", "l": [1, 2]})


class RowStateTests(unittest.TestCase):
    """Réglages grisés ou masqués selon les autres, comme refreshDisabled de la page."""

    def test_threshold_greys_out_with_the_automatic_threshold(self):
        s = spec.load()
        state = s.defaults()
        disabled, _hidden = s.row_states(state)
        self.assertIn("threshold", disabled)
        state["auto_threshold"] = False
        self.assertNotIn("threshold", s.row_states(state)[0])

    def test_mode_specific_settings_are_hidden_elsewhere(self):
        s = spec.load()
        state = dict(s.defaults(), output="stencil")
        hidden = s.row_states(state)[1]
        self.assertIn("qr_text", hidden)                              # réglage du QR code
        state["output"] = "qr"
        self.assertNotIn("qr_text", s.row_states(state)[1])

    def test_presets_offered_for_the_mode(self):
        s = spec.load()
        self.assertEqual(s.presets_for("halftone"), ["halftone"])
        self.assertIn("portrait", s.presets_for("stencil"))
        self.assertEqual(s.presets["halftone"]["output"], "halftone")


class FrameTests(unittest.TestCase):
    def test_largest_centred_frame_at_the_shape_ratio(self):
        circle = centered_frame({"shape": "circle"}, 1600, 1200)
        self.assertEqual((circle["cx"], circle["cy"], circle["w"], circle["aspect"]), (0.5, 0.5, 0.75, 1.0))
        full = centered_frame({"shape": "rect", "aspect": "full"}, 1600, 1200)
        self.assertEqual((full["w"], full["full"]), (1.0, True))

    def test_a_rotated_frame_is_placed_freely(self):
        from stencil_studio.models import frame
        state = {"shape": "circle", "rot": 10}
        f = frame.clamp(state, 1600, 1200, {"cx": 0.95, "cy": 0.5, "w": 3.0})
        self.assertEqual((f["cx"], f["w"]), (0.95, 3.0))           # peut déborder de la photo
        self.assertTrue(frame.request_frame(state, 1600, 1200, f)["free"])
        f = frame.clamp({"shape": "circle"}, 1600, 1200, {"cx": 0.95, "cy": 0.5, "w": 3.0})
        self.assertEqual((round(f["cx"], 3), f["w"]), (0.625, 0.75))   # sinon : contenu dans la photo


@unittest.skipIf(StudioService is None, "OpenCV ou PyQt6 non importables ici")
class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tempfile.TemporaryDirectory()
        os.environ["XDG_DATA_HOME"] = cls.data.name

    @classmethod
    def tearDownClass(cls):
        cls.data.cleanup()

    def test_service_gives_raw_results(self):
        service = StudioService(StudioSession())
        with open(IMAGE, "rb") as f:
            service.load_image(f.read(), "girl1.png")
        req = {"params": {"output": "stencil"}, "frame": {"cx": 0.5, "cy": 0.5, "w": 0.6}, "seq": 1, "work": 300}
        out = service.preview_result(req)
        self.assertEqual(out["image"].ndim, 3)                   # tableau RGB, pas une image « data: »
        self.assertIn("<svg", service.export_result(req)["svg"])



if __name__ == "__main__":
    unittest.main()
