"""Contratto di successo con HEEDS: codice di uscita da heeds.success_statuses e riga
'FS_DRIVER_RESULT status=<n> success=<0|1>' in fondo a run_info.txt e all'output del driver.

    python -m unittest discover -s tests -v

Non lancia FlightStream: usa --extract-only su carichi e log veri (aoa 4, tests/fixtures) e un VTK
illeggibile, che da' status 4 con CL/CD validi.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")


def run_driver(cfg_changes, loads="loads_a04.txt"):
    """--extract-only in una cartella temporanea; restituisce (codice, ultima riga stdout, run_info, results)."""
    with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
    for sec, val in cfg_changes.items():
        cfg[sec] = val
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write("aoa = 4\nvelocity = 20\n")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                            "--workdir", d, "--extract-only", "--loads", os.path.join(FIX, loads),
                            "--log", os.path.join(FIX, "log_a04.txt"), "--vtk", os.path.join(FIX, "vtk_rotto.txt")],
                           capture_output=True, text=True)
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            info = f.read().splitlines()
        with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
            res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
        return p.returncode, p.stdout.strip().splitlines()[-1], info, res


class TestSuccessContract(unittest.TestCase):
    def test_status4_default_is_failure(self):
        rc, last, info, res = run_driver({})
        self.assertEqual(res["status"], "4")
        self.assertEqual(res["CL"], "0.5767")                  # CL/CD validi anche con status 4
        self.assertEqual(rc, 1)
        self.assertEqual(info[-1], "FS_DRIVER_RESULT status=4 success=0")
        self.assertEqual(last, "FS_DRIVER_RESULT status=4 success=0")
        self.assertEqual(res["schema_version"], "8")

    def test_status4_accepted_in_doe(self):
        rc, last, info, res = run_driver({"heeds": {"success_statuses": [0, 4]}})
        self.assertEqual((res["status"], rc), ("4", 0))
        self.assertEqual(info[-1], "FS_DRIVER_RESULT status=4 success=1")
        self.assertEqual(last, "FS_DRIVER_RESULT status=4 success=1")

    def test_status1_never_success_with_0_4(self):
        rc, last, info, res = run_driver({"heeds": {"success_statuses": [0, 4]}}, loads="non_esiste.txt")
        # senza tabella dei carichi manca CDo: coefficienti incompleti -> status 1
        self.assertEqual((res["status"], rc), ("1", 1))
        self.assertEqual(last, "FS_DRIVER_RESULT status=1 success=0")

    def test_invalid_success_statuses(self):
        rc, last, info, res = run_driver({"heeds": {"success_statuses": [0, 9]}})
        self.assertEqual((res["status"], rc), ("1", 1))
        self.assertTrue(any("success_statuses" in ln for ln in info))
        self.assertEqual(info[-1], "FS_DRIVER_RESULT status=1 success=0")


if __name__ == "__main__":
    unittest.main()
