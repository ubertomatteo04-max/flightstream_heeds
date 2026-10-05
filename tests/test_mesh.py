"""Blocco 'mesh' del JSON (v2.6.0): righe Mesh_U/Mesh_V del CCS in ccs_wing; i default riproducono la mesh
validata (stesso testo del CCS di partenza). Non lancia FlightStream (--dry-run).

    python -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fs_driver  # noqa: E402
import geometry  # noqa: E402


def ccs_dry_run(changes):
    """ccs_wing --dry-run con modifiche al JSON; restituisce (run_info, righe Mesh_ del CCS scritto)."""
    with open(os.path.join(ROOT, "case_semiala_ccs.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["geometry"]["base_ccs"] = os.path.join(ROOT, "..", "semiala_ccs_U120_V64_blended.csv")
    for path, val in changes.items():
        sec, key = path.split(".")
        cfg.setdefault(sec, {})[key] = val
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write("aoa = 4\nchord_scale = 1\n")
        subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                        "--workdir", d, "--dry-run"], capture_output=True, text=True)
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            info = f.read()
        ccs, mesh = os.path.join(d, "case_ccs.csv"), []
        if os.path.isfile(ccs):
            with open(ccs, encoding="utf-8") as f:
                mesh = [ln.strip() for ln in f if ln.startswith("Mesh_")]
    return info, mesh


class TestMeshBlock(unittest.TestCase):
    def test_defaults_are_validated_mesh(self):
        cfg = {"geometry": {}, "mesh": dict(fs_driver.DEFAULTS["mesh"])}
        self.assertEqual(geometry.mesh_lines(cfg), ["Mesh_U;120;3;1.1;2", "Mesh_V;64;1;1.0;1"])
        # stesso testo del CCS di partenza (a parte gli zeri finali del growth rate)
        with open(os.path.join(ROOT, "..", "semiala_ccs_U120_V64_blended.csv"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("Mesh_U;120;3;1.10000;2", src)
        self.assertIn("Mesh_V;64;1;1.00000;1", src)

    def test_json_mesh_written_to_ccs(self):
        info, mesh = ccs_dry_run({"mesh.u_pts": 180, "mesh.v_pts": 96})
        self.assertEqual(mesh, ["Mesh_U;180;3;1.1;2", "Mesh_V;96;1;1.0;1"])

    def test_legacy_keys_rejected(self):
        info, mesh = ccs_dry_run({"geometry.mesh_u": 120})
        self.assertIn("mesh_u/mesh_v non sono piu' usate", info)

    def test_invalid_values(self):
        for ch in ({"mesh.u_pts": 1}, {"mesh.u_growth_type": 5}, {"mesh.v_growth_rate": 0}, {"mesh.u_pts": 80.5}):
            info, mesh = ccs_dry_run(ch)
            self.assertIn("mesh.", info, ch)
            self.assertEqual(mesh, [], ch)


class TestBluntTrailingEdge(unittest.TestCase):
    """te_type "blunt" (v2.6.0, opzione): facce di base + base region per i bordi d'uscita."""

    def test_blunt_script(self):
        with open(os.path.join(ROOT, "case_semiala_ccs.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["geometry"]["base_ccs"] = os.path.join(ROOT, "..", "semiala_ccs_U120_V64_blended.csv")
        cfg["geometry"]["te_type"] = "blunt"
        cfg["solver"]["init_surfaces"] = -1
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
                f.write("aoa = 4\nchord_scale = 1\n")
            subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                            "--workdir", d, "--dry-run"], capture_output=True, text=True)
            with open(os.path.join(d, "fs_script.txt"), encoding="utf-8") as f:
                script = f.read()
            with open(os.path.join(d, "case_ccs.csv"), encoding="utf-8") as f:
                ccs = f.read()
        self.assertIn("DELETE_SELECTED_FACES\n\nAUTO_DETECT_BASE_REGIONS\n\nSET_BASE_REGION_TRAILING_EDGES -1\n\n", script)
        self.assertIn("SURFACES -1", script)
        self.assertIn("Open_Cross_Sections\nBlunt_trailing_edges", ccs)
        self.assertNotIn("Mark_trailing_edges", ccs)

    def test_blunt_requires_all_surfaces(self):
        info, mesh = ccs_dry_run({"geometry.te_type": "blunt"})
        self.assertIn("init_surfaces = -1", info)

    def test_default_has_no_base_region(self):
        info, mesh = ccs_dry_run({})
        self.assertEqual(mesh, ["Mesh_U;120;3;1.1;2", "Mesh_V;64;1;1.0;1"])


if __name__ == "__main__":
    unittest.main()
