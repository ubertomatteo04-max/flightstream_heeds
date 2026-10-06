#!/usr/bin/env python3
"""
heeds_mock.py - Simula HEEDS in locale: per ogni design crea una cartella, ci scrive params.txt,
lancia il comando come fara' HEEDS (run_fs.bat --config <JSON assoluto>, con la cartella del
design come cartella corrente) e legge results.txt. Alla fine scrive summary.csv.

Esempi:
    python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8
    python heeds_mock.py --config case_semiala_ccs.json --var aoa=2,6 --var chord_scale=0.9,1.1
    python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,4 --dry-run
    python heeds_mock.py --config case_semiala_fixed.json --var aoa=4 --root "C:\\HEEDS prove\\studio 1"

Cartelle: senza --root, <--out>\\Design_NNN (default mock_runs); con --root, come HEEDS:
<root>\\Design_<N>\\<--analysis> (default Analysis_1; nomi esatti di HEEDS: DA VERIFICARE), anche
fuori dal repo e con spazi nel percorso.
Argomenti dopo "--" vanno al driver tali e quali (solo per prove, es. -- --extract-only --loads ...).
Piu' opzioni --var producono tutte le combinazioni (piano fattoriale completo).
Le variabili non indicate prendono il valore del blocco 'case' del JSON.
ATTENZIONE: all'avvio vengono cancellate le cartelle dei design gia' presenti (Design_NNN in --out,
Design_<N> in --root).
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
sys.path.insert(0, HERE)
import fs_driver  # noqa: E402  (solo per l'ordine delle colonne: fs_driver.result_keys)
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


def empty_tree(path):
    """Cancella tutti i file sotto path e le sottocartelle che si lasciano cancellare. Su Windows rmdir puo'
    fallire (Accesso negato) se un altro processo (Esplora risorse, indicizzazione) tiene aperta una cartella:
    in quel caso la cartella resta, vuota, e viene riusata."""
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except OSError:
                pass


def clean_designs(base, pattern):
    """Cancella le cartelle dei design di una simulazione precedente (solo quelle che rispettano pattern);
    se Windows nega la rimozione di una cartella, la svuota (empty_tree)."""
    for name in os.listdir(base):
        p = os.path.join(base, name)
        if re.fullmatch(pattern, name) and os.path.isdir(p):
            try:
                shutil.rmtree(p)
            except PermissionError:
                empty_tree(p)


def design_dir(i, a):
    """Cartella in cui gira il design i: <out>/Design_NNN oppure, con --root, <root>/Design_<i>/<analysis>."""
    if a.root:
        return os.path.join(a.root, f"Design_{i}", a.analysis)
    return os.path.join(a.out, f"Design_{i:03d}")


def driver_command(a, config):
    """Comando come in HEEDS: run_fs.bat (Windows) con il JSON assoluto; altrove python fs_driver.py."""
    if os.name == "nt":
        cmd = [os.path.join(HERE, "run_fs.bat"), "--config", config]
    else:
        cmd = [sys.executable, os.path.join(HERE, "fs_driver.py"), "--config", config]
    if a.dry_run:
        cmd.append("--dry-run")
    if a.exe:
        cmd += ["--exe", a.exe]
    return cmd + a.driver_args


def run_design(i, names, values, a, config):
    """Crea la cartella del design, scrive params.txt, lancia il comando con la cartella del design
    come cartella corrente e restituisce la riga per il CSV."""
    d = design_dir(i, a)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
        f.write("# scritto da heeds_mock.py (HEEDS sostituira' i valori a destra dell'uguale)\n")
        for n, v in zip(names, values):
            f.write(f"{n} = {v:g}\n")
    with open(os.path.join(d, "driver_stdout.txt"), "w", encoding="utf-8", errors="replace") as out:
        t0 = time.time()
        rc = subprocess.run(driver_command(a, config), cwd=d, stdout=out, stderr=subprocess.STDOUT).returncode
    name = f"Design_{i}" if a.root else os.path.basename(d)
    row = {"design": name, "exit_code": rc, "wall_s": f"{time.time() - t0:.1f}"}
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
    ap.add_argument("--root", help="cartella dello studio con la struttura di HEEDS (Design_<N>\\<analysis>), "
                                   "anche fuori dal repo e con spazi; summary.csv va qui")
    ap.add_argument("--analysis", default="Analysis_1", help="nome della cartella dell'analisi con --root")
    argv = sys.argv[1:] if argv is None else list(argv)
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    a = ap.parse_args(argv[:argv.index("--")] if "--" in argv else argv)
    a.driver_args = extra

    config = os.path.abspath(a.config)
    if a.root:
        a.root = a.out = os.path.abspath(a.root)
        os.makedirs(a.root, exist_ok=True)
        clean_designs(a.root, r"Design_\d+")
    else:
        a.out = os.path.abspath(a.out)
        os.makedirs(a.out, exist_ok=True)
        clean_designs(a.out, r"Design_\d{3,}")
    vars_ = [parse_var(v) for v in a.var]
    names = [n for n, _ in vars_]
    combos = list(itertools.product(*[vals for _, vals in vars_]))
    print(f"{len(combos)} design in {a.out}" + (" (dry-run)" if a.dry_run else ""))

    rows = []
    for i, values in enumerate(combos, 1):
        print(f"  {os.path.relpath(design_dir(i, a), a.out)}: " + ", ".join(f"{n}={v:g}" for n, v in zip(names, values)), flush=True)
        rows.append(run_design(i, names, values, a, config))

    # colonne fisse: design, codice di uscita, tempo, poi le chiavi di results.txt nell'ordine di
    # RESULTS_SCHEMA (uguale per tutte le modalita'), poi eventuali extra e il motivo dello status
    keys = ["design", "exit_code", "wall_s"] + fs_driver.result_keys()
    for r in rows:
        keys += [k for k in r if k not in keys and k != "reason"]
    keys.append("reason")
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
