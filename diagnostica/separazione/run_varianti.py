#!/usr/bin/env python3
"""
run_varianti.py - Punto 4 bis, Parte 1: run diagnostici del modello di separazione (SOLO DIAGNOSTICA).

Parte da configs/esplorativi/case_semiala_fixed_coupled_sep.json (CS: fixed, accoppiato + Airfoil) e cambia una cosa alla volta:
    CS_Re22   V = 22 m/s (Re ~ 522 000, dentro il campo TRANSITIONAL)
    CS_turb   solver.bl_type = TURBULENT
    CS_lam    separation.laminar_separation = true
    DS        solver.viscous_coupling = false (disaccoppiato + Airfoil)
    CS_pdrag  solver.vorticity_drag_boundaries = [] -> DELETE_VORTICITY_DRAG_BOUNDARIES (CDi da pressione)
Scrive i JSON in configs/esplorativi/ e lancia heeds_mock.py con aoa = 0, 4, 12, 16 in runs\\<variante>\\.
I JSON di produzione non vengono toccati. CS di partenza: ..\\..\\mock_runs_visc_CS (stesso driver).

Uso:  python run_varianti.py [--only CS_turb,DS] [--aoa 0,4,12,16]
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
BASE = os.path.join(CONFIGS, "case_semiala_fixed_coupled_sep.json")


def _set(cfg, path, value):
    d = cfg
    keys = path.split(".")
    for k in keys[:-1]:
        d = d[k]
    d[keys[-1]] = value


VARIANTS = {
    "CS_Re22": {"case.velocity": 22.0},
    "CS_turb": {"solver.bl_type": "TURBULENT"},
    "CS_lam": {"separation.laminar_separation": True},
    "DS": {"solver.viscous_coupling": False},
    "CS_pdrag": {"solver.vorticity_drag_boundaries": []},
}


def write_config(name, changes):
    """JSON della variante in configs/esplorativi/: percorsi del template riportati rispetto alla nuova cartella."""
    with open(BASE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg = copy.deepcopy(cfg)
    tpl = os.path.normpath(os.path.join(CONFIGS, cfg["geometry"]["template_fsm"]))
    cfg["geometry"]["template_fsm"] = os.path.relpath(tpl, CONFIGS).replace("\\", "/")
    for k, v in changes.items():
        _set(cfg, k, v)
    cfg["_nota"] = (f"DIAGNOSTICA punto 4 bis, variante {name} di CS: "
                    + ", ".join(f"{k} = {json.dumps(v)}" for k, v in changes.items())
                    + ". Non usare in produzione.")
    os.makedirs(CONFIGS, exist_ok=True)
    path = os.path.join(CONFIGS, f"case_{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="varianti separate da virgola (default: tutte)")
    ap.add_argument("--aoa", default="0,4,12,16")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    names = [n for n in a.only.split(",") if n] or list(VARIANTS)
    for name in names:
        cfg = write_config(name, VARIANTS[name])
        out = os.path.join(HERE, "runs", name)
        cmd = [sys.executable, os.path.join(REPO, "heeds_mock.py"), "--config", cfg,
               "--var", f"aoa={a.aoa}", "--out", out] + (["--dry-run"] if a.dry_run else [])
        print(f"=== {name}: {' '.join(cmd)}", flush=True)
        subprocess.run(cmd, cwd=REPO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
