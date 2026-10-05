"""Carico lungo l'apertura (v2.6.0, schema 4): lettura dei carichi di sezione di FlightStream, cl(eta),
controllo dell'integrale contro CL, chiavi cl_sec_* in coda a results.txt.

    python -m unittest discover -s tests -v

Non lancia FlightStream: tests/fixtures/sectional_a04.txt e' l'export vero (EXPORT_SURFACE_SECTIONAL_LOADS,
40 sezioni, fixed aoa 4, 2026-10-05); --extract-only per il driver.
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

SPAN = {"root": 0.0, "b_half": 2.64, "sign": 1.0}


def extract(extra):
    with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write("aoa = 4\n")
        subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                        "--workdir", d, "--extract-only", "--loads", os.path.join(FIX, "loads_a04.txt"),
                        "--log", os.path.join(FIX, "log_a04.txt"), "--vtk", os.path.join(FIX, "vtk_rotto.txt")] + extra,
                       capture_output=True, text=True)
        with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            info = f.read()
        csv_ok = os.path.isfile(os.path.join(d, "spanload.csv"))
    return lines, dict(ln.split(" = ", 1) for ln in lines), info, csv_ok


class TestSpanload(unittest.TestCase):
    def test_parse_real_export(self):
        rows = pp.parse_sectional_loads(os.path.join(FIX, "sectional_a04.txt"))
        self.assertEqual(len(rows), 40)
        self.assertAlmostEqual(rows[0]["chord"], 0.3451, places=4)

    def test_stations_cluster_to_tip(self):
        e = pp.spanload_stations(40)
        self.assertEqual(len(e), 40)
        self.assertLess(e[-1] - e[-2], e[1] - e[0])
        self.assertTrue(0 < e[0] < e[-1] < 1)

    def test_integral_matches_CL(self):
        rows = pp.parse_sectional_loads(os.path.join(FIX, "sectional_a04.txt"))
        m, tab, cl_int = pp.spanload_metrics(rows, 4.0, SPAN, 1.82208, 2.0)
        self.assertLess(abs(cl_int - 0.5767) / 0.5767, 0.01)       # entro l'1 % dal CL dei carichi
        self.assertGreater(m["cl_sec_max"], m["cl_sec_eta05"])
        self.assertAlmostEqual(m["cl_sec_root"], tab[0]["cl"])
        self.assertTrue(0.0 < m["eta_cl_sec_max"] < 0.5)

    def test_extract_with_spanload(self):
        lines, res, info, csv_ok = extract(["--spanload", os.path.join(FIX, "sectional_a04.txt")])
        self.assertEqual(len(lines), 49)
        self.assertNotEqual(res["cl_sec_eta05"], "-999")
        self.assertIn("scarto", info)
        self.assertTrue(csv_ok)

    def test_extract_without_spanload(self):
        lines, res, info, _ = extract([])
        self.assertEqual([res[k] for k in pp.SPANLOAD_KEYS], ["-999"] * 4)
        self.assertIn("carico in apertura non calcolato", info)

    def test_missing_spanload_file_is_status4(self):
        # VTK leggibile non disponibile nei fixture: lo status 4 qui viene anche dal VTK, si controlla la nota
        lines, res, info, _ = extract(["--spanload", os.path.join(FIX, "non_esiste.txt")])
        self.assertEqual(res["status"], "4")
        self.assertIn("carico in apertura: ValueError", info)


class TestTaggedRows(unittest.TestCase):
    def test_tagged_rows_do_not_move(self):
        """Righe di results.txt gia' taggate in HEEDS (Study_1, Study_2): 2 status, 5 CL, 6 CD, 10 CMy, 12 L_over_D."""
        keys = fs_driver.result_keys()
        self.assertEqual({n: keys[n - 1] for n in (2, 5, 6, 10, 12)},
                         {2: "status", 5: "CL", 6: "CD", 10: "CMy", 12: "L_over_D"})


if __name__ == "__main__":
    unittest.main()
