#!/usr/bin/env python3
"""
collaudo.py - Collaudo end-to-end della v2.6.0: confronta le righe 1-39 dei results.txt dei DOE nuovi (run_fs.bat via
heeds_mock.py) con quelle dei DOE precedenti:
    fixed  mock_runs_collaudo_fixed (aoa 0-12, passo 2)   contro lo Study_2 di HEEDS (v2.4.1, schema 2)
    ccs    mock_runs_collaudo_ccs (chord_scale 0,9/1,0/1,1, aoa 4) contro mock_runs_ccs (v2.2.x, §3.4 di STATO.md)
La riga 1 (schema_version) cambia per costruzione (2 -> 4); le righe 2-39 devono coincidere. Scrive collaudo.md.

Uso:  python diagnostica\\collaudo\\collaudo.py [--study2 <cartella dello Study_2>]
"""
import argparse
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
STUDY2 = r"C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala_Study_2"


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip().split(" = ", 1) for ln in f if " = " in ln]


def by_key(folder_glob, key):
    out = {}
    for p in glob.glob(folder_glob):
        rows = read_lines(p)
        d = dict(rows)
        out[float(d[key])] = rows
    return out


def compare(new, old):
    """Righe 2-39 del file nuovo, confrontate PER CHIAVE (i DOE ccs precedenti hanno lo schema pre-v2.2.1, con un
    altro ordine). Restituisce (righe diverse, (diff assoluta, diff relativa, chiave) peggiore, chiavi assenti)."""
    nd, worst, absent = 0, (0.0, 0.0, "-"), []
    od = dict(old)
    for k1, v1 in new[1:39]:
        if k1 not in od:
            absent.append(k1)
            continue
        v0 = od[k1]
        if v1 != v0:
            nd += 1
        try:
            a, b = float(v1), float(v0)
            da = abs(a - b)
            dr = da / abs(b) if b not in (0.0, -999.0) else 0.0
            if dr > worst[1] or (dr == worst[1] and da > worst[0]):
                worst = (da, dr, k1)
        except ValueError:
            pass
    return nd, worst, absent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study2", default=STUDY2)
    a = ap.parse_args()
    L = ["# Collaudo end-to-end v2.6.0 (run_fs.bat via heeds_mock.py), generato da collaudo.py", "",
         "Righe 2–39 di results.txt confrontate per chiave con i DOE precedenti; la riga 1 (`schema_version`) cambia per costruzione.", ""]
    ok_all = True
    cases = [
        ("fixed", "aoa", os.path.join(REPO, "mock_runs_collaudo_fixed", "Design_*", "results.txt"),
         os.path.join(a.study2, "HEEDS_0", "Design*", "Analysis_1", "results.txt"), "Study_2 (HEEDS, v2.4.1)"),
        ("ccs_wing", "chord_scale", os.path.join(REPO, "mock_runs_collaudo_ccs", "Design_*", "results.txt"),
         os.path.join(REPO, "mock_runs_ccs", "Design_*", "results.txt"), "mock_runs_ccs (v2.2.x)"),
    ]
    for mode, key, gnew, gold, label in cases:
        new, old = by_key(gnew, key), by_key(gold, key)
        L += [f"## {mode} contro {label}", "",
              f"| {key} | status | CL | CD | CMy | L_N [N] | righe 1 (nuovo / prima) | righe 2–39 diverse | diff. max assoluta (chiave) | diff. max relativa | chiavi assenti nel riferimento |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in sorted(new):
            n = dict(new[x])
            if x not in old:
                L.append(f"| {x:g} | {n['status']} | – | – | – | – | – | riferimento mancante | – | – |")
                ok_all = False
                continue
            nd, worst, absent = compare(new[x], old[x])
            ok_all &= nd == 0
            L.append(f"| {x:g} | {n['status']} | {n['CL']} | {n['CD']} | {n['CMy']} | {n['L_N']} | "
                     f"{new[x][0][1]} / {dict(old[x]).get('schema_version', 'assente')} | {nd} | {worst[0]:.3g} ({worst[2]}) | "
                     f"{100 * worst[1]:.3g} % | {', '.join(absent) or '–'} |")
        L.append("")
    L.append(f"**ESITO: {'righe 2–39 identiche in tutti i design' if ok_all else 'DIFFERENZE: vedi tabelle'}**")
    with open(os.path.join(HERE, "collaudo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("COLLAUDO", "OK" if ok_all else "CON DIFFERENZE")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
