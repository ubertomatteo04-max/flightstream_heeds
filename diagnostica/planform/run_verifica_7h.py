#!/usr/bin/env python3
"""
run_verifica_7h.py - 7H: verifica del design migliore dello studio SHERPA completo (HEEDS, semiala_planform_full).

Rilancia baseline e design migliore (params.txt ESATTI: quello salvato da HEEDS per il migliore, Design129 "LatestBest",
e heeds_inputs/planform_full/params.txt per la baseline) con run_fs.bat, come HEEDS, su due mesh:
    U120V64  case_semiala_planform_full.json (mesh dello studio)
    U180V64  configs/esplorativi/case_planform_full_U180.json (u_pts 180, u_growth_rate 1.0656, come nella 7E)
Trim attivo, clmax di XFOIL Ncrit 9. Cartelle: runs/verifica_7h/<mesh>_<design>/.
Uso:  python diagnostica\\planform\\run_verifica_7h.py [--only U180V64]
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
STUDY = r"C:\Users\UtenteLocale\Desktop\heeds\semiala_planform_full\semiala_planform_full_full_planform"
PARAMS = {"baseline": os.path.join(REPO, "heeds_inputs", "planform_full", "params.txt"),
          "migliore": os.path.join(STUDY, "HEEDS_0", "Design129", "Analysis_1", "params.txt")}
FULL = os.path.join(REPO, "case_semiala_planform_full.json")
FINE = os.path.join(REPO, "configs", "esplorativi", "case_planform_full_U180.json")


def write_fine():
    with open(FULL, encoding="utf-8") as f:
        cfg = copy.deepcopy(json.load(f))
    cfg["_nota"] = ("VERIFICA 7H (non per HEEDS): come case_semiala_planform_full.json con mesh U180 x V64 "
                    "(u_growth_rate 1.0656, famiglia simile della 7E).")
    cfg["geometry"]["profile"] = "../../profiles/vespa_root.dat"
    cfg["mission"]["clmax_file"] = "../../xfoil/clmax_vs_Re.csv"
    cfg["mesh"].update({"u_pts": 180, "u_growth_rate": 1.0656})
    cfg["mesh"]["_nota"] = "mesh fine della verifica 7H: U180 x V64, growth rate in corda 1,1^(120/180)"
    cfg["heeds"].pop("inputs_dir", None)
    cfg["heeds"].pop("_nota_inputs_dir", None)
    with open(FINE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return FINE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    meshes = {"U120V64": FULL, "U180V64": write_fine()}
    for mesh, cfg in meshes.items():
        if a.only and mesh not in a.only.split(","):
            continue
        for name, params in PARAMS.items():
            wd = os.path.join(HERE, "runs", "verifica_7h", f"{mesh}_{name}")
            os.makedirs(wd, exist_ok=True)
            shutil.copy(params, os.path.join(wd, "params.txt"))
            print(f"=== {mesh} {name}", flush=True)
            r = subprocess.run([os.path.join(REPO, "run_fs.bat"), "--config", cfg], cwd=wd,
                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            print(f"    codice {r.returncode}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
