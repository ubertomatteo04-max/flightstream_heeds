"""Accoppiamento viscoso e modello di separazione (v2.5.0, esplorativo): lettura delle due fasi del log,
status 3 se la fase viscosa non converge, comandi dello script, controlli del JSON.

    python -m unittest discover -s tests -v

Non lancia FlightStream: --extract-only su log e carichi veri di un run accoppiato a 4 gradi
(tests/fixtures/*coupled*) e --dry-run per lo script.
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
import postprocess as pp  # noqa: E402


def run_driver(cfg_changes, extra, params="aoa = 4\nvelocity = 20\n"):
    """Driver fixed in una cartella temporanea: (codice, results, run_info, script o None)."""
    with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
    for path, val in cfg_changes.items():
        sec, key = path.split(".")
        cfg[sec][key] = val
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write(params)
        p = subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                            "--workdir", d] + extra, capture_output=True, text=True)
        with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
            res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            info = f.read()
        script = None
        if os.path.isfile(os.path.join(d, "fs_script.txt")):
            with open(os.path.join(d, "fs_script.txt"), encoding="utf-8") as f:
                script = f.read()
        return p.returncode, res, info, script


def extract(log_name, coupled=True):
    return run_driver({"solver.viscous_coupling": coupled},
                      ["--extract-only", "--loads", os.path.join(FIX, "loads_coupled_a04.txt"),
                       "--log", os.path.join(FIX, log_name), "--vtk", os.path.join(FIX, "vtk_rotto.txt")])


class TestCoupledLog(unittest.TestCase):
    def test_parse_two_phases(self):
        logd = pp.parse_log(os.path.join(FIX, "log_coupled_a04.txt"))
        self.assertEqual([p["iterations"] for p in logd["phases"]], [91, 126])
        self.assertAlmostEqual(logd["CL"], 0.55148)
        v = pp.viscous_convergence(logd, True, 1e-5)
        self.assertEqual(v, {"iterations_inviscid": 91, "iterations_viscous": 35, "converged_viscous": 1})

    def test_decoupled_log_has_one_phase(self):
        logd = pp.parse_log(os.path.join(FIX, "log_a04.txt"))
        self.assertEqual(len(logd["phases"]), 1)
        v = pp.viscous_convergence(logd, False, 1e-5)
        self.assertEqual(v, {"iterations_inviscid": 91, "iterations_viscous": 0, "converged_viscous": None})
        self.assertEqual(pp.viscous_convergence(logd, True, 1e-5)["converged_viscous"], 0)   # accoppiato senza fase 2

    def test_coupled_extract_ok(self):
        rc, res, info, _ = extract("log_coupled_a04.txt")
        self.assertEqual(res["status"], "4")           # VTK finto illeggibile: CL/CD validi, H/cf no
        self.assertEqual((res["viscous_coupling"], res["iterations_inviscid"], res["iterations_viscous"],
                          res["converged_viscous"], res["converged"]), ("1", "91", "35", "1", "1"))
        self.assertEqual(res["CL"], "0.5515")

    def test_viscous_not_converged_gives_status3(self):
        rc, res, info, _ = extract("log_coupled_a04_nonconv.txt")
        self.assertEqual((res["status"], rc), ("3", 1))
        self.assertEqual(res["converged_viscous"], "0")
        self.assertIn("fase viscosa (accoppiata) non convergente", info)

    def test_coupled_config_but_single_phase_log_gives_status3(self):
        rc, res, info, _ = run_driver({"solver.viscous_coupling": True},
                                      ["--extract-only", "--loads", os.path.join(FIX, "loads_a04.txt"),
                                       "--log", os.path.join(FIX, "log_a04.txt"), "--vtk", os.path.join(FIX, "vtk_rotto.txt")])
        self.assertEqual(res["status"], "3")
        self.assertIn("1 tabelle di iterazioni", info)


class TestSeparationScript(unittest.TestCase):
    def test_default_script(self):
        rc, res, info, script = run_driver({}, ["--dry-run"])
        self.assertIn("SET_SOLVER_VISCOUS_COUPLING DISABLE\n\nDELETE_SEPARATION -1\n\nLAMINAR_SEPARATION DISABLE\n\n", script)
        self.assertNotIn("CREATE_AIRFOIL_SEPARATION", script)
        self.assertEqual((res["viscous_coupling"], res["separation_model"]), ("0", "0"))
        # i comandi di fisica vanno prima di INITIALIZE_SOLVER
        self.assertLess(script.index("DELETE_SEPARATION"), script.index("INITIALIZE_SOLVER"))

    def test_airfoil_separation_script(self):
        rc, res, info, script = run_driver({"solver.viscous_coupling": True, "separation.model": "airfoil",
                                            "separation.surfaces": [1], "separation.laminar_separation": True},
                                           ["--dry-run"])
        self.assertIn("SET_SOLVER_VISCOUS_COUPLING ENABLE\n\nDELETE_SEPARATION -1\n\n"
                      "CREATE_AIRFOIL_SEPARATION AIRFOIL_SEP 1 DISABLE\n1\n\nLAMINAR_SEPARATION ENABLE\n\n", script)
        self.assertEqual((res["viscous_coupling"], res["separation_model"]), ("1", "1"))

    def test_all_surfaces(self):
        rc, res, info, script = run_driver({"separation.model": "airfoil", "separation.surfaces": -1}, ["--dry-run"])
        self.assertIn("CREATE_AIRFOIL_SEPARATION AIRFOIL_SEP -1 DISABLE\n\n", script)

    def test_vorticity_drag_boundaries(self):
        # default dei JSON della semiala: [1]; lista vuota (solo diagnostica) = CDi da pressione
        rc, res, info, script = run_driver({}, ["--dry-run"])
        self.assertIn("START_SOLVER\n\nSET_VORTICITY_DRAG_BOUNDARIES 1\n1\n\n", script)
        rc, res, info, script = run_driver({"solver.vorticity_drag_boundaries": []}, ["--dry-run"])
        self.assertIn("START_SOLVER\n\nDELETE_VORTICITY_DRAG_BOUNDARIES\n\n", script)
        self.assertNotIn("SET_VORTICITY_DRAG_BOUNDARIES", script)

    def test_invalid_separation(self):
        for change in ({"separation.model": "stratford"}, {"separation.surfaces": [0]}, {"separation.surfaces": []}):
            rc, res, info, script = run_driver(change, ["--dry-run"])
            self.assertEqual(res["status"], "1", change)
            self.assertIn("separation.", info, change)


if __name__ == "__main__":
    unittest.main()
