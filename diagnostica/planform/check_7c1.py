#!/usr/bin/env python3
"""
check_7c1.py - 7C.1: D_N non quantizzato. Legge runs/taper_7c1 (taper 0,30-0,50, S_half fisso, trim) e il DOE della 7C
(runs/taper, D_N vecchio = CD q Sref) e verifica che D_N = Di_N + D0_N (foglio in newton) sia liscio: residuo di un fit
quadratico in taper < 0,1 %. Scrive check_7c1.md. Solo libreria standard.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIM = 0.1   # %


def kv(path):
    with open(path, encoding="utf-8") as f:
        return dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)


def load(sub):
    rows = []
    folder = os.path.join(HERE, "runs", sub)
    with open(os.path.join(folder, "summary.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            res = kv(os.path.join(folder, r["design"], "results.txt"))
            with open(os.path.join(folder, r["design"], "run_info.txt"), encoding="utf-8") as fi:
                d0 = next((ln.strip()[2:] for ln in fi if "D0_N dal foglio" in ln), "")
            rows.append({"taper": float(res["taper"]), "status": res["status"], "t": float(r["wall_s"]),
                         **{k: float(res[k]) for k in ("D_N", "Di_N", "D0_N", "alpha_trim", "CDo", "q_Pa", "Sref_m2")},
                         "_d0": d0})
    return sorted(rows, key=lambda x: x["taper"])


def quad_fit(x, y):
    """Minimi quadrati y = a + b x + c x^2 (equazioni normali 3x3, Cramer)."""
    s = [sum(xi ** k for xi in x) for k in range(5)]
    t = [sum(yi * xi ** k for xi, yi in zip(x, y)) for k in range(3)]
    m = [[s[0], s[1], s[2]], [s[1], s[2], s[3]], [s[2], s[3], s[4]]]

    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    coef = []
    for j in range(3):
        mj = [row[:] for row in m]
        for i in range(3):
            mj[i][j] = t[i]
        coef.append(det(mj) / d)
    return coef


def it(v, nd):
    return f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def main():
    new = load("taper_7c1")
    old = {round(r["taper"], 2): r for r in load("taper")}
    x = [r["taper"] for r in new]
    L = ["# 7C.1 – D_N non quantizzato (generato da check_7c1.py)", "",
         "`configs/esplorativi/case_planform_taper_S.json` (S_half fisso, trim W = 147,15 N), driver v2.8.1 (schema 7): "
         "D0_N dal foglio dei carichi in NEWTONS, Di_N dal log, **D_N = Di_N + D0_N**. Colonne \"7C\": DOE della 7C (driver "
         "v2.7.0: D_N = CD·q·Sref, D0_N = CDo·q·Sref, 4 decimali).", "",
         "| taper | status | α* [°] | Di_N [N] | D0_N [N] | D_N [N] | Di_N + D0_N − D_N | D0_N 7C | D_N 7C | D0 (N) − CDo·q·S [N] | tempo [s] |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in new:
        o = old.get(round(r["taper"], 2))
        d0c = r["CDo"] * r["q_Pa"] * r["Sref_m2"]
        L.append(f"| {it(r['taper'], 2)} | {r['status']} | {it(r['alpha_trim'], 3)} | {it(r['Di_N'], 5)} | {it(r['D0_N'], 4)} | "
                 f"{it(r['D_N'], 5)} | {r['Di_N'] + r['D0_N'] - r['D_N']:.1e} | {it(o['D0_N'], 4) if o else '–'} | "
                 f"{it(o['D_N'], 4) if o else '–'} | {it(r['D0_N'] - d0c, 4)} (±{it(0.5e-4 * r['q_Pa'] * r['Sref_m2'], 4)}) | "
                 f"{it(r['t'], 1)} |")
    L += ["", "## Fit quadratico in taper (5 punti)", "", "| grandezza | residuo massimo [%] | residuo RMS [%] | esito (< 0,1 %) |",
          "|---|---|---|---|"]
    ok_all = True
    for k in ("D_N", "Di_N", "D0_N"):
        y = [r[k] for r in new]
        a, b, c = quad_fit(x, y)
        res = [100 * (yi - (a + b * xi + c * xi * xi)) / yi for xi, yi in zip(x, y)]
        mx = max(abs(v) for v in res)
        rms = (sum(v * v for v in res) / len(res)) ** 0.5
        ok = mx < LIM
        ok_all &= ok if k == "D_N" else True
        L.append(f"| {k} | {it(mx, 4)} | {it(rms, 4)} | {'OK' if ok else 'NO'} |")
    yo = [old[round(t, 2)]["D_N"] for t in x if round(t, 2) in old]
    if len(yo) == len(x):
        a, b, c = quad_fit(x, yo)
        mxo = max(abs(100 * (yi - (a + b * xi + c * xi * xi)) / yi) for xi, yi in zip(x, yo))
        L.append(f"| D_N 7C (vecchio, CD·q·S) | {it(mxo, 4)} | – | {'OK' if mxo < LIM else 'NO'} (confronto) |")
    t = [r["t"] for r in new]
    L += ["", f"Tempo per design (3 run di FlightStream con trim): {it(min(t), 1)}–{it(max(t), 1)} s, media {it(sum(t) / len(t), 1)} s.",
          f"**Esito: D_N {'liscio' if ok_all else 'NON liscio'}** (residuo del fit quadratico {'<' if ok_all else '≥'} 0,1 %)."]
    with open(os.path.join(HERE, "check_7c1.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("OK" if ok_all else "NON liscio")


if __name__ == "__main__":
    main()
