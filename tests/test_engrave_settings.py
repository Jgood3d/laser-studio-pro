"""Gravure d'une image : vitesse et puissance LUES dans le calque de gravure
(plus de copie séparée qui pourrait diverger du calque).
Découpe de l'ancien mode SVG : vitesse, puissance et passes (JobController)."""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from job_fakes import make_job
except ImportError:  # PyQt6... manquant
    make_job = None


@unittest.skipIf(make_job is None, "PyQt6 non importable ici")
class EngraveSettingsTests(unittest.TestCase):
    def make(self):
        job, _ = make_job()
        job.messages = []
        job.status.connect(job.messages.append)
        return job

    def fill_layer(self, job):
        return next(l for l in job.layers.layers if l.mode == "engrave_fill")

    def test_values_are_whole_numbers_within_bounds(self):
        job = self.make()
        job.set_engrave_settings(1234.7, 55.2)
        self.assertEqual((job.engrave_speed, job.engrave_power), (1234, 55))
        job.set_engrave_settings(5, 150)
        self.assertEqual((job.engrave_speed, job.engrave_power), (10, 100))   # 100 % reste possible

    def test_set_engrave_settings_writes_the_engrave_layer(self):
        job = self.make()
        job.set_engrave_settings(1500, 60)
        fill = self.fill_layer(job)
        self.assertEqual((fill.speed, fill.power), (1500, 60.0))

    def test_cut_values_are_whole_numbers_within_bounds(self):
        job = self.make()
        job.set_cut_settings(250.9, 95.4, 2.7)
        self.assertEqual((job.cut_speed, job.cut_power, job.cut_passes), (250, 95, 2))
        job.set_cut_settings(5, 100, 0)                   # 100 % et 0 passe restent possibles
        self.assertEqual((job.cut_speed, job.cut_power, job.cut_passes), (10, 100, 0))
        job.set_cut_settings(9000, 150, 500)
        self.assertEqual((job.cut_speed, job.cut_power, job.cut_passes), (5000, 100, 99))

    def test_image_uses_the_first_engrave_layer(self):
        job = self.make()
        fill = self.fill_layer(job)
        job.layers.update(fill.id, speed=1500, power=100)
        self.assertEqual(job.layers.engrave_layer(), fill)
        self.assertEqual((job.engrave_speed, job.engrave_power), (1500, 100))
        self.assertEqual(job.engrave_layer_label(), f"{fill.name}  [Gravure Remplie]")

    def test_layer_change_is_seen_without_any_copy(self):
        """Le cas du bug : le calque est modifié (saisie, matériau, profil),
        la génération lit aussitôt la nouvelle valeur."""
        job = self.make()
        fill = self.fill_layer(job)
        job.layers.update(fill.id, speed=1800, power=80)
        job.check_engrave_layer()
        self.assertEqual((job.engrave_speed, job.engrave_power), (1800, 80))
        self.assertEqual(job.messages, [])

    def test_without_engrave_layer_the_first_layer_is_used(self):
        job = self.make()
        for layer in [l for l in job.layers.layers if l.mode == "engrave_fill"]:
            job.layers.remove_layer(layer.id)
        self.assertEqual(job.layers.engrave_layer(), job.layers.layers[0])
        job.check_engrave_layer()                       # simple message
        self.assertEqual(len(job.messages), 1)


if __name__ == "__main__":
    unittest.main()
