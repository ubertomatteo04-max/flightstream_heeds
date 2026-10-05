#!/usr/bin/env python3
"""
plot_spanload.py - Grafico di cl(eta) dai spanload.csv di un DOE di heeds_mock.py (v2.6.0).

Uso (Python di HEEDS, con matplotlib), dopo
    python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,4,8,12 --out mock_runs_spanload
    "C:\\Program Files\\Siemens\\SimcenterHEEDS-2604.0\\MDO\\Python3\\python.exe" diagnostica\\apertura\\plot_spanload.py
Scrive cl_eta.png e spanload_riepilogo.md in questa cartella. Linea tratteggiata: distribuzione ellittica con lo
stesso CL (ala rettangolare: cl = 4/pi CL sqrt(1 - eta^2)).
"""
import argparse
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def read_kv(path):
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            if "=" in ln:
                k, v = (s.strip() for s in ln.split("=", 1))
                out[k] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doe", default=os.path.join(REPO, "mock_runs_spanload"))
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    runs = []
    for d in sorted(os.listdir(a.doe)):
        p = os.path.join(a.doe, d)
        if d.startswith("Design_") and os.path.isfile(os.path.join(p, "spanload.csv")):
            res = read_kv(os.path.join(p, "results.txt"))
            with open(os.path.join(p, "spanload.csv"), encoding="utf-8") as f:
                rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
            note = [ln.strip() for ln in open(os.path.join(p, "run_info.txt"), encoding="utf-8") if "carico in apertura" in ln]
            runs.append((float(res["aoa"]), float(res["CL"]), rows, res, note[0] if note else ""))
    runs.sort()
    cols = ["#1f4e9c", "#3a8d4f", "#d9822b", "#b8322a", "#7a4fa0", "#555555"]
    f, ax = plt.subplots(figsize=(7.2, 4.8))
    for (aoa, CL, rows, _, _), c in zip(runs, cols):
        eta = [r["eta"] for r in rows]
        ax.plot(eta, [r["cl"] for r in rows], color=c, lw=1.6, marker="o", ms=2.5, label=f"α = {aoa:g}° (CL {CL:.3f})")
        e = [i / 200 for i in range(201)]
        ax.plot(e, [4 / math.pi * CL * math.sqrt(max(0.0, 1 - x * x)) for x in e], color=c, lw=0.8, ls="--")
    ax.plot([], [], color="k", lw=0.8, ls="--", label="ellittica a pari CL")
    ax.set_xlabel("η = y / (b/2)"); ax.set_ylabel("cl di sezione"); ax.set_xlim(0, 1); ax.set_ylim(bottom=0)
    ax.set_title("Semiala, configurazione D: carico lungo l'apertura (FlightStream)")
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower left")
    f.tight_layout(); f.savefig(os.path.join(HERE, "cl_eta.png"), dpi=150); plt.close(f)

    L = ["# Carico lungo l'apertura – configurazione D (fixed), generato da plot_spanload.py", "",
         "| α [°] | CL carichi | cl_sec_max | η del massimo | cl_sec_root | cl_sec_eta05 | controllo ∫cl·c |",
         "|---|---|---|---|---|---|---|"]
    for aoa, CL, rows, res, note in runs:
        chk = note.split("scarto ")[-1].rstrip(")") if "scarto" in note else "–"
        L.append(f"| {aoa:g} | {CL:.4f} | {float(res['cl_sec_max']):.4f} | {float(res['eta_cl_sec_max']):.3f} | "
                 f"{float(res['cl_sec_root']):.4f} | {float(res['cl_sec_eta05']):.4f} | {chk} |")
    with open(os.path.join(HERE, "spanload_riepilogo.md"), "w", encoding="utf-8") as fo:
        fo.write("\n".join(L).replace(".", ",").replace("plot_spanload,py", "plot_spanload.py") + "\n")
    print(f"scritti cl_eta.png e spanload_riepilogo.md in {HERE}")


if __name__ == "__main__":
    main()
