#!/usr/bin/env python3
"""
run_mesh_7e.py - 7E: convergenza di mesh per ccs_planform con trim (W = 147,15 N), configurazione D.

Parte da configs/esplorativi/case_planform_taper_S.json (size_by S_half, S_half 0,911041, b_half 2,64, twist 0) e
cambia solo il blocco mesh; ogni mesh gira con taper = 1,0 (baseline) e 0,38. JSON in configs/esplorativi/
(case_planform_mesh7e_<nome>.json), run in runs/mesh_7e/<nome>/.

Serie in apertura (U = 120): V43, V64 (= U120, mesh attuale), V96.
Serie in corda (V = 64): U80, U120, U180 con growth rate in corda scalato 1,1^(120/u_pts) (famiglia geometricamente
simile, come nella v2.6.0: con 1,1 fisso il primo pannello al LE scala di 3-4,5 invece di 1,5).

Uso:  python diagnostica\\planform\\run_mesh_7e.py [--only V43,U180]
"""
import argparse
import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CONFIGS = os.path.join(REPO, "configs", "esplorativi")
BASE = os.path.join(CONFIGS, "case_planform_taper_S.json")
MESHES = {
    "V43": {"v_pts": 43},
    "V64": {},
    "V96": {"v_pts": 96},
    "U80": {"u_pts": 80, "u_growth_rate": 1.15369},
    "U180": {"u_pts": 180, "u_growth_rate": 1.0656},
}


def write_config(name, changes):
    with open(BASE, encoding="utf-8") as f:
        cfg = copy.deepcopy(json.load(f))
    cfg["mesh"].update(changes)
    cfg["_nota"] = (f"DIAGNOSTICA 7E (convergenza di mesh, non per HEEDS): come case_planform_taper_S.json con mesh "
                    + (", ".join(f"{k} = {v}" for k, v in changes.items()) or "attuale (U 120, V 64)") + ".")
    path = os.path.join(CONFIGS, f"case_planform_mesh7e_{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    for name in [n for n in a.only.split(",") if n] or list(MESHES):
        cfg = write_config(name, MESHES[name])
        print(f"=== {name}", flush=True)
        subprocess.run([sys.executable, os.path.join(REPO, "heeds_mock.py"), "--config", cfg, "--var", "taper=1.0,0.38",
                        "--out", os.path.join(HERE, "runs", "mesh_7e", name)], cwd=REPO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
