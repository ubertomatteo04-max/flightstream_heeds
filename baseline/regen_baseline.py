#!/usr/bin/env python3
"""
regen_baseline.py - Rigenera le baseline per HEEDS con run reali di FlightStream (come in HEEDS).

Per ogni modalita' (fixed, ccs): copia baseline\\<m>\\params_baseline.txt in
..\\..\\baseline_runs\\<m>\\Design_1\\Analysis_1\\params.txt, lancia run_fs.bat --config <JSON assoluto> con quella
cartella come cartella corrente, poi copia results.txt e run_info.txt in baseline\\<m>\\ (*_baseline.txt) e in
heeds_inputs\\<m>\\ (params.txt, results.txt). Prima di sovrascrivere confronta il nuovo results.txt con il
precedente e stampa le righe diverse (numero di riga, prima, dopo).

Uso:  python baseline\\regen_baseline.py [--only fixed|ccs] [--dry]   (--dry: solo confronto, non copia)
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RUNS = os.path.abspath(os.path.join(REPO, "..", "baseline_runs"))
CONFIG = {"fixed": "case_semiala_fixed.json", "ccs": "case_semiala_ccs.json", "planform": "case_semiala_planform.json"}


def lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(CONFIG))
    ap.add_argument("--dry", action="store_true", help="lancia e confronta, ma non copia")
    a = ap.parse_args()
    rc_all = 0
    for m in ([a.only] if a.only else list(CONFIG)):
        wd = os.path.join(RUNS, m, "Design_1", "Analysis_1")
        # si svuota la cartella invece di cancellarla: su Windows rmdir puo' fallire (Accesso negato) se un
        # altro processo (Esplora risorse, indicizzazione) tiene aperta la cartella
        os.makedirs(wd, exist_ok=True)
        for name in os.listdir(wd):
            p = os.path.join(wd, name)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        shutil.copy(os.path.join(HERE, m, "params_baseline.txt"), os.path.join(wd, "params.txt"))
        cmd = [os.path.join(REPO, "run_fs.bat"), "--config", os.path.join(REPO, CONFIG[m])]
        rc = subprocess.run(cmd, cwd=wd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT).returncode
        prev = os.path.join(HERE, m, "results_baseline.txt")
        new, old = lines(os.path.join(wd, "results.txt")), (lines(prev) if os.path.isfile(prev) else [])
        diff = [(i + 1, o, n) for i, (o, n) in enumerate(zip(old + [""] * (len(new) - len(old)), new)) if o != n]
        print(f"{m}: codice {rc}, {len(new)} righe (prima {len(old)}), righe diverse: {len(diff)}")
        for i, o, n in diff:
            print(f"   riga {i}: {o!r} -> {n!r}")
        rc_all |= rc
        if not a.dry:
            shutil.copy(os.path.join(wd, "results.txt"), os.path.join(HERE, m, "results_baseline.txt"))
            shutil.copy(os.path.join(wd, "run_info.txt"), os.path.join(HERE, m, "run_info_baseline.txt"))
            shutil.copy(os.path.join(HERE, m, "params_baseline.txt"), os.path.join(REPO, "heeds_inputs", m, "params.txt"))
            shutil.copy(os.path.join(wd, "results.txt"), os.path.join(REPO, "heeds_inputs", m, "results.txt"))
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
