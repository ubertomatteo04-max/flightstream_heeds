#!/usr/bin/env python3
"""
proto_te_blunt.py - Prova (v2.6.0, punto 3.4, SOLO DIAGNOSTICA) del bordo d'uscita tozzo fedele in ccs_wing:
CCS con Open_Cross_Sections + Blunt_trailing_edges (manuale 26.1 p. 84: facce di base conformi in un boundary
proprio), poi AUTO_DETECT_BASE_REGIONS e SET_BASE_REGION_TRAILING_EDGES -1 (p. 316) per marcare i bordi d'uscita
sulla base, INITIALIZE_SOLVER su tutte le superfici. Lo script del driver (te_type "blunt") viene modificato qui,
lanciato con FlightStream e letto con fs_driver --extract-only. Uscite in runs\\te_blunt\\a<aoa>\\.

Uso:  python diagnostica\\mesh\\proto_te_blunt.py [--aoa 4,12]
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXE = r"C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoa", default="4,12")
    a = ap.parse_args()
    with open(os.path.join(REPO, "case_semiala_ccs.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["geometry"]["base_ccs"] = os.path.abspath(os.path.join(REPO, cfg["geometry"]["base_ccs"]))
    cfg["geometry"]["te_type"] = "blunt"
    cfg["solver"]["init_surfaces"] = -1
    for aoa in [float(x) for x in a.aoa.split(",")]:
        wd = os.path.join(HERE, "runs", "te_blunt", f"a{aoa:g}")
        os.makedirs(wd, exist_ok=True)
        cj = os.path.join(wd, "case.json")
        with open(cj, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1)
        with open(os.path.join(wd, "params.txt"), "w", encoding="utf-8") as f:
            f.write(f"aoa = {aoa:g}\nchord_scale = 1\n")
        drv = [sys.executable, os.path.join(REPO, "fs_driver.py"), "--config", cj, "--workdir", wd]
        subprocess.run(drv + ["--dry-run"], capture_output=True)
        sp = os.path.join(wd, "fs_script.txt")
        with open(sp, encoding="utf-8") as f:
            s = f.read()
        mark = "DELETE_SELECTED_FACES\n\n"
        assert mark in s
        s = s.replace(mark, mark + "AUTO_DETECT_BASE_REGIONS\n\nSET_BASE_REGION_TRAILING_EDGES -1\n\n", 1)
        with open(sp, "w", encoding="utf-8") as f:
            f.write(s)
        with open(os.path.join(wd, "fs_stdout.txt"), "w") as out:
            subprocess.run([EXE, "-hidden", "-script", sp], cwd=wd, stdout=out, stderr=subprocess.STDOUT, timeout=600)
        subprocess.run(drv + ["--extract-only", "--loads", os.path.join(wd, "loads.txt"), "--log", os.path.join(wd, "fs_log.txt"),
                              "--vtk", os.path.join(wd, "surface.vtk"), "--spanload", os.path.join(wd, "spanload.txt")],
                       capture_output=True)
        with open(os.path.join(wd, "results.txt"), encoding="utf-8") as f:
            res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
        print(f"aoa {aoa:g}: status {res['status']} CL {res['CL']} CD {res['CD']} CMy {res['CMy']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
