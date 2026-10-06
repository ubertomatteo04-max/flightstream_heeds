#!/usr/bin/env python3
"""
xfoil_polars.py - Parte 7D: polari XFOIL 6.99 del profilo di radice (profiles/vespa_root.dat) e clmax(Re).

Non usa FlightStream e non tocca il driver, il JSON ne' profiles/clmax_vs_Re.csv (segnaposto usato dagli studi HEEDS).
Per ogni (Re, Ncrit) due sessioni di XFOIL (file di comandi in work\\, subprocess con timeout): ASEQ 0 -> 18 e
0 -> -4 con passo 0,25, Mach 0, ITER 200, PPAR N = 180. I punti non convergenti mancano dalla polare.
clmax(Re) = massimo cl fra i punti convergenti; VALIDO solo se ci sono almeno 2 punti convergenti ad alfa maggiore
di quello del massimo (stallo visto davvero), altrimenti INCERTO.

Uscite (in questa cartella): polars\\polar_Re<Re>_N<n>.txt (grezze XFOIL) e .csv; clmax_vs_Re.csv (Ncrit 9,
colonna source); clmax.md (tabelle Ncrit 9 e 5, cl_alfa e cl a 4 gradi a Re 4,75e5, TE tozzo).
Uso:  python xfoil\\xfoil_polars.py [--xfoil <xfoil.exe>]
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORK = os.path.join(HERE, "work")
POLARS = os.path.join(HERE, "polars")
PROFILE = os.path.join(REPO, "profiles", "vespa_root.dat")
XFOIL_DEFAULT = os.path.abspath(os.path.join(REPO, "..", "tools", "XFOIL6.99", "xfoil.exe"))
RES = [1.0e5, 1.5e5, 2.0e5, 2.5e5, 3.0e5, 4.0e5, 5.0e5, 6.0e5, 8.0e5]
RE_FS = 4.75e5               # Re della semiala in FlightStream (V 20 m/s, corda 0,345 m)
NCRITS = [9, 5]
NPAN, ITER, DA, A_MIN, A_MAX = 180, 200, 0.25, -4.0, 18.0
TIMEOUT_S = 600


def run_xfoil(exe, name, cmds):
    inp = os.path.join(WORK, name + ".inp")
    with open(inp, "w", encoding="ascii") as f:
        f.write("\n".join(cmds) + "\n")
    with open(inp, encoding="ascii") as fin:
        try:
            r = subprocess.run([exe], stdin=fin, cwd=WORK, capture_output=True, text=True, timeout=TIMEOUT_S)
            out = r.stdout
        except subprocess.TimeoutExpired as e:
            out = (e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")) + \
                  f"\n*** TIMEOUT {TIMEOUT_S} s ***\n"
    with open(os.path.join(WORK, name + ".out"), "w", encoding="utf-8") as f:
        f.write(out)
    return out


def head():
    return ["PLOP", "G", "", "LOAD vespa_root.dat", "PPAR", f"N {NPAN}", "", "", "OPER", "MACH 0"]


def read_polar(path):
    rows, cols = [], None
    if not os.path.isfile(path):
        return rows
    with open(path, encoding="ascii", errors="replace") as f:
        for ln in f:
            t = ln.split()
            if t[:2] == ["alpha", "CL"]:
                cols = t
            elif cols and len(t) == len(cols):
                try:
                    rows.append({c: float(v) for c, v in zip(cols, t)})
                except ValueError:
                    pass
    return rows


def polar(exe, re_, ncrit):
    """Polare completa (due sequenze da 0): restituisce le righe convergenti ordinate per alfa."""
    tag = f"Re{int(re_):07d}_N{ncrit}"
    rows = {}
    for side, (a0, a1, da) in (("pos", (0.0, A_MAX, DA)), ("neg", (0.0, A_MIN, -DA))):
        pol = f"{tag}_{side}.txt"
        if os.path.exists(os.path.join(WORK, pol)):
            os.remove(os.path.join(WORK, pol))
        run_xfoil(exe, f"{tag}_{side}", head() + [f"VISC {re_:.0f}", "VPAR", f"N {ncrit}", "", f"ITER {ITER}",
                                                  "PACC", pol, "", f"ASEQ {a0} {a1} {da}", "PACC", "", "QUIT"])
        for r in read_polar(os.path.join(WORK, pol)):
            rows.setdefault(round(r["alpha"], 3), r)
    out = [rows[a] for a in sorted(rows)]
    # polare grezza (sequenza positiva, intestazione XFOIL) e CSV completo
    src = os.path.join(WORK, f"{tag}_pos.txt")
    if os.path.isfile(src):
        shutil.copy(src, os.path.join(POLARS, f"polar_{tag}_pos.txt"))
    srcn = os.path.join(WORK, f"{tag}_neg.txt")
    if os.path.isfile(srcn):
        shutil.copy(srcn, os.path.join(POLARS, f"polar_{tag}_neg.txt"))
    with open(os.path.join(POLARS, f"polar_{tag}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alpha", "CL", "CD", "CDp", "CM", "Top_Xtr", "Bot_Xtr"])
        for r in out:
            w.writerow([f"{r[k]:.6g}" for k in ("alpha", "CL", "CD", "CDp", "CM", "Top_Xtr", "Bot_Xtr")])
    n_req = int(round((A_MAX - A_MIN) / DA)) + 1
    return out, n_req


def clmax_of(rows):
    """(clmax, alfa_stallo, punti convergenti oltre il massimo, valido)."""
    if not rows:
        return None, None, 0, False
    k = max(range(len(rows)), key=lambda i: rows[i]["CL"])
    beyond = sum(1 for r in rows if r["alpha"] > rows[k]["alpha"])
    return rows[k]["CL"], rows[k]["alpha"], beyond, beyond >= 2


def lin_slope(rows, a_lo=-2.0, a_hi=6.0):
    pts = [(r["alpha"], r["CL"]) for r in rows if a_lo <= r["alpha"] <= a_hi]
    n = len(pts)
    if n < 3:
        return None, None
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
    b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    a = (sy - b * sx) / n
    return b, -a / b               # pendenza [/deg], alfa0 [deg]


def it(v, nd):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xfoil", default=XFOIL_DEFAULT)
    a = ap.parse_args()
    if not os.path.isfile(a.xfoil):
        sys.exit(f"xfoil.exe non trovato: {a.xfoil}")
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(POLARS, exist_ok=True)
    shutil.copy(PROFILE, os.path.join(WORK, "vespa_root.dat"))

    # bordo d'uscita: come XFOIL vede il profilo (stampa del caricamento e del pannellamento)
    geo_out = run_xfoil(a.xfoil, "geometria", head()[:8] + ["GDES", "", "QUIT"])
    gap = re.findall(r"(?i)blunt trailing edge\.\s*gap\s*=\s*[-+0-9.eE]+", geo_out)

    table = {}
    for n in NCRITS:
        for re_ in RES + [RE_FS]:
            rows, n_req = polar(a.xfoil, re_, n)
            cl, al, beyond, ok = clmax_of(rows)
            table[(n, re_)] = {"rows": rows, "n_req": n_req, "clmax": cl, "a_stall": al, "beyond": beyond, "ok": ok}
            print(f"Ncrit {n} Re {re_:.3g}: {len(rows)}/{n_req} convergenti, clmax {cl} a {al} ({beyond} punti oltre)",
                  flush=True)

    with open(os.path.join(HERE, "clmax_vs_Re.csv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# clmax(Re) del profilo profiles/vespa_root.dat, XFOIL 6.99 Ncrit 9, Mach 0, PPAR N 180 (Parte 7D).\n"
                "# Massimo cl fra i punti convergenti di alfa -4..18 passo 0,25. 'incerto' = meno di 2 punti convergenti\n"
                "# oltre il massimo (stallo non visto). NON ancora attivo nel JSON (mission.clmax_file).\n")
        f.write("Re,clmax,alpha_stall_deg,source\n")
        for re_ in RES:
            t = table[(9, re_)]
            if t["clmax"] is None:
                continue
            src = "XFOIL Ncrit 9" + ("" if t["ok"] else " (incerto: stallo non visto)")
            f.write(f"{re_:.0f},{t['clmax']:.4f},{t['a_stall']:.2f},{src}\n")

    L = ["# XFOIL 6.99 – polari e clmax(Re) di vespa_root.dat (Parte 7D, generato da xfoil_polars.py)", "",
         f"Profilo `profiles/vespa_root.dat` (200 punti, corda 1, TE tozzo 0,652 % c), PPAR N = {NPAN}, Mach 0, ITER {ITER}, "
         f"α da {it(A_MIN, 0)} a {it(A_MAX, 0)}° con passo {it(DA, 2)}° in due sequenze da 0°. clmax = massimo cl fra i punti convergenti; "
         "**valido** se almeno 2 punti convergenti oltre il massimo, altrimenti **incerto**.", "",
         "**TE tozzo:** XFOIL tiene il profilo aperto com'è (nessuna chiusura): il gap al TE entra come pannello di "
         "bordo d'uscita con la scia che parte dai due spigoli (trattamento standard di XFOIL per TE spessi)."
         + (f" XFOIL al caricamento: `{gap[0].strip()}` (= 0,652 % c)." if gap else " (XFOIL non stampa il valore del gap al caricamento.)"),
         ""]
    for n in NCRITS:
        L += [f"## Ncrit {n}", "", "| Re | punti convergenti | clmax | α_stall [°] | punti oltre il massimo | esito |",
              "|---|---|---|---|---|---|"]
        for re_ in RES:
            t = table[(n, re_)]
            L.append(f"| {re_:.2e}".replace(".", ",") + f" | {len(t['rows'])}/{t['n_req']} | {it(t['clmax'], 4)} | {it(t['a_stall'], 2)} | "
                     f"{t['beyond']} | {'valido' if t['ok'] else '**incerto**'} |")
        L.append("")
    L += [f"## Re {RE_FS:.3g}".replace(".", ",") + " (semiala in FlightStream, V 20 m/s, corda 0,345 m)", "",
          "| Ncrit | cl_α 2D (−2…6°) [/rad] | α₀ [°] | cl a 4° | clmax | α_stall [°] |", "|---|---|---|---|---|---|"]
    for n in NCRITS:
        t = table[(n, RE_FS)]
        sl, a0 = lin_slope(t["rows"])
        cl4 = next((r["CL"] for r in t["rows"] if abs(r["alpha"] - 4.0) < 1e-6), None)
        L.append(f"| {n} | {it(sl * 57.29578 if sl else None, 3)} | {it(a0, 2)} | {it(cl4, 4)} | {it(t['clmax'], 4)} | "
                 f"{it(t['a_stall'], 2)} |")
    L += ["", "Confronto con la sezione a metà apertura in FlightStream: rimandato (come da richiesta).", "",
          "Polari complete: `polars/polar_Re<Re>_N<n>.csv` (punti convergenti) e i file grezzi di XFOIL `_pos.txt`/`_neg.txt`."]
    with open(os.path.join(HERE, "clmax.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("scritti clmax_vs_Re.csv e clmax.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
