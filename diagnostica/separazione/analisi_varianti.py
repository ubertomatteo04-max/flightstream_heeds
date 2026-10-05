#!/usr/bin/env python3
"""
analisi_varianti.py - Punto 4 bis: analisi dei run diagnostici del modello di separazione (SOLO DIAGNOSTICA).

Per ogni configurazione (CS, C, D dai DOE di v2.5.0; varianti in runs\\) e alfa = 0, 4, 12, 16:
  - CL dal log (ultima riga dell'ultima tabella) e CL, CD, CDi, CMy dai carichi (results.txt);
  - striscia di celle a eta ~ 0,5 (riga della mesh piu' vicina): x/c di transizione sul dorso
    (primo Transition_marker >= 0,5), x/c del primo Separation_marker >= 0,5 sul dorso e inizio della zona
    separata contigua al TE; cl di sezione dall'integrale di Cp sulla striscia;
  - frazione d'area del dorso con Separation_marker >= 0,5 (sep_marker_frac_up, ricalcolata).
Controlli: Cp a eta ~ 0,5 di C contro CS a 4 e 12 deg (cp_eta05_C_vs_CS.png); differenza massima di Cp, cf, H
fra i VTK di D e di C a 4 e 12 deg; Separation_marker lungo la corda a 4 deg per tutte le varianti.
Confronto dell'innesco con XFOIL (..\\..\\reference\\xfoil\\riepilogo_N9.csv) a 0, 4, 12 deg.
Uscite in questa cartella: tabella_varianti.csv, analisi.md, *.png. Interprete: Python di HEEDS.
"""
import csv
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
import postprocess as pp  # noqa: E402

AOAS = [0.0, 4.0, 12.0, 16.0]
CONFIGS = [  # nome, cartella dei design, descrizione
    ("CS", os.path.join(REPO, "mock_runs_visc_CS"), "accoppiato + Airfoil, TRANSITIONAL, V 20 (partenza)"),
    ("CS_Re22", os.path.join(HERE, "runs", "CS_Re22"), "CS con V = 22 m/s (Re 522 484)"),
    ("CS_turb", os.path.join(HERE, "runs", "CS_turb"), "CS con bl_type TURBULENT"),
    ("CS_lam", os.path.join(HERE, "runs", "CS_lam"), "CS con LAMINAR_SEPARATION ENABLE"),
    ("DS", os.path.join(HERE, "runs", "DS"), "disaccoppiato + Airfoil"),
    ("CS_pdrag", os.path.join(HERE, "runs", "CS_pdrag"), "CS con CDi da pressione (DELETE_VORTICITY_DRAG_BOUNDARIES)"),
    ("C", os.path.join(REPO, "mock_runs_visc_C"), "accoppiato senza separazione (riferimento)"),
    ("D", os.path.join(REPO, "mock_runs_visc_D"), "disaccoppiato senza separazione (default validato)"),
]
FRAME = pp.parse_wing_frame({"chord_axis": "+x", "span_axis": "+y", "up_axis": "+z", "span_root_m": 0.0})
ON = 0.5                 # soglia richiesta per il Separation_marker
FULL = 0.999             # Separation_marker = 1: "fully separated" (manuale p. 245)
TR_ON = 0.99             # Transition_marker cresce da 0 a 1; = 1 a valle della transizione
XFOIL = os.path.join(REPO, "reference", "xfoil", "riepilogo_N9.csv")


def read_kv(path):
    out = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                if "=" in ln:
                    k, v = (s.strip() for s in ln.split("=", 1))
                    out[k] = v
    return out


def designs_by_aoa(folder):
    out = {}
    if not os.path.isdir(folder):
        return out
    for d in sorted(os.listdir(folder)):
        p = os.path.join(folder, d, "params.txt")
        if d.startswith("Design_") and os.path.isfile(p):
            kv = read_kv(p)
            if "aoa" in kv:
                out[float(kv["aoa"])] = os.path.join(folder, d)
    return out


def strip_profile(vtk, cells, aoa, eta_target=0.5):
    """Riga di celle della mesh piu' vicina a eta_target: profili lungo la corda e cl di sezione."""
    pts, polys, f = vtk["pts"], vtk["polys"], vtk["cell"]
    wing = [c for c in cells if c["side"] in ("up", "lo")]
    etas = np.array([round(c["eta"], 4) for c in wing])
    rows = np.unique(etas)
    eta_row = rows[np.argmin(np.abs(rows - eta_target))]
    sel = [c for c, e in zip(wing, etas) if e == eta_row]
    # Cp_reference contiene la correzione di pressione del modello di separazione (in CS differisce da
    # Cp_freestream fino a 0,12 a 4 deg e 0,97 a 12 deg; in C e D le due variabili coincidono)
    cp = f["Cp_reference"]
    cp0 = f["Cp_freestream"]
    out = {"eta": float(eta_row)}
    for side in ("up", "lo"):
        cs = sorted([c for c in sel if c["side"] == side], key=lambda c: c["xc"])
        idx = [c["i"] for c in cs]
        out[side] = {"xc": np.array([c["xc"] for c in cs]), "Cp": np.array([cp[i] for i in idx]),
                     "Cp0": np.array([cp0[i] for i in idx]),
                     "sep": np.array([f["Separation_marker"][i] for i in idx]),
                     "tr": np.array([f["Transition_marker"][i] for i in idx]),
                     "cf": np.array([f["skin_friction_coeff."][i] for i in idx]),
                     "H": np.array([f["BL_shape_factor"][i] for i in idx])}
    # cl di sezione: forza di pressione sulla striscia / (q c w)
    F = np.zeros(3)
    ys, xs = [], []
    for c in sel:
        q = [pts[k] for k in polys[c["i"]]]
        n = np.array(pp._newell(q))
        F += -cp[c["i"]] * n * f["Area"][c["i"]]
        ys += [p[1] for p in q]; xs += [p[0] for p in q]
    # verso delle normali: sul dorso la normale esterna ha z > 0
    up_c = [c for c in sel if c["side"] == "up"][0]
    nz = pp._newell([pts[k] for k in polys[up_c["i"]]])[2]
    F *= 1.0 if nz > 0 else -1.0
    w, chord = max(ys) - min(ys), max(xs) - min(xs)
    a = math.radians(aoa)
    cz, cx = F[2] / (chord * w), F[0] / (chord * w)
    out["cl_sec"] = cz * math.cos(a) - cx * math.sin(a)
    return out


def onset(prof):
    up = prof["up"]
    x, sep, tr = up["xc"], up["sep"], up["tr"]
    on = sep >= ON
    x_first = float(x[on][0]) if on.any() else None
    if on.any() and on[-1]:
        k = len(on) - 1
        while k > 0 and on[k - 1]:
            k -= 1
        x_te = float(x[k])
    else:
        x_te = None
    trn = tr >= TR_ON
    x_tr = float(x[trn][0]) if trn.any() else None
    full = sep >= FULL
    x_full = float(x[full][0]) if full.any() else None
    return x_first, x_te, x_tr, x_full


def analyse():
    rows, profiles = [], {}
    for name, folder, _ in CONFIGS:
        des = designs_by_aoa(folder)
        for a in AOAS:
            d = des.get(a)
            if d is None:
                continue
            res = read_kv(os.path.join(d, "results.txt"))
            r = {"conf": name, "aoa": a, "status": res.get("status", "?")}
            try:
                lg = pp.parse_log(os.path.join(d, "fs_log.txt"))
                r["CL_log"] = lg["CL"]
                r["iter"] = "+".join(str(p["iterations"]) for p in lg["phases"])
            except Exception as e:  # noqa: BLE001
                r["CL_log"], r["iter"] = None, f"log: {e}"
            for k in ("CL", "CD", "CDi", "CDo", "CMy", "sep_marker_frac_up"):
                try:
                    r[k] = float(res[k])
                except (KeyError, ValueError):
                    r[k] = None
            vp = os.path.join(d, "surface.vtk")
            if os.path.isfile(vp):
                vtk = pp.read_vtk(vp)
                cells = pp.wing_cells(vtk, FRAME)
                prof = strip_profile(vtk, cells, a)
                profiles[(name, a)] = prof
                r["eta"] = prof["eta"]
                r["x_sep_first"], r["x_sep_te"], r["x_tr"], r["x_sep_full"] = onset(prof)
                r["cl_sec"] = prof["cl_sec"]
                f = vtk["cell"]
                up = [c for c in cells if c["side"] == "up"]
                A = sum(f["Area"][c["i"]] for c in up)
                r["frac_sep_up"] = sum(f["Area"][c["i"]] for c in up if f["Separation_marker"][c["i"]] >= ON) / A
                r["frac_sep_full_up"] = sum(f["Area"][c["i"]] for c in up if f["Separation_marker"][c["i"]] >= FULL) / A
                r["frac_cfneg_up"] = sum(f["Area"][c["i"]] for c in up if f["skin_friction_coeff."][c["i"]] < 0) / A
                if name in ("C", "D", "CS") and a in (4.0, 12.0):
                    profiles[("vtk", name, a)] = {k: np.array(f[k]) for k in
                                                  ("Cp_freestream", "Cp_reference", "skin_friction_coeff.",
                                                   "BL_shape_factor", "Transition_marker", "BL_Thickness", "Velocity",
                                                   "Separation_marker")}
            rows.append(r)
            print(f"{name:9s} {a:4g}: CL {r.get('CL')} log {r.get('CL_log')}  x_tr {r.get('x_tr')}  "
                  f"sep {r.get('x_sep_first')} / {r.get('x_sep_te')} / =1 {r.get('x_sep_full')}  frac {r.get('frac_sep_up')}", flush=True)
    return rows, profiles


def vtk_diff(profiles):
    """Differenza massima cella per cella: D contro C e C contro CS, a 4 e 12 deg."""
    out = []
    for p, q in (("D", "C"), ("C", "CS")):
        for a in (4.0, 12.0):
            c, d = profiles.get(("vtk", p, a)), profiles.get(("vtk", q, a))
            if c is None or d is None:
                continue
            out.append((f"{p} – {q}", a, {k: float(np.nanmax(np.abs(c[k] - d[k]))) for k in c}))
    return out


def read_xfoil():
    out = {}
    if os.path.isfile(XFOIL):
        with open(XFOIL, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[round(float(r["alpha"]), 3)] = r
    return out


def xfoil_at_cl(xf, cl):
    """Riga XFOIL (interpolazione al punto piu' vicino) con cl di sezione uguale."""
    best = min((r for r in xf.values()), key=lambda r: abs(float(r["CL"]) - cl) + (0 if float(r["alpha"]) <= 15.5 else 9))
    return best


def plots(profiles, xf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharey=False)
    for ax, a in zip(axs, (4.0, 12.0)):
        for name, col in (("C", "#1f4e9c"), ("CS", "#b8322a")):
            p = profiles.get((name, a))
            if p is None:
                continue
            ax.plot(p["up"]["xc"], p["up"]["Cp"], color=col, lw=1.5, label=f"{name} dorso")
            ax.plot(p["lo"]["xc"], p["lo"]["Cp"], color=col, lw=1.0, ls="--", label=f"{name} ventre")
            if name == "CS":
                ax.plot(p["up"]["xc"], p["up"]["Cp0"], color="#e8a09a", lw=0.8, ls="-.",
                        label="CS dorso, Cp_freestream (senza correzione)")
            if name == "CS":
                x1 = onset(p)[0]
                if x1 is not None:
                    ax.axvline(x1, color=col, lw=0.7, ls=":", label=f"CS Separation_marker ≥ 0,5 da x/c {x1:.2f}")
        ax.invert_yaxis(); ax.grid(alpha=0.3)
        eta = profiles.get(("CS", a), profiles.get(("C", a), {"eta": 0.5}))["eta"]
        ax.set_title(f"α = {a:g}°, striscia η = {eta:.3f}")
        ax.set_xlabel("x/c"); ax.set_ylabel("Cp"); ax.legend(fontsize=8)
    f.suptitle("Cp_reference a η ≈ 0,5: C (accoppiato) contro CS (accoppiato + Airfoil)")
    f.tight_layout(); f.savefig(os.path.join(HERE, "cp_eta05_C_vs_CS.png"), dpi=150); plt.close(f)

    f, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    cols = {"CS": "#b8322a", "CS_Re22": "#d9822b", "CS_turb": "#7a4fa0", "CS_lam": "#3a8d4f", "DS": "#1f4e9c",
            "CS_pdrag": "#888888"}
    for name, col in cols.items():
        p = profiles.get((name, 4.0))
        if p is None:
            continue
        axs[0].step(p["up"]["xc"], p["up"]["sep"], where="mid", color=col, lw=1.3, label=name)
        axs[1].step(p["up"]["xc"], p["up"]["tr"], where="mid", color=col, lw=1.3, label=name)
    r4 = xf.get(4.0)
    for ax, ttl in zip(axs, ("Separation_marker sul dorso", "Transition_marker sul dorso")):
        if r4:
            ax.axvline(float(r4["xtr_dorso"]), color="k", lw=0.8, ls="--", label="XFOIL x_tr (α 4°)")
            if r4["bolla_dorso_inizio"]:
                ax.axvspan(float(r4["bolla_dorso_inizio"]), float(r4["bolla_dorso_fine"]), color="k", alpha=0.12,
                           label="XFOIL bolla (α 4°)")
        ax.set_title(f"{ttl}, α = 4°, η ≈ 0,5"); ax.set_xlabel("x/c"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    f.tight_layout(); f.savefig(os.path.join(HERE, "marker_4deg_varianti.png"), dpi=150); plt.close(f)


def it(v, nd=4):
    if v is None or v == "":
        return "–"
    if isinstance(v, str):
        return v
    return f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


def write_outputs(rows, diffs, xf):
    keys = ["conf", "aoa", "status", "iter", "CL_log", "CL", "CD", "CDi", "CDo", "CMy", "eta", "x_tr", "x_sep_first",
            "x_sep_te", "x_sep_full", "frac_sep_up", "frac_sep_full_up", "frac_cfneg_up", "sep_marker_frac_up", "cl_sec"]
    with open(os.path.join(HERE, "tabella_varianti.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r in rows:
            w.writerow(["" if r.get(k) is None else (f"{r[k]:.6g}" if isinstance(r.get(k), float) else r.get(k))
                        for k in keys])
    desc = {n: d for n, _, d in CONFIGS}
    L = ["# Punto 4 bis – diagnosi del modello di separazione: run diagnostici FlightStream", "",
         "**SOLO DIAGNOSTICA, NON VALIDATO.** Generato da `analisi_varianti.py`. Semiala fixed, mesh del template.",
         "Striscia: riga di celle della mesh più vicina a η = 0,5 (dorso). x_tr = primo Transition_marker ≥ 0,99 "
         "(il marker cresce da 0 al LE fino a 1 alla transizione); "
         "sep. primo / sep. TE = primo Separation_marker ≥ 0,5 e inizio della zona ≥ 0,5 contigua al TE; "
         "sep. = 1: primo Separation_marker = 1 (\"fully separated\", manuale p. 245); "
         "frazione sep. = area del dorso (metà ala, senza estremità) con Separation_marker ≥ 0,5 (fra parentesi: = 1); "
         "cl sez. = integrale di Cp_reference sulla striscia (Cp_reference contiene la correzione di separazione; "
         "Cp_freestream no).", "",
         "Configurazioni: " + "; ".join(f"**{n}** = {desc[n]}" for n, _, _ in CONFIGS) + ".", "",
         "| conf | α | status | iter. | CL log | CL carichi | CD | CDi | CMy | x_tr | sep. ≥ 0,5 primo | sep. ≥ 0,5 TE | sep. = 1 | frazione sep. ≥ 0,5 (= 1) | cl sez. |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['conf']} | {r['aoa']:g} | {r['status']} | {r.get('iter', '–')} | {it(r.get('CL_log'))} | {it(r.get('CL'))} | "
                 f"{it(r.get('CD'))} | {it(r.get('CDi'))} | {it(r.get('CMy'))} | {it(r.get('x_tr'), 3)} | "
                 f"{it(r.get('x_sep_first'), 3)} | {it(r.get('x_sep_te'), 3)} | {it(r.get('x_sep_full'), 3)} | "
                 f"{it(r.get('frac_sep_up'), 3)} ({it(r.get('frac_sep_full_up'), 3)}) | "
                 f"{it(r.get('cl_sec'), 3)} |")
    L += ["", "## VTK: differenza massima cella per cella", "",
          "| confronto | α | ΔCp_freestream | ΔCp_reference | Δcf | ΔH | ΔTransition_marker | ΔBL_Thickness | ΔVelocity | ΔSeparation_marker |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for lab, a, d in diffs:
        L.append(f"| {lab} | {a:g} | {it(d['Cp_freestream'], 4)} | {it(d['Cp_reference'], 4)} | {it(d['skin_friction_coeff.'], 5)} | "
                 f"{it(d['BL_shape_factor'], 4)} | {it(d['Transition_marker'], 3)} | {it(d['BL_Thickness'], 6)} | "
                 f"{it(d['Velocity'], 3)} | {it(d['Separation_marker'], 3)} |")
    L += ["", "## Innesco: XFOIL (Ncrit 9) contro FlightStream a η ≈ 0,5", "",
          "XFOIL allo stesso α geometrico e allo stesso cl di sezione (cl sez. di CS). Sep. XFOIL = inizio bolla "
          "laminare (cf < 0 prima della transizione) / inizio separazione turbolenta al TE.", "",
          "| α | XFOIL x_tr | XFOIL bolla | XFOIL sep. TE | XFOIL a pari cl (α, x_tr, bolla, sep. TE) | "
          + " | ".join(f"{n} x_tr / sep. ≥ 0,5 / sep. = 1" for n in ("CS", "CS_Re22", "CS_turb", "CS_lam", "DS", "CS_pdrag")) + " |",
          "|---|---|---|---|---|" + "---|" * 6]
    byk = {(r["conf"], r["aoa"]): r for r in rows}
    for a in (0.0, 4.0, 12.0):
        x = xf.get(a)
        if not x:
            continue
        bub = f"{float(x['bolla_dorso_inizio']):.3f}–{float(x['bolla_dorso_fine']):.3f}" if x["bolla_dorso_inizio"] else "–"
        te = f"{float(x['sep_TE_dorso']):.3f}" if x["sep_TE_dorso"] else "–"
        cs = byk.get(("CS", a))
        if cs and cs.get("cl_sec") is not None:
            m = xfoil_at_cl(xf, cs["cl_sec"])
            mb = f"{float(m['bolla_dorso_inizio']):.3f}–{float(m['bolla_dorso_fine']):.3f}" if m["bolla_dorso_inizio"] else "–"
            mt = f"{float(m['sep_TE_dorso']):.3f}" if m["sep_TE_dorso"] else "–"
            mm = f"{float(m['alpha']):g}°, {float(m['xtr_dorso']):.3f}, {mb}, {mt}"
        else:
            mm = "–"
        cells = []
        for n in ("CS", "CS_Re22", "CS_turb", "CS_lam", "DS", "CS_pdrag"):
            r = byk.get((n, a))
            cells.append("–" if not r else f"{it(r.get('x_tr'), 3)} / {it(r.get('x_sep_first'), 3)} / {it(r.get('x_sep_full'), 3)}")
        L.append(f"| {a:g} | {float(x['xtr_dorso']):.3f} | {bub} | {te} | {mm} | " + " | ".join(cells) + " |")
    # colonne XFOIL (testo del CSV) con la virgola decimale come il resto del file
    head, sep_, tail = "\n".join(L).partition("## Innesco")
    tail = re.sub(r"(?<=[ (|/])-(?=\d)", "−", re.sub(r"(?<=\d)\.(?=\d)", ",", tail))
    with open(os.path.join(HERE, "analisi.md"), "w", encoding="utf-8") as f:
        f.write(head + sep_ + tail + "\n")


def main():
    rows, profiles = analyse()
    diffs = vtk_diff(profiles)
    for lab, a, d in diffs:
        print(f"{lab}, aoa {a:g}: " + ", ".join(f"{k} {v:.3g}" for k, v in d.items()))
    xf = read_xfoil()
    write_outputs(rows, diffs, xf)
    plots(profiles, xf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
