#!/usr/bin/env python3
"""
gci_7e.py - 7E: analisi della convergenza di mesh dei run di run_mesh_7e.py (runs/mesh_7e/<mesh>/Design_00{1,2}:
taper 1,0 e 0,38). Celik et al. (2008) con raffinamento in UNA direzione per serie: r = rapporto degli intervalli
(apertura: (v-1), corda: (u-1)), Fs = 1,25; ordine osservato p con l'iterazione di Celik; phi_ext di Richardson;
GCI_fine; per ogni livello errore stimato E = Fs |phi - phi_ext| / |phi_ext| (serve a scegliere la mesh piu' leggera).
Scrive gci_7e.md. Solo libreria standard.
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs", "mesh_7e")
FS = 1.25
QTY = ["Di_N", "D0_N", "D_N", "e_span", "alpha_trim", "CLmax_wing", "M_root_Nm"]
SERIES = {"apertura (U 120)": [("V43", 42), ("V64", 63), ("V96", 95)],
          "corda (V 64, growth scalato)": [("U80", 79), ("V64", 119), ("U180", 179)]}
MESH_TXT = {"V43": "U120 × V43", "V64": "U120 × V64 (attuale)", "V96": "U120 × V96", "U80": "U80 × V64",
            "U180": "U180 × V64", "U80V43": "U80 × V43"}
LL = {1.0: 0.91, 0.38: 0.98}      # e della linea portante citato nella richiesta


def kv(path):
    with open(path, encoding="utf-8") as f:
        return dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)


def load(mesh):
    folder = os.path.join(RUNS, mesh)
    out = {}
    if not os.path.isfile(os.path.join(folder, "summary.csv")):
        return out
    with open(os.path.join(folder, "summary.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            res = kv(os.path.join(folder, r["design"], "results.txt"))
            out[round(float(res["taper"]), 2)] = {**{k: float(res[k]) for k in QTY}, "status": res["status"],
                                                   "t": float(r["wall_s"])}
    return out


def celik(f1, f2, f3, r21, r32):
    e21, e32 = f2 - f1, f3 - f2
    out = {"p": None, "ext": None, "gci": None, "tipo": "–"}
    if e21 == 0 and e32 == 0:
        out.update(tipo="costante", ext=f1, gci=0.0)
        return out
    if e21 == 0 or e32 == 0:
        out["tipo"] = "non determinabile"
        return out
    R = e21 / e32
    out["tipo"] = "monotona" if 0 < R < 1 else ("oscillante" if -1 < R < 0 else "divergente")
    s = 1.0 if e32 / e21 > 0 else -1.0
    p, q = 1.0, 0.0
    for _ in range(200):
        pn = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        try:
            q = math.log((r21 ** pn - s) / (r32 ** pn - s))
        except ValueError:
            break
        if abs(pn - p) < 1e-10:
            p = pn
            break
        p = pn
    rp = r21 ** p
    out["p"] = p
    if rp != 1:
        out["ext"] = (rp * f1 - f2) / (rp - 1)
        out["gci"] = 100 * FS * abs((f1 - f2) / f1) / (rp - 1)
    return out


def it(v, nd):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def main():
    data = {m: load(m) for m in MESH_TXT}
    L = ["# 7E – convergenza di mesh di ccs_planform con trim (generato da gci_7e.py)", "",
         "`configs/esplorativi/case_planform_mesh7e_<mesh>.json` (= case_planform_taper_S.json con il solo blocco mesh "
         "cambiato), S_half 0,911041, b_half 2,64, twist 0, trim W = 147,15 N, configurazione D. CLmax_wing con clmax "
         "**segnaposto**. Celik et al. (2008): r = rapporto degli intervalli nella direzione raffinata, Fs = 1,25; "
         "E = Fs·|φ − φ_ext|/|φ_ext| = errore stimato di ogni livello.", "",
         "| mesh | tempo taper 1 / 0,38 [s] | status |", "|---|---|---|"]
    for m, txt in MESH_TXT.items():
        d = data[m]
        if d:
            L.append(f"| {txt} | {it(d[1.0]['t'], 1)} / {it(d[0.38]['t'], 1)} | {d[1.0]['status']} / {d[0.38]['status']} |")
    err = {}          # (serie, taper, mesh, qty) -> E %
    ext = {}
    for sname, levels in SERIES.items():
        (m3, n3), (m2, n2), (m1, n1) = levels
        r21, r32 = n1 / n2, n2 / n3
        for tp in (1.0, 0.38):
            L += ["", f"## Serie {sname}, taper {it(tp, 2)} (r21 = {it(r21, 3)}, r32 = {it(r32, 3)})", "",
                  "| grandezza | coarse | medium | fine | convergenza | p | φ_ext | GCI_fine [%] | E coarse / medium / fine [%] |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for k in QTY:
                f3, f2, f1 = data[m3][tp][k], data[m2][tp][k], data[m1][tp][k]
                g = celik(f1, f2, f3, r21, r32)
                nd = 5 if k in ("Di_N", "D_N", "e_span") else 4
                es = [FS * abs(f - g["ext"]) / abs(g["ext"]) * 100 if g["ext"] else None for f in (f3, f2, f1)]
                for m, e in zip((m3, m2, m1), es):
                    err[(sname, tp, m, k)] = e
                ext[(sname, tp, k)] = g["ext"]
                L.append(f"| {k} | {it(f3, nd)} | {it(f2, nd)} | {it(f1, nd)} | {g['tipo']} | {it(g['p'], 2)} | "
                         f"{it(g['ext'], nd)} | {it(g['gci'], 3)} | {' / '.join(it(e, 3) for e in es)} |")
    # (a) e contro la linea portante
    L += ["", "## (a) Scarto di e_span dalla linea portante", "", "| taper | linea portante | e mesh attuale | e_ext apertura | "
          "e_ext corda | e fine (V96) | e fine (U180) |", "|---|---|---|---|---|---|---|"]
    for tp in (1.0, 0.38):
        L.append(f"| {it(tp, 2)} | ≈ {it(LL[tp], 2)} | {it(data['V64'][tp]['e_span'], 4)} | "
                 f"{it(ext[('apertura (U 120)', tp, 'e_span')], 4)} | {it(ext[('corda (V 64, growth scalato)', tp, 'e_span')], 4)} | "
                 f"{it(data['V96'][tp]['e_span'], 4)} | {it(data['U180'][tp]['e_span'], 4)} |")
    # (b) stabilita' della differenza
    L += ["", "## (b) Differenza di Di_N e D_N fra taper 1 e 0,38", "",
          "| mesh | Di_N taper 1 [N] | Di_N 0,38 [N] | ΔDi [%] | ΔD [%] |", "|---|---|---|---|---|"]
    dd = []
    for m, txt in MESH_TXT.items():
        d = data[m]
        if not d:
            continue
        di = 100 * (d[1.0]["Di_N"] - d[0.38]["Di_N"]) / d[1.0]["Di_N"]
        dD = 100 * (d[1.0]["D_N"] - d[0.38]["D_N"]) / d[1.0]["D_N"]
        dd.append((m, di, dD))
        L.append(f"| {txt} | {it(d[1.0]['Di_N'], 5)} | {it(d[0.38]['Di_N'], 5)} | {it(di, 3)} | {it(dD, 3)} |")
    span = max(x[1] for x in dd) - min(x[1] for x in dd)
    spanD = max(x[2] for x in dd) - min(x[2] for x in dd)
    L.append(f"\nEscursione di ΔDi fra le mesh: **{it(span, 3)} punti percentuali** "
             f"({it(100 * span / abs(dd[0][1]), 1)} % del valore); ΔD: {it(spanD, 3)} punti percentuali.")
    # proposta
    L += ["", "## Errore stimato di D_N per mesh (max sulle due geometrie)", "", "| mesh | E(D_N) [%] | serie |", "|---|---|---|"]
    for (s, tp, m, k), e in sorted(err.items()):
        pass
    best = {}
    for (s, tp, m, k), e in err.items():
        if k == "D_N" and e is not None:
            best[(m, s)] = max(best.get((m, s), 0.0), e)
    for (m, s), e in sorted(best.items(), key=lambda x: x[1]):
        L.append(f"| {MESH_TXT[m]} | {it(e, 3)} | {s} |")
    with open(os.path.join(HERE, "gci_7e.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("scritto gci_7e.md")


if __name__ == "__main__":
    main()
