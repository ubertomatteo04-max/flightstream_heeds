#!/usr/bin/env python3
"""
riepilogo_7b.py - Tabelle della Parte 7B (trim, carichi sezionali, sezione critica) dai DOE di heeds_mock.py:
    runs/vertici_trim  (8 vertici della 7A con trim)       runs/apertura  (b_half 2,112 e 3,04, c0, taper 1, twist 0)
    ..\\..\\..\\baseline_runs\\planform\\Design_1\\Analysis_1 (baseline con trim)
Per ogni design: alfa*, carichi (dal run ad alfa*), grandezze di missione, controllo di integrale di L' dy = L_N/2 e
|L - W|/W da run_info.txt, tempo. Scrive riepilogo_7b.md. Uso: python diagnostica\\planform\\riepilogo_7b.py
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BASE = os.path.abspath(os.path.join(REPO, "..", "baseline_runs", "planform", "Design_1", "Analysis_1"))


def kv(path):
    with open(path, encoding="utf-8") as f:
        return dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)


def checks(info_path):
    with open(info_path, encoding="utf-8") as f:
        txt = f.read()
    lp = re.search(r"integrale di L' dy = .*?scarto ([+-]?[\d.]+) %", txt)
    lw = re.search(r"\|L-W\|/W ([\d.]+) %", txt)
    return (lp.group(1) if lp else "–"), (lw.group(1) if lw else "–")


def fmt(v, nd):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "–"
    return "–" if x == -999 else f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def rows_of(folder):
    out = []
    with open(os.path.join(folder, "summary.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = os.path.join(folder, r["design"])
            out.append((r, kv(os.path.join(d, "results.txt")), checks(os.path.join(d, "run_info.txt"))))
    return out


HEAD = ("| design | c_root [m] | taper | twist [°] | b_half [m] | status | α* [°] | CL | D_N [N] | Di_N [N] | D0_N [N] | "
        "e_span | AR | CLmax_wing* | CL_req | η_stall* | Re_tip | M_root [N m] | ∫L′dy vs L_N/2 | \\|L−W\\|/W | tempo [s] |")


def line(name, res, chk, t):
    return (f"| {name} | {fmt(res['c_root'], 4)} | {fmt(res['taper'], 2)} | {fmt(res['twist_tip_deg'], 0)} | "
            f"{fmt(res['b_half'], 3)} | {res['status']} | {fmt(res['alpha_trim'], 3)} | {fmt(res['CL'], 4)} | "
            f"{fmt(res['D_N'], 3)} | {fmt(res['Di_N'], 3)} | {fmt(res['D0_N'], 3)} | {fmt(res['e_span'], 3)} | "
            f"{fmt(res['AR'], 2)} | {fmt(res['CLmax_wing'], 3)} | {fmt(res['CL_req'], 3)} | {fmt(res['eta_stall'], 3)} | "
            f"{fmt(res['Re_tip'], 0)} | {fmt(res['M_root_Nm'], 1)} | {chk[0].replace('.', ',')} % | "
            f"{chk[1].replace('.', ',')} % | {t} |")


def main():
    L = ["# Parte 7B – trim, carichi sezionali, sezione critica (generato da riepilogo_7b.py)", "",
         "Configurazione D, `case_semiala_planform.json` con trim (W = 147,15 N, V_cruise 20 m/s, α1 = 0°, α2 = 2°), "
         "tutte le grandezze di carico dal terzo run ad α*. \\* **clmax segnaposto 1,2 costante**: CLmax_wing e η_stall non "
         "sono stime fisiche. CL_req a V_min = 12 m/s.", ""]
    L += ["## Baseline (c0, taper 1, twist 0, b0)", "", HEAD, "|" + "---|" * 21]
    if os.path.isfile(os.path.join(BASE, "results.txt")):
        L.append(line("baseline", kv(os.path.join(BASE, "results.txt")), checks(os.path.join(BASE, "run_info.txt")), "–"))
    for title, sub in (("8 vertici della 7A (c_root 0,8/1,6 c0, taper 0,4/1,0, twist −5/+1, b_half = b0)", "vertici_trim"),
                       ("Estremi dell'apertura (c0, taper 1, twist 0)", "apertura")):
        L += ["", f"## {title}", "", HEAD, "|" + "---|" * 21]
        for r, res, chk in rows_of(os.path.join(HERE, "runs", sub)):
            L.append(line(r["design"], res, chk, r["wall_s"].replace(".", ",")))
    with open(os.path.join(HERE, "riepilogo_7b.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("scritto riepilogo_7b.md")


if __name__ == "__main__":
    main()
