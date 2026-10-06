#!/usr/bin/env python3
"""
analisi_7h.py - 7H: verifica del design migliore SHERPA (runs/verifica_7h, da run_verifica_7h.py).

1. Tabella di baseline e migliore su U120 x V64 e U180 x V64; Delta (migliore - baseline) e criterio: stesso segno su
   entrambe le mesh e |Delta D_N| > 3 % sulla mesh fine.
2. Sensibilita' allo stallo: stall_margin del migliore (U120 x V64) ricalcolato con clmax(Re) di XFOIL Ncrit 5 (polari in
   xfoil/polars, stesso criterio di xfoil_polars.py; scrive xfoil/clmax_vs_Re_N5.csv) dalle sezioni dei run ad alfa1 e
   alfa2 (trim_1, trim_2): solo post-processing dei dati di FlightStream, nessun run nuovo.
3. Grafico verifica_7h.png: L'(y)/L'(0) ad alfa* contro l'ellittica, e cl(eta)/clmax(eta) alla condizione di stallo
   (CL dell'ala = CLmax_wing, cl lineare fra alfa1 e alfa2) e in crociera.
Scrive verifica_7h.md. Interprete: Python di HEEDS (matplotlib).
"""
import csv
import glob
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
import postprocess as pp  # noqa: E402

RUNS = os.path.join(HERE, "runs", "verifica_7h")
KEYS = ["D_N", "Di_N", "D0_N", "e_span", "alpha_trim", "CLmax_wing", "CL_req", "stall_margin", "eta_stall", "Re_tip",
        "M_root_Nm"]
NU = 1.78e-5 / 1.225
V_MIN = 12.0
HEEDS_BEST = {"D_N": 4.90745, "stall_margin": 0.0118607}     # valori dello studio (Design129)


def kv(path):
    with open(path, encoding="utf-8") as f:
        return {k: (float(v) if re.fullmatch(r"[-+0-9.eE]+", v) else v)
                for k, v in (ln.strip().split(" = ", 1) for ln in f if " = " in ln)}


def tab(path):
    with open(path, encoding="utf-8") as f:
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]


def clmax_n5_table():
    """clmax(Re) Ncrit 5 dalle polari di XFOIL (massimo cl fra i punti convergenti; valido se >= 2 punti oltre)."""
    rows = []
    for p in sorted(glob.glob(os.path.join(REPO, "xfoil", "polars", "polar_Re*_N5.csv"))):
        re_ = float(re.search(r"Re(\d+)_N5", p).group(1))
        if abs(re_ - 475000) < 1:
            continue                                          # punto aggiuntivo di confronto, non nella griglia
        pol = tab(p)
        k = max(range(len(pol)), key=lambda i: pol[i]["CL"])
        beyond = sum(1 for r in pol if r["alpha"] > pol[k]["alpha"])
        rows.append((re_, pol[k]["CL"], pol[k]["alpha"], beyond >= 2))
    out = os.path.join(REPO, "xfoil", "clmax_vs_Re_N5.csv")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# clmax(Re) di vespa_root.dat, XFOIL 6.99 Ncrit 5 (sensibilita', 7H), dalle polari in xfoil/polars.\n"
                "# NON attivo in nessun JSON.\nRe,clmax,alpha_stall_deg,source\n")
        for re_, cl, al, ok in rows:
            f.write(f"{re_:.0f},{cl:.4f},{al:.2f},XFOIL Ncrit 5{'' if ok else ' (incerto)'}\n")
    return out, rows


def it(v, nd):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    R = {}
    for mesh in ("U120V64", "U180V64"):
        for name in ("baseline", "migliore"):
            d = os.path.join(RUNS, f"{mesh}_{name}")
            R[(mesh, name)] = {"res": kv(os.path.join(d, "results.txt")), "dir": d}
    L = ["# 7H – verifica del design migliore SHERPA (generato da analisi_7h.py)", "",
         "Studio HEEDS `semiala_planform_full` (150 valutazioni), design migliore = **Design129** (\"LatestBest\"): params.txt "
         "esatto c_root 0,287040, taper 0,508000, twist_tip_deg −0,440000, b_half 3,03072. Baseline: c_root 0,345091293, "
         "taper 1, twist 0, b_half 2,64. Run con `run_fs.bat` come HEEDS, trim W = 147,15 N, clmax XFOIL Ncrit 9. "
         "Mesh U120 × V64 (studio) e U180 × V64 (growth in corda 1,0656).", "",
         "## 1. Risultati", "",
         "| mesh | design | status | " + " | ".join(KEYS) + " |", "|---|---|---|" + "---|" * len(KEYS)]
    nd = {"D_N": 4, "Di_N": 4, "D0_N": 4, "e_span": 4, "alpha_trim": 3, "CLmax_wing": 4, "CL_req": 4, "stall_margin": 4,
          "eta_stall": 3, "Re_tip": 0, "M_root_Nm": 2}
    for (mesh, name), v in R.items():
        r = v["res"]
        L.append(f"| {mesh} | {name} | {int(r['status'])} | " + " | ".join(it(r[k], nd[k]) for k in KEYS) + " |")
    b = R[("U120V64", "migliore")]["res"]
    L.append(f"\nControllo con lo studio HEEDS (stesso design, stessa mesh): D_N {it(b['D_N'], 5)} contro "
             f"{it(HEEDS_BEST['D_N'], 5)}, stall_margin {it(b['stall_margin'], 5)} contro {it(HEEDS_BEST['stall_margin'], 5)}.")
    L += ["", "## 2. Δ = migliore − baseline", "", "| mesh | ΔD_N [N] | ΔD_N [%] | ΔDi_N [N] (%) | ΔD0_N [N] (%) | "
          "stall_margin baseline / migliore |", "|---|---|---|---|---|---|"]
    dD = {}
    for mesh in ("U120V64", "U180V64"):
        a, m = R[(mesh, "baseline")]["res"], R[(mesh, "migliore")]["res"]
        dD[mesh] = 100 * (m["D_N"] - a["D_N"]) / a["D_N"]
        L.append(f"| {mesh} | {it(m['D_N'] - a['D_N'], 4)} | {it(dD[mesh], 2)} % | {it(m['Di_N'] - a['Di_N'], 4)} "
                 f"({it(100 * (m['Di_N'] - a['Di_N']) / a['Di_N'], 1)} %) | {it(m['D0_N'] - a['D0_N'], 4)} "
                 f"({it(100 * (m['D0_N'] - a['D0_N']) / a['D0_N'], 1)} %) | {it(a['stall_margin'], 4)} / "
                 f"{it(m['stall_margin'], 4)} |")
    same = (dD["U120V64"] > 0) == (dD["U180V64"] > 0)
    ok = same and abs(dD["U180V64"]) > 3.0
    L.append(f"\n**Criterio (stesso segno su entrambe le mesh e |ΔD_N| > 3 % sulla mesh fine): "
             f"{'SUPERATO' if ok else 'NON SUPERATO'}** (segno {'uguale' if same else 'diverso'}; ΔD_N fine "
             f"{it(dD['U180V64'], 2)} %).")

    # 3. sensibilita' Ncrit 5
    fn5_path, n5 = clmax_n5_table()
    f9 = pp.read_clmax_table(os.path.join(REPO, "xfoil", "clmax_vs_Re.csv"))
    f5 = pp.read_clmax_table(fn5_path)
    out = {}
    for name in ("baseline", "migliore"):
        d = R[("U120V64", name)]["dir"]
        t1, t2 = tab(os.path.join(d, "trim_1", "spanload.csv")), tab(os.path.join(d, "trim_2", "spanload.csv"))
        cl1 = pp.parse_log(os.path.join(d, "trim_1", "fs_log.txt"))["CL"]
        cl2 = pp.parse_log(os.path.join(d, "trim_2", "fs_log.txt"))["CL"]
        req = R[("U120V64", name)]["res"]["CL_req"]
        c9, e9 = pp.critical_section(t1, t2, cl1, cl2, lambda c: f9(V_MIN * c / NU))
        c5, e5 = pp.critical_section(t1, t2, cl1, cl2, lambda c: f5(V_MIN * c / NU))
        out[name] = {"t1": t1, "t2": t2, "CL1": cl1, "CL2": cl2, "c9": c9, "e9": e9, "c5": c5, "e5": e5, "req": req}
    L += ["", "## 3. Sensibilità allo stallo: clmax XFOIL Ncrit 5 (mesh U120 × V64, solo post-processing)", "",
          f"clmax(Re) Ncrit 5 da `xfoil/polars` → `xfoil/clmax_vs_Re_N5.csv` (non attivo): "
          + ", ".join(f"{re_ / 1e5:.1f}e5: {it(cl, 3)}" for re_, cl, _, _ in n5) + ".", "",
          "| design | CL_req | CLmax_wing Ncrit 9 (ricalcolo) | stall_margin Ncrit 9 | η_stall | CLmax_wing Ncrit 5 | "
          "stall_margin Ncrit 5 | η_stall |", "|---|---|---|---|---|---|---|---|"]
    for name, o in out.items():
        L.append(f"| {name} | {it(o['req'], 4)} | {it(o['c9'], 4)} | {it(o['c9'] / o['req'] - 1, 4)} | {it(o['e9'], 3)} | "
                 f"{it(o['c5'], 4)} | {it(o['c5'] / o['req'] - 1, 4)} | {it(o['e5'], 3)} |")
    sm5 = out["migliore"]["c5"] / out["migliore"]["req"] - 1
    L.append(f"\n**stall_margin del migliore con Ncrit 5 = {it(sm5, 4)}: "
             f"{'resta ≥ 0,01' if sm5 >= 0.01 else ('< 0,01 ma ≥ 0' if sm5 >= 0 else 'NEGATIVO: il design non è ammissibile con Ncrit 5')}**.")

    # 4. grafico
    f, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    eta_e = [i / 300 for i in range(301)]
    axs[0].plot(eta_e, [math.sqrt(1 - x * x) for x in eta_e], "k--", lw=1, label="ellittica √(1 − η²)")
    cols = {"baseline": "#1f4e9c", "migliore": "#b8322a"}
    for name, c in cols.items():
        sl = tab(os.path.join(R[("U120V64", name)]["dir"], "spanload.csv"))
        lp0 = sl[0]["Lp_N_m"]
        axs[0].plot([s["eta"] for s in sl], [s["Lp_N_m"] / lp0 for s in sl], color=c, lw=1.7, label=f"{name} (α*)")
        o = out[name]
        eta = [s["eta"] for s in o["t1"]]
        cl_st = [s1["cl"] + (o["c9"] - o["CL1"]) * (s2["cl"] - s1["cl"]) / (o["CL2"] - o["CL1"]) for s1, s2 in zip(o["t1"], o["t2"])]
        ratio_st = [cl / f9(V_MIN * s["chord_m"] / NU) for cl, s in zip(cl_st, o["t1"])]
        ratio_cr = [s["cl"] / f9(V_MIN * s["chord_m"] / NU) for s in sl]
        axs[1].plot(eta, ratio_st, color=c, lw=1.7, label=f"{name}: allo stallo (CL = {o['c9']:.3f})")
        axs[1].plot([s["eta"] for s in sl], ratio_cr, color=c, lw=1.0, ls=":", label=f"{name}: in crociera (α*)")
        axs[1].axvline(o["e9"], color=c, lw=0.6, ls="--")
    axs[1].plot(eta_e, [math.sqrt(1 - x * x) for x in eta_e], "k--", lw=1, label="ellittica √(1 − η²)")
    axs[0].set_title("L′(y) / L′(0) ad α* (mesh U120 × V64)")
    axs[1].set_title("cl(η) / clmax(η), clmax XFOIL Ncrit 9 a V_min")
    for ax in axs:
        ax.set_xlabel("η = y / (b/2)"); ax.set_xlim(0, 1); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    axs[0].set_ylim(0, 1.15); axs[1].set_ylim(0, 1.1)
    f.tight_layout(); f.savefig(os.path.join(HERE, "verifica_7h.png"), dpi=150); plt.close(f)
    L += ["", "## 4. Carico in apertura", "", "![verifica 7H](verifica_7h.png)", "",
          "Sinistra: L′(y)/L′(0) ad α* (L′(0) = sezione a η ≈ 0,02) contro l'ellittica. Destra: cl/clmax lungo l'apertura "
          "alla condizione di stallo (CL dell'ala = CLmax_wing; il massimo vale 1 a η_stall, linea tratteggiata verticale) "
          "e in crociera (punteggiato)."]
    with open(os.path.join(HERE, "verifica_7h.md"), "w", encoding="utf-8") as fo:
        fo.write("\n".join(L) + "\n")
    print("criterio", "SUPERATO" if ok else "NON SUPERATO", "| dD", dD, "| sm5", round(sm5, 4))


if __name__ == "__main__":
    main()
