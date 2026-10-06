#!/usr/bin/env python3
"""
benchmark_taper.py - Parte 7C: benchmark sulla rastremazione (solo heeds_mock, NON per HEEDS).

DOE: configs/esplorativi/case_planform_taper_S.json (size_by S_half, S_half 0,911041 m², b_half 2,64 m, twist 0,
trim su W = 147,15 N), taper 0,25-1,00 passo 0,05, in runs/taper. Scrive in questa cartella:
    benchmark_taper.md     tabella, minimo di Di_N, rumore
    taper_e_Di.png         e_span(taper) e Di_N(taper), minimo di Di_N evidenziato
    taper_carico.png       L'(y)/L'(0) per taper 1,0, ottimo e 0,25 contro l'ellittica sqrt(1 - eta^2)
    taper_eta_stall.png    eta_stall(taper) (clmax SEGNAPOSTO)
Rumore: differenze seconde di Di_N lungo il taper (contengono anche la curvatura vera, f'' h^2) e residui da un
polinomio di 4° grado in taper (stima del rumore vero). Soglia: 0,5 % di Di_N.
Interprete: Python di HEEDS (numpy, matplotlib).
"""
import csv
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs", "taper")
NOISE_LIM = 0.5          # % di Di_N


def kv(path):
    with open(path, encoding="utf-8") as f:
        return dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)


def load():
    rows = []
    with open(os.path.join(RUNS, "summary.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = os.path.join(RUNS, r["design"])
            res = {k: float(v) for k, v in kv(os.path.join(d, "results.txt")).items()}
            with open(os.path.join(d, "spanload.csv"), encoding="utf-8") as fs:
                sl = [{k: float(v) for k, v in s.items()} for s in csv.DictReader(fs)]
            res["_sl"], res["_t"], res["_design"] = sl, float(r["wall_s"]), r["design"]
            rows.append(res)
    rows.sort(key=lambda r: r["taper"])
    return rows


def it(v, nd):
    return "–" if v == -999 else f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = load()
    t = np.array([r["taper"] for r in rows])
    di = np.array([r["Di_N"] for r in rows])
    e = np.array([r["e_span"] for r in rows])
    k = int(np.argmin(di))
    # minimo "liscio": parabola sui 5 punti attorno al minimo discreto
    lo, hi = max(0, k - 2), min(len(t), k + 3)
    pa = np.polyfit(t[lo:hi], di[lo:hi], 2)
    t_min_fit = -pa[1] / (2 * pa[0]) if pa[0] > 0 else float("nan")
    # rumore
    d2 = di[:-2] - 2 * di[1:-1] + di[2:]
    d2_pct = 100 * np.abs(d2) / di[1:-1]
    p4 = np.polyfit(t, di, 4)
    resid = di - np.polyval(p4, t)
    resid_pct = 100 * np.abs(resid) / di
    curv = np.polyval(np.polyder(p4, 2), t[1:-1]) * 0.05 ** 2          # parte liscia delle differenze seconde
    d2_noise_pct = 100 * np.abs(d2 - curv) / di[1:-1]

    L = ["# Benchmark 7C – rastremazione ad area e apertura fisse (generato da benchmark_taper.py)", "",
         "`configs/esplorativi/case_planform_taper_S.json`: ccs_planform, `size_by: \"S_half\"`, S_half = 0,911041 m², "
         "b_half = 2,64 m (AR 15,30), twist 0, trim su W = 147,15 N a 20 m/s (α1 = 0°, α2 = 2°), configurazione D. "
         "Tutte le grandezze dal run ad α*. \\* = **clmax segnaposto 1,2 costante** (non è una stima fisica).", "",
         "| taper | c_root [m] | c_tip [m] | α* [°] | Di_N [N] | e_span | D_N [N] | D0_N [N] | CLmax_wing\\* | η_stall\\* | "
         "Re_tip | M_root [N m] | status | tempo [s] |", "|" + "---|" * 14]
    for i, r in enumerate(rows):
        mark = " **(min)**" if i == k else ""
        L.append(f"| {it(r['taper'], 2)}{mark} | {it(r['c_root'], 4)} | {it(r['c_root'] * r['taper'], 4)} | "
                 f"{it(r['alpha_trim'], 3)} | {it(r['Di_N'], 4)} | {it(r['e_span'], 4)} | {it(r['D_N'], 3)} | "
                 f"{it(r['D0_N'], 3)} | {it(r['CLmax_wing'], 3)} | {it(r['eta_stall'], 3)} | {it(r['Re_tip'], 0)} | "
                 f"{it(r['M_root_Nm'], 1)} | {int(r['status'])} | {it(r['_t'], 1)} |")
    L += ["", f"**Minimo di Di_N:** taper = {it(t[k], 2)} (Di_N {it(di[k], 4)} N, e_span {it(e[k], 4)}); parabola sui "
              f"5 punti attorno: taper ≈ {it(t_min_fit, 3)}. e_span da {it(e[-1], 3)} (taper 1) a {it(e.max(), 3)} "
              f"(massimo a taper {it(t[int(np.argmax(e))], 2)}); Di_N rettangolare/ottimo = {it(di[-1] / di[k], 4)}.", "",
          "## Rumore di Di_N lungo il taper", "",
          f"- Differenze seconde |Di(i−1) − 2 Di(i) + Di(i+1)| / Di: massimo **{it(d2_pct.max(), 3)} %**, mediana "
          f"{it(float(np.median(d2_pct)), 3)} % (includono la curvatura vera: f″h² dal polinomio, massimo "
          f"{it(float((100 * np.abs(curv) / di[1:-1]).max()), 3)} %).",
          f"- Differenze seconde meno la curvatura del polinomio di 4° grado: massimo **{it(d2_noise_pct.max(), 3)} %**.",
          f"- Residui dal polinomio di 4° grado: massimo **{it(resid_pct.max(), 3)} %**, RMS "
          f"{it(float(np.sqrt(np.mean(resid_pct ** 2))), 3)} %.",
          f"- Soglia 0,5 % di Di_N: **{'SUPERATA' if max(d2_noise_pct.max(), resid_pct.max()) > NOISE_LIM else 'non superata'}**"
          f" dal rumore stimato; differenze seconde grezze {'oltre' if d2_pct.max() > NOISE_LIM else 'entro'} lo 0,5 %.",
          "", "| taper | Di_N [N] | diff. seconda [% Di] | residuo polinomio [% Di] |", "|---|---|---|---|"]
    for i in range(len(t)):
        dd = it(d2_pct[i - 1], 3) if 0 < i < len(t) - 1 else "–"
        L.append(f"| {it(t[i], 2)} | {it(di[i], 4)} | {dd} | {it(resid_pct[i], 3)} |")
    with open(os.path.join(HERE, "benchmark_taper.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # grafico 1: e_span e Di_N
    f, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(t, di, "o-", color="#1f4e9c", lw=1.6, ms=4, label="Di_N [N]")
    ax.plot(t[k], di[k], "o", ms=11, mfc="none", mec="#b8322a", mew=2, label=f"minimo Di_N (taper {t[k]:.2f})")
    ax.set_xlabel("taper = c_tip / c_root"); ax.set_ylabel("Di_N [N]", color="#1f4e9c"); ax.grid(alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(t, e, "s--", color="#d9822b", lw=1.3, ms=3.5, label="e_span")
    ax2.set_ylabel("e_span", color="#d9822b")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", fontsize=8)
    ax.set_title("Benchmark 7C: S e b fissi, twist 0, trim W = 147,15 N")
    f.tight_layout(); f.savefig(os.path.join(HERE, "taper_e_Di.png"), dpi=150); plt.close(f)

    # grafico 2: carico normalizzato
    f, ax = plt.subplots(figsize=(7.2, 4.6))
    eta_e = np.linspace(0, 1, 300)
    ax.plot(eta_e, np.sqrt(1 - eta_e ** 2), color="k", lw=1.0, ls="--", label="ellittica √(1 − η²)")
    for idx, col in ((len(t) - 1, "#1f4e9c"), (k, "#b8322a"), (0, "#3a8d4f")):
        sl = rows[idx]["_sl"]
        lp = np.array([s["Lp_N_m"] for s in sl])
        ax.plot([s["eta"] for s in sl], lp / lp[0], color=col, lw=1.6, label=f"taper {t[idx]:.2f}")
    ax.set_xlabel("η = y / (b/2)"); ax.set_ylabel("L′(y) / L′(0)"); ax.set_xlim(0, 1); ax.set_ylim(0, 1.15)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title("Carico in apertura ad α* (L′(0) = sezione più vicina alla radice, η ≈ 0,02)")
    f.tight_layout(); f.savefig(os.path.join(HERE, "taper_carico.png"), dpi=150); plt.close(f)

    # grafico 3: eta_stall
    f, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(t, [r["eta_stall"] for r in rows], "o-", color="#7a4fa0", lw=1.5, ms=4)
    ax.set_xlabel("taper"); ax.set_ylabel("η_stall"); ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    ax.set_title("Sezione critica η_stall (clmax SEGNAPOSTO 1,2 costante)")
    f.tight_layout(); f.savefig(os.path.join(HERE, "taper_eta_stall.png"), dpi=150); plt.close(f)
    print(f"minimo Di_N a taper {t[k]:.2f}; rumore d2 max {d2_pct.max():.3f} %, residui max {resid_pct.max():.3f} %")


if __name__ == "__main__":
    main()
