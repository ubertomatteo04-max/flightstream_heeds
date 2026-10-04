#!/usr/bin/env python3
"""
heeds_mock.py - Simula HEEDS in locale: per ogni design crea una cartella Design_NNN, ci scrive
params.txt, lancia fs_driver.py dentro quella cartella (come fara' HEEDS) e legge results.txt.
Alla fine scrive summary.csv con una riga per design.

Esempi:
    python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8
    python heeds_mock.py --config case_semiala_ccs.json --var aoa=2,6 --var chord_scale=0.9,1.1
    python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,4 --dry-run

Piu' opzioni --var producono tutte le combinazioni (piano fattoriale completo).
Le variabili non indicate prendono il valore del blocco 'case' del JSON.
ATTENZIONE: all'avvio vengono cancellate le cartelle Design_NNN gia' presenti in --out.
"""
import argparse
import csv
import itertools
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOW = ["status", "CL", "CD", "CMy", "L_over_D", "L_N", "D_N", "wall_s"]


def parse_var(text):
    """'aoa=0,2,4' -> ('aoa', [0.0, 2.0, 4.0])."""
    if "=" not in text:
        raise SystemExit(f"--var deve essere nome=v1,v2,... (ricevuto {text!r})")
    name, vals = text.split("=", 1)
    return name.strip(), [float(v) for v in vals.split(",") if v.strip()]


def read_results(path):
    """results.txt -> dizionario ordinato {chiave: testo del valore}."""
    out = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = (s.strip() for s in line.split("=", 1))
                    out[k] = v
    return out


def first_reason(design_dir):
    """Prima nota di run_info.txt (il motivo di uno status diverso da 0)."""
    path = os.path.join(design_dir, "run_info.txt")
    if not os.path.isfile(path):
        return "run_info.txt assente"
    with open(path, "r", encoding="utf-8") as f:
        notes = [ln[2:].strip() for ln in f if ln.startswith("- ")]
    return notes[0] if notes else ""


def clean_designs(out):
    """Cancella le cartelle Design_NNN di una simulazione precedente."""
    for name in os.listdir(out):
        if re.fullmatch(r"Design_\d{3,}", name) and os.path.isdir(os.path.join(out, name)):
            shutil.rmtree(os.path.join(out, name))


def run_design(i, names, values, a, config):
    """Crea Design_NNN, scrive params.txt, lancia il driver e restituisce la riga per il CSV."""
    d = os.path.join(a.out, f"Design_{i:03d}")
    os.makedirs(d)
    with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
        f.write("# scritto da heeds_mock.py (HEEDS sostituira' i valori a destra dell'uguale)\n")
        for n, v in zip(names, values):
            f.write(f"{n} = {v:g}\n")
    cmd = [sys.executable, os.path.join(HERE, "fs_driver.py"), "--config", config]
    if a.dry_run:
        cmd.append("--dry-run")
    if a.exe:
        cmd += ["--exe", a.exe]
    with open(os.path.join(d, "driver_stdout.txt"), "w", encoding="utf-8", errors="replace") as out:
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=d, stdout=out, stderr=subprocess.STDOUT).returncode
    row = {"design": os.path.basename(d), "exit_code": rc, "wall_s": f"{time.time() - t0:.1f}"}
    row.update({n: f"{v:g}" for n, v in zip(names, values)})
    row.update(read_results(os.path.join(d, "results.txt")))
    row["reason"] = first_reason(d)
    return row


def print_table(rows, names):
    """Tabella riassuntiva a schermo."""
    cols = ["design"] + names + SHOW + ["reason"]
    print("  ".join(f"{c:>10s}" if c != "reason" else c for c in cols))
    for r in rows:
        print("  ".join(f"{str(r.get(c, '')):>10s}" if c != "reason" else str(r.get(c, ""))[:70]
                        for c in cols))


def main(argv=None):
    """Crea i design, li lancia uno alla volta e scrive summary.csv."""
    ap = argparse.ArgumentParser(description="Simulatore di HEEDS per fs_driver.py")
    ap.add_argument("--config", required=True, help="JSON del caso")
    ap.add_argument("--var", action="append", required=True, help="nome=v1,v2,... (ripetibile)")
    ap.add_argument("--out", default="mock_runs", help="cartella dei design (default: mock_runs)")
    ap.add_argument("--dry-run", action="store_true", help="genera solo gli script, non lancia FlightStream")
    ap.add_argument("--exe", help="percorso di FlightStream da passare al driver")
    a = ap.parse_args(argv)

    config = os.path.abspath(a.config)
    a.out = os.path.abspath(a.out)
    os.makedirs(a.out, exist_ok=True)
    clean_designs(a.out)
    vars_ = [parse_var(v) for v in a.var]
    names = [n for n, _ in vars_]
    combos = list(itertools.product(*[vals for _, vals in vars_]))
    print(f"{len(combos)} design in {a.out}" + (" (dry-run)" if a.dry_run else ""))

    rows = []
    for i, values in enumerate(combos, 1):
        print(f"  Design_{i:03d}: " + ", ".join(f"{n}={v:g}" for n, v in zip(names, values)), flush=True)
        rows.append(run_design(i, names, values, a, config))

    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    summary = os.path.join(a.out, "summary.csv")
    with open(summary, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print()
    print_table(rows, names)
    print(f"\nRiepilogo: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
