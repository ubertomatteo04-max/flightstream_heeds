"""Schema di results.txt: fixed e ccs_wing devono scrivere le stesse chiavi nello stesso ordine.

    python -m unittest discover -s tests -v

Usa --dry-run: FlightStream non viene lanciato (results.txt e' scritto comunque, con status 1).
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fs_driver  # noqa: E402

CASES = {"fixed": ("case_semiala_fixed.json", "aoa = 4\nvelocity = 20\n"),
         "ccs_wing": ("case_semiala_ccs.json", "aoa = 4\nvelocity = 20\nchord_scale = 1\n")}


def keys_of(path):
    with open(path, encoding="utf-8") as f:
        return [ln.split("=", 1)[0].strip() for ln in f if "=" in ln]


class TestResultsSchema(unittest.TestCase):
    def dry_run_keys(self, mode):
        config, params = CASES[mode]
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
                f.write(params)
            subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config",
                            os.path.join(ROOT, config), "--workdir", d, "--dry-run"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return keys_of(os.path.join(d, "results.txt"))

    def test_same_keys_all_modes(self):
        fixed, ccs = self.dry_run_keys("fixed"), self.dry_run_keys("ccs_wing")
        self.assertEqual(fixed, ccs)
        self.assertEqual(fixed, fs_driver.result_keys())

    def test_section_order(self):
        names = [s for s, _ in fs_driver.RESULTS_SCHEMA]
        self.assertEqual(names, ["stato", "carichi", "riferimenti", "strato_limite", "ingressi", "viscoso"])
        keys = fs_driver.result_keys()
        self.assertEqual(keys[:2], ["schema_version", "status"])
        self.assertEqual(keys[34:39], ["aoa", "velocity", "altitude", "sideslip", "chord_scale"])

    def test_schema_positions_frozen(self):
        """Posizioni dello schema 3 (v2.5.0; righe 1-39 = schema 2): se questo test fallisce, una chiave e' stata inserita in
        mezzo o tolta. Per una chiave nuova: aggiungerla in fondo, allungare questo elenco e
        incrementare SCHEMA_VERSION (e il numero atteso in test_schema_version)."""
        frozen = ["schema_version", "status", "converged", "iterations",
                  "CL", "CD", "CDi", "CDo", "CMx", "CMy", "CMz", "L_over_D", "L_N", "D_N",
                  "Sref_m2", "Lref_m", "Re_ref", "q_Pa",
                  "xtr_up", "xtr_lo", "H_te_up", "H_te_lo", "H_max_up", "H_max_lo", "cf_min_up", "cf_min_lo",
                  "area_frac_cf_neg", "H_max", "sep_max",
                  "sep_frac_up_le", "x_sep_up", "H_max_attached_up", "x_H_max_attached_up", "sep_frac_lo_te",
                  "aoa", "velocity", "altitude", "sideslip", "chord_scale",
                  # schema 3: in coda, le righe 1-39 (tagging HEEDS esistente) non cambiano
                  "viscous_coupling", "separation_model", "iterations_inviscid", "iterations_viscous",
                  "converged_viscous", "sep_marker_frac_up"]
        self.assertEqual(fs_driver.result_keys(), frozen)

    def test_schema_version(self):
        self.assertEqual(fs_driver.SCHEMA_VERSION, 3)
        config, params = CASES["fixed"]
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
                f.write(params)
            subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config",
                            os.path.join(ROOT, config), "--workdir", d, "--dry-run"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
                first = f.readline().strip()
        self.assertEqual(first, "schema_version = 3")       # testo cercato da "File contains" in HEEDS


if __name__ == "__main__":
    unittest.main()
