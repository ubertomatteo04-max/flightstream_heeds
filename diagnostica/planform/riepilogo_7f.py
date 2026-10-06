#!/usr/bin/env python3
"""
riepilogo_7f.py - 7F: clmax di XFOIL attivo (case_semiala_planform.json, mesh U120 x V64, trim W = 147,15 N).
Tabelle: baseline + 8 vertici della 7B (CLmax_wing, CL_req, margine = CLmax_wing/CL_req - 1, eta_stall, D_N,
ammissibile = margine >= 0) e corda minima della rettangolare non svergolata (margine = 0 per interpolazione lineare
in c_root). Scrive riepilogo_7f.md. Solo libreria standard.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BASE = os.path.join(REPO, "baseline", "planform", "results_baseline.txt")


def kv(path):
    with open(path, encoding="utf-8") as f:
        return {k: float(v) for k, v in (ln.strip().split(" = ", 1) for ln in f if " = " in ln)}


def doe(sub):
    folder = os.path.join(HERE, "runs", sub)
    out = []
    with open(os.path.join(folder, "summary.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            res = kv(os.path.join(folder, r["design"], "results.txt"))
            res["_t"], res["_name"] = float(r["wall_s"]), r["design"]
            out.append(res)
    return out


def it(v, nd):
    return f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def margin(r):
    return r["CLmax_wing"] / r["CL_req"] - 1.0


def row(name, r, t="–"):
    m = margin(r)
    return (f"| {name} | {it(r['c_root'], 4)} | {it(r['taper'], 2)} | {it(r['twist_tip_deg'], 0)} | {it(r['Sref_m2'], 4)} | "
            f"{int(r['status'])} | {it(r['alpha_trim'], 3)} | {it(r['CLmax_wing'], 4)} | {it(r['CL_req'], 4)} | "
            f"{it(100 * m, 1)} % | {it(r['eta_stall'], 3)} | {it(r['D_N'], 4)} | {'sì' if m >= 0 else '**no**'} | "
            f"{'sì' if r['eta_stall'] <= 0.6 else 'no'} | {t} |")


HEAD = ("| design | c_root [m] | taper | twist [°] | Sref [m²] | status | α* [°] | CLmax_wing | CL_req | margine | η_stall | "
        "D_N [N] | ammissibile (margine ≥ 0) | η_stall ≤ 0,6 | tempo [s] |")


def main():
    L = ["# 7F – clmax di XFOIL attivo (generato da riepilogo_7f.py)", "",
         "`case_semiala_planform.json`: `mission.clmax_file = xfoil/clmax_vs_Re.csv` (XFOIL 6.99, Ncrit 9; Re = V_min·c/ν, "
         "V_min 12 m/s), mesh U120 × V64, trim W = 147,15 N a 20 m/s, configurazione D. Margine = CLmax_wing / CL_req − 1; "
         "CL_req = W / (½ ρ V_min² Sref).", "", "## Baseline e 8 vertici della 7B (b_half 2,64 m)", "", HEAD, "|" + "---|" * 15]
    L.append(row("baseline", kv(BASE)))
    for r in doe("vertici_7f"):
        L.append(row(r["_name"], r, it(r["_t"], 1)))
    cs = sorted(doe("corda_7f"), key=lambda r: r["c_root"])
    L += ["", "## Corda minima della rettangolare non svergolata (taper 1, twist 0, b_half 2,64 m)", "", HEAD, "|" + "---|" * 15]
    for r in cs:
        L.append(row(r["_name"], r, it(r["_t"], 1)))
    cmin = None
    for a, b in zip(cs, cs[1:]):
        ma, mb = margin(a), margin(b)
        if ma <= 0 <= mb or mb <= 0 <= ma:
            cmin = a["c_root"] + (0 - ma) * (b["c_root"] - a["c_root"]) / (mb - ma)
    if cmin is not None:
        smin = 2 * 2.64 * cmin
        L += ["", f"**Corda minima ammissibile ≈ {it(cmin, 4)} m** (margine = 0 per interpolazione lineare fra i run): "
                  f"Sref minima ≈ **{it(smin, 3)} m²** (ala intera; AR {it(5.28 ** 2 / smin, 1)}), cioè "
                  f"{it(100 * (smin / 1.82208 - 1), 1)} % rispetto alla baseline (1,822 m²)."]
    else:
        L += ["", "Margine = 0 non attraversato nell'intervallo di c_root provato: estendere i run."]
    with open(os.path.join(HERE, "riepilogo_7f.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("scritto riepilogo_7f.md; c_min =", cmin)


if __name__ == "__main__":
    main()
