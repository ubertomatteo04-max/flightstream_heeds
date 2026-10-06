"""Modalita' ccs_planform (v2.7.0): profilo, pianta, svergolamento, CCS generato, variabili ammesse.
Non lancia FlightStream (funzioni di geometry.py e --dry-run del driver).

    python -m unittest discover -s tests -v

Il confronto con FlightStream (taper 1, twist 0 = baseline ccs_wing: righe 2-45 identiche) e' nella baseline
baseline/planform (STATO.md, Parte 7A).
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import geometry  # noqa: E402

C0, B0 = 0.345091293, 2.64
LE = [0.002108707, 0.0, 0.01586614]
PROFILE = os.path.join(ROOT, "profiles", "vespa_root.dat")
SOURCE_CCS = os.path.join(ROOT, "..", "semiala_ccs_U120_V64_blended.csv")


def ccs_sections(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for ln in f:
            if ln.startswith("CrossSection"):
                v = [float(t) for t in ln.strip().split(";")[1:] if t.strip()]
                out.append([v[i:i + 3] for i in range(0, len(v), 3)])
    return out


def dry_run(params, geo_changes=None):
    """--dry-run di case_semiala_planform.json: (run_info, results, sezioni del CCS scritto)."""
    with open(os.path.join(ROOT, "case_semiala_planform.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["geometry"]["profile"] = PROFILE
    cfg["geometry"].update(geo_changes or {})
    if cfg["geometry"].get("size_by") == "S_half":
        cfg["case"].pop("c_root")
        cfg["case"]["S_half"] = 0.911041
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write(params)
        subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                        "--workdir", d, "--dry-run"], capture_output=True, text=True)
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            info = f.read()
        with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
            res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
        ccs = os.path.join(d, "case_ccs.csv")
        secs = ccs_sections(ccs) if os.path.isfile(ccs) else []
        head = []
        if os.path.isfile(ccs):
            with open(ccs, encoding="utf-8") as f:
                head = f.read().splitlines()[:5]
    return info, res, secs, head


class TestPlanformGeometry(unittest.TestCase):
    def test_profile_file(self):
        prof = geometry.read_selig(PROFILE)
        self.assertEqual(len(prof), 200)
        xs = [p[0] for p in prof]
        self.assertAlmostEqual(min(xs), 0.0, places=12)
        self.assertAlmostEqual(max(xs), 1.0, places=9)
        self.assertEqual(prof[xs.index(0.0)], (0.0, 0.0))

    def test_area_and_mac(self):
        g = geometry.planform_geometry(0.4, 0.5, 0.0, 2.0, 7, LE)
        self.assertAlmostEqual(g["S_half"], 2.0 * 0.4 * 1.5 / 2)
        self.assertAlmostEqual(g["MAC"], 2 / 3 * 0.4 * (1 + 0.5 + 0.25) / 1.5)
        self.assertAlmostEqual(g["c_tip"], 0.2)

    def test_quarter_chord_line_and_twist_sign(self):
        prof = geometry.read_selig(PROFILE)
        g = geometry.planform_geometry(C0, 0.5, 3.0, B0, 7, LE)
        secs = geometry.planform_sections(prof, g, 0.5, 3.0, 7, LE)
        self.assertEqual({len(s) for s in secs}, {200})                 # stesso numero di punti per sezione
        root, tip = secs[0], secs[-1]
        i_le = [p[0] for p in prof].index(0.0)
        # radice: nessuna rotazione, LE nel punto del CCS
        self.assertAlmostEqual(root[i_le][0], LE[0], places=12)
        # estremita': corda dimezzata, ruotata di +3 gradi a cabrare attorno a c/4: LE sale, TE scende
        c_tip = 0.5 * C0
        self.assertAlmostEqual(tip[i_le][1], B0)
        self.assertGreater(tip[i_le][2], LE[2])
        te_mid_tip = 0.5 * (tip[0][2] + tip[-1][2])
        te_mid_root = 0.5 * (root[0][2] + root[-1][2])
        self.assertLess(te_mid_tip - LE[2], (te_mid_root - LE[2]) * 0.5)
        # punto a c/4 fermo (sulla quota del LE): distanza LE-c/4 = c/4
        xc4 = LE[0] + C0 / 4
        d = math.hypot(tip[i_le][0] - xc4, tip[i_le][2] - LE[2])
        self.assertAlmostEqual(d, c_tip / 4, places=12)

    def test_baseline_sections_equal_source_ccs(self):
        info, res, secs, head = dry_run("aoa = 4\n")
        src = ccs_sections(SOURCE_CCS)
        self.assertEqual(len(secs), 7)
        for a, b in ((src[0], secs[0]), (src[1], secs[-1])):
            self.assertLess(max(abs(x - y) for p, q in zip(a, b) for x, y in zip(p, q)), 1e-9)
        self.assertEqual(head[:4], ["Aircraft;Vespa_planform", "ReferenceArea;1.82208203",
                                    "ReferenceLength;0.345091293", "Units;Meter"])
        self.assertEqual(head[4], "")
        self.assertEqual((res["Sref_m2"], res["Lref_m"], res["S_half"]), ("1.82208", "0.345091", "0.911041"))

    def test_size_by_S_half(self):
        info, res, secs, _ = dry_run("aoa = 4\ntaper = 0.5\n", {"size_by": "S_half"})
        self.assertAlmostEqual(float(res["c_root"]), 2 * 0.911041 / (B0 * 1.5), places=5)
        self.assertAlmostEqual(float(res["Sref_m2"]), 2 * 0.911041, places=5)
        info, res, secs, _ = dry_run("aoa = 4\nc_root = 0.3\n", {"size_by": "S_half"})
        self.assertIn("chiavi non ammesse", info)

    def test_invalid(self):
        for params in ("aoa = 4\ntaper = 0\n", "aoa = 4\ntwist_tip_deg = 25\n", "aoa = 4\nsideslip = 2\n"):
            info, res, secs, _ = dry_run(params)
            self.assertEqual(res["status"], "1", params)
            self.assertEqual(secs, [], params)


if __name__ == "__main__":
    unittest.main()
