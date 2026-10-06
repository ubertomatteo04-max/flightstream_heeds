"""Foglio dei carichi in newton e D_N = Di_N + D0_N (v2.8.1, 7C.1, schema 7). Non lancia FlightStream.

    python -m unittest discover -s tests -v

tests/fixtures/loads_N_planform_trim.txt: export VERO (baseline ccs_planform trimmata, alfa* 1,4395 gradi, 2026-10-06):
etichette 'Fx, Fy, Fz, L, Di, Do, Mx, My, Mz', 'Force Units: Newtons'.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, ROOT)
import fs_driver  # noqa: E402
import postprocess as pp  # noqa: E402


class TestLoadsNewtons(unittest.TestCase):
    def test_parse_by_position(self):
        d = pp.parse_loads_newtons(os.path.join(FIX, "loads_N_planform_trim.txt"))
        self.assertAlmostEqual(d["CDo"], 5.4216)
        self.assertAlmostEqual(d["CL"], 147.1659)
        self.assertEqual(d["_labels"], ["Fx", "Fy", "Fz", "L", "Di", "Do", "Mx", "My", "Mz"])
        self.assertIn("Newton", d["_units"])

    def test_rejects_coefficients(self):
        with self.assertRaises(ValueError):
            pp.parse_loads_newtons(os.path.join(FIX, "loads_a04.txt"))      # foglio in coefficienti

    def test_D_N_is_sum(self):
        cfg = {"mission": {"W_N": None, "V_cruise": None, "V_min": None, "rho": None}, "_span": None, "_geo_span": None}
        res = {"q_Pa": 245.0, "Sref_m2": 1.82208, "_CL_log": 0.3297, "_CDi_log": 0.0025474, "CDo": 0.0121,
               "_D0_N_exp": 5.4016, "D_N": 6.51759}
        notes = []
        fs_driver.mission_metrics(cfg, res, {"rho": 1.225, "mu": 1.78e-5}, notes)
        self.assertAlmostEqual(res["D0_N"], 5.4016)
        self.assertEqual(res["D_N"], res["Di_N"] + res["D0_N"])                # esattamente
        self.assertIn("D0_N dal foglio in newton", notes[0])
        self.assertNotIn("ATTENZIONE", notes[0])                                # 5,4016 vs 5,4016 (CDo 0,0121)

    def test_quantization_warning(self):
        cfg = {"mission": {"W_N": None, "V_cruise": None, "V_min": None, "rho": None}}
        res = {"q_Pa": 245.0, "Sref_m2": 1.82208, "_CDi_log": 0.0025, "CDo": 0.0121, "_D0_N_exp": 5.50}
        notes = []
        fs_driver.mission_metrics(cfg, res, {"rho": 1.225, "mu": 1.78e-5}, notes)
        self.assertTrue(notes[0].startswith("ATTENZIONE"))

    def test_script_exports_newtons_after_coefficients(self):
        with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
                f.write("aoa = 4\n")
            subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                            "--workdir", d, "--dry-run"], capture_output=True, text=True)
            with open(os.path.join(d, "fs_script.txt"), encoding="utf-8") as f:
                s = f.read()
        i_coef = s.index("SET_LOADS_AND_MOMENTS_UNITS COEFFICIENTS")
        i_n = s.index("SET_LOADS_AND_MOMENTS_UNITS NEWTONS")
        self.assertLess(i_coef, s.index("loads.txt"))
        self.assertLess(s.index("loads.txt"), i_n)
        self.assertLess(i_n, s.index("loads_N.txt"))


if __name__ == "__main__":
    unittest.main()
