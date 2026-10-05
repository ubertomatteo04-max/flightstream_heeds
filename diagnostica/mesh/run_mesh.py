#!/usr/bin/env python3
"""
run_mesh.py - Convergenza di mesh (v2.6.0, configurazione D, ccs_wing, chord_scale 1): genera i JSON dei
livelli a partire da case_semiala_ccs.json cambiando solo il blocco 'mesh' (o geometry.te_type per le varianti
del bordo d'uscita) e lancia heeds_mock.py con aoa = 4 e 12 in runs\\<livello>\\.

Livelli (rapporto 1,5 per direzione, clustering invariato):
    coarse  u_pts  80, v_pts 43      medium  120 x 64 (attuale)      fine  180 x 96
Varianti del bordo d'uscita (mesh medium): te_sharp (te_type "sharp": sezioni chiuse, nessun raccordo).
Famiglia simile: coarse_g / fine_g con u_growth_rate = 1,1^1,5 = 1,15369 e 1,1^(1/1,5) = 1,0656.

Uso:  python diagnostica\\mesh\\run_mesh.py [--only coarse,fine] [--aoa 4,12]
"""
import argparse
import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BASE = os.path.join(REPO, "case_semiala_ccs.json")

LEVELS = {
    "coarse": {"mesh.u_pts": 80, "mesh.v_pts": 43},
    "medium": {},
    "fine": {"mesh.u_pts": 180, "mesh.v_pts": 96},
    "te_sharp": {"geometry.te_type": "sharp"},
    # famiglia geometricamente simile (Celik): growth rate in corda scalato come 1,1^(1/r) con r = 80/120, 180/120,
    # cosi' il primo pannello al LE scala anch'esso di circa 1,5 (con 1,1 fisso scala di 3-4,5)
    "coarse_g": {"mesh.u_pts": 80, "mesh.v_pts": 43, "mesh.u_growth_rate": 1.15369},
    "fine_g": {"mesh.u_pts": 180, "mesh.v_pts": 96, "mesh.u_growth_rate": 1.0656},
}


def write_config(name, changes):
    with open(BASE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg = copy.deepcopy(cfg)
    src = os.path.normpath(os.path.join(REPO, cfg["geometry"]["base_ccs"]))
    cfg["geometry"]["base_ccs"] = os.path.relpath(src, os.path.join(HERE, "config")).replace("\\", "/")
    for path, val in changes.items():
        sec, key = path.split(".")
        cfg[sec][key] = val
    cfg["_nota"] = f"DIAGNOSTICA convergenza di mesh, livello {name}: " + (
        ", ".join(f"{k} = {v}" for k, v in changes.items()) or "mesh attuale") + ". Non usare in produzione."
    os.makedirs(os.path.join(HERE, "config"), exist_ok=True)
    path = os.path.join(HERE, "config", f"case_mesh_{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--aoa", default="4,12")
    a = ap.parse_args()
    for name in [n for n in a.only.split(",") if n] or list(LEVELS):
        cfg = write_config(name, LEVELS[name])
        out = os.path.join(HERE, "runs", name)
        cmd = [sys.executable, os.path.join(REPO, "heeds_mock.py"), "--config", cfg,
               "--var", f"aoa={a.aoa}", "--var", "chord_scale=1", "--out", out]
        print(f"=== {name}", flush=True)
        subprocess.run(cmd, cwd=REPO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
