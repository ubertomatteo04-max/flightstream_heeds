"""Trim, carichi in newton, sezione critica e grandezze di missione (v2.7.0, Parte 7B).
Non lancia FlightStream: i file in tests/fixtures/*planform_trim* e spanload_trim_{1,2}.csv vengono dal run reale della
baseline ccs_planform con trim (alfa1 0, alfa2 2, alfa* 1,43952 gradi; 2026-10-06).

    python -m unittest discover -s tests -v
"""
import csv
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

SPAN = {"root": 0.0, "b_half": 2.64, "sign": 1.0}
ASTAR, L_STAR = 1.43952, 147.181           # alfa* e L_N del terzo run della baseline


def read_tab(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]


class TestNewtonsAndCritical(unittest.TestCase):
    def test_newtons_integral_and_root_moment(self):
        rows = pp.parse_sectional_loads(os.path.join(FIX, "sectional_N_planform_trim.txt"))
        lp, lift, mom = pp.spanload_newtons(rows, ASTAR, SPAN)
        self.assertEqual(len(lp), 40)
        self.assertLess(abs(lift - L_STAR / 2) / (L_STAR / 2), 0.01)     # integrale di L' dy = L_N/2 entro l'1 %
        self.assertAlmostEqual(mom, 89.606, delta=0.01)
        # coerenza con i coefficienti: L' = cl q c (q = 245 Pa) sezione per sezione
        cf = pp.parse_sectional_loads(os.path.join(FIX, "sectional_planform_trim.txt"))
        _, tab, _ = pp.spanload_metrics(cf, ASTAR, SPAN, 1.82208, 2.0)
        for t in tab:
            self.assertAlmostEqual(lp[round(t["y_m"], 9)], t["cl"] * 245.0 * t["chord_m"], delta=0.02)

    def test_clmax_placeholder(self):
        f = pp.read_clmax_table(os.path.join(ROOT, "profiles", "clmax_vs_Re.csv"))
        self.assertEqual((f(1e4), f(3e5), f(5e6)), (1.2, 1.2, 1.2))

    def test_clmax_interpolation(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("# prova\nRe,clmax\n100000,1.0\n300000,1.4\n")
            fn = pp.read_clmax_table(p)
        self.assertAlmostEqual(fn(200000), 1.2)
        self.assertEqual((fn(5e4), fn(1e6)), (1.0, 1.4))

    def test_critical_section_baseline(self):
        t1, t2 = read_tab("spanload_trim_1.csv"), read_tab("spanload_trim_2.csv")
        cl_max, eta = pp.critical_section(t1, t2, 0.19052, 0.38380, lambda c: 1.2)
        self.assertAlmostEqual(cl_max, 1.08579, places=4)
        self.assertAlmostEqual(eta, 0.0588636, places=6)


class TestTrimAndMission(unittest.TestCase):
    def test_trim_alpha(self):
        self.assertAlmostEqual(fs_driver.trim_alpha(0.0, 2.0, 85.0411, 171.3322, 147.15), ASTAR, places=4)
        self.assertAlmostEqual(fs_driver.trim_alpha(0.0, 2.0, 10.0, 20.0, 40.0), 6.0)      # estrapolazione

    def test_mission_metrics(self):
        cfg = {"mission": {"W_N": 147.15, "V_cruise": 20.0, "V_min": 12.0, "rho": 1.225},
               "_span": {"b_half": 2.64}, "_geo_span": {"b_half": 2.64, "c_tip": 0.345091293}}
        res = {"q_Pa": 245.0, "Sref_m2": 1.82208, "_CL_log": 0.32970, "_CDi_log": 0.0025474, "CDo": 0.0121}
        fs_driver.mission_metrics(cfg, res, {"rho": 1.225, "mu": 1.78e-5})
        self.assertAlmostEqual(res["AR"], 5.28 ** 2 / 1.82208)
        self.assertAlmostEqual(res["e_span"], 0.3297 ** 2 / (3.141592653589793 * res["AR"] * 0.0025474))
        self.assertAlmostEqual(res["CL_req"], 147.15 / (0.5 * 1.225 * 144 * 1.82208))
        self.assertAlmostEqual(res["Re_tip"], 20 * 0.345091293 * 1.225 / 1.78e-5, places=3)
        self.assertAlmostEqual(res["Di_N"], 0.0025474 * 245 * 1.82208)
        self.assertAlmostEqual(res["D0_N"], 0.0121 * 245 * 1.82208)

    def test_check_mission(self):
        base = {"mission": {"W_N": 147.15, "V_cruise": 20.0, "V_min": 12.0, "rho": 1.225, "b_half_max": 3.04},
                "trim": {"enabled": True}}
        fluid = {"rho": 1.225, "mu": 1.78e-5}
        fs_driver.check_mission(base, {"b_half": 3.04, "velocity": 20.0}, fluid, [])
        with self.assertRaises(ValueError):
            fs_driver.check_mission(base, {"b_half": 3.05, "velocity": 20.0}, fluid, [])
        with self.assertRaises(ValueError):
            fs_driver.check_mission(base, {"b_half": 2.64, "velocity": 15.0}, fluid, [])
        no_w = json.loads(json.dumps(base))
        no_w["mission"]["W_N"] = None
        with self.assertRaises(ValueError):
            fs_driver.check_mission(no_w, {"b_half": 2.64, "velocity": 20.0}, fluid, [])

    def test_dry_run_with_trim(self):
        with open(os.path.join(ROOT, "case_semiala_planform.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["geometry"]["profile"] = os.path.join(ROOT, "profiles", "vespa_root.dat")
        cfg["mission"]["clmax_file"] = os.path.join(ROOT, "profiles", "clmax_vs_Re.csv")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
                f.write("aoa = 0\n")
            subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                            "--workdir", d, "--dry-run"], capture_output=True, text=True)
            with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
                info = f.read()
            with open(os.path.join(d, "fs_script.txt"), encoding="utf-8") as f:
                script = f.read()
        self.assertIn("trim: dry-run", info)
        self.assertIn("COMPUTE_SURFACE_SECTIONAL_LOADS COEFFICIENTS", script)
        self.assertIn("COMPUTE_SURFACE_SECTIONAL_LOADS NEWTONS", script)
        self.assertIn("SET_VORTICITY_DRAG_BOUNDARIES 1\n1\n", script)


if __name__ == "__main__":
    unittest.main()
