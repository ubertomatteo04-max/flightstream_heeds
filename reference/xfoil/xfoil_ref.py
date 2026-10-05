#!/usr/bin/env python3
"""
xfoil_ref.py - Punto 4 bis, Parte 2: riferimento 2D XFOIL 6.99 per il profilo della semiala (SOLO RIFERIMENTO).

Per ogni sessione scrive un file di comandi in work\\, lo passa a xfoil.exe (subprocess con timeout) e legge
polare, DUMP (s, x, y, Ue, d*, theta, cf, H) e CPWR (Cp). Impostazioni: PPAR N = 160, Re = 474985,
M = 0,059, Ncrit = 9 (sensibilita' 7 e 11), ITER 200, alfa da -4 a 18 deg con passo 0,5 in due sequenze
(0 -> 18 e 0 -> -4, sessioni separate). Ogni alfa e' un comando ALFA seguito da DUMP e CPWR: e' la stessa
continuazione di ASEQ, ma lascia lo strato limite di ogni punto.

Uscite in questa cartella: inviscido.csv, polare_N{7,9,11}.csv, dump_N9_a{00,04,08,12,clmax}.csv,
riepilogo_N9.csv (x_tr, bolla, separazione al TE per ogni alfa), summary.md, grafici *.png.
Interprete: Python di HEEDS (numpy, matplotlib). XFOIL: ..\\..\\..\\tools\\XFOIL6.99\\xfoil.exe (o --xfoil).

Uso:  python xfoil_ref.py [--xfoil <xfoil.exe>] [--only-check]
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
XFOIL_DEFAULT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "tools", "XFOIL6.99", "xfoil.exe"))
RE, MACH, NPAN, ITER = 474985, 0.059, 160, 200
A_MIN, A_MAX, DA = -4.0, 18.0, 0.5
ALPHA0_FS = -1.98            # -CL0/CLa dello Study_2 (ala rettangolare non svergolata), deg
ALPHA0_TOL = 0.2
DUMP_ALPHAS = [0.0, 4.0, 8.0, 12.0]
CF_SEP = 0.0                 # separato: cf < 0
TIMEOUT_S = 600


def tag(a):
    return f"{'m' if a < 0 else ''}{abs(a):05.2f}".replace(".", "p")


def run_xfoil(exe, name, cmds, timeout=TIMEOUT_S):
    """Scrive il file di comandi work\\<name>.inp, lancia XFOIL con stdin = file e restituisce lo stdout."""
    inp = os.path.join(WORK, f"{name}.inp")
    with open(inp, "w", encoding="ascii") as f:
        f.write("\n".join(cmds) + "\n")
    with open(inp, "r", encoding="ascii") as fin:
        try:
            r = subprocess.run([exe], stdin=fin, cwd=WORK, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            open(os.path.join(WORK, f"{name}.out"), "w", encoding="utf-8").write(out)
            raise RuntimeError(f"XFOIL: timeout di {timeout} s nella sessione {name}")
    with open(os.path.join(WORK, f"{name}.out"), "w", encoding="utf-8") as f:
        f.write(r.stdout)
    return r.stdout


def head_cmds():
    return ["PLOP", "G", "", "LOAD vespa.dat", "PPAR", f"N {NPAN}", "", "", "OPER", f"MACH {MACH}"]


def read_polar(path):
    """Polare di XFOIL -> lista di dizionari (alpha, CL, CD, CDp, CM, Top_Xtr, Bot_Xtr)."""
    rows, cols = [], None
    with open(path, "r", encoding="ascii", errors="replace") as f:
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


def read_table(path):
    """File di XFOIL con intestazione '#' -> array (le righe non numeriche vengono saltate)."""
    data = []
    with open(path, "r", encoding="ascii", errors="replace") as f:
        for ln in f:
            t = ln.split()
            if not t or ln.lstrip().startswith("#"):
                continue
            try:
                data.append([float(v) for v in t])
            except ValueError:
                continue
    n = min(len(r) for r in data)
    return np.array([r[:n] for r in data])


def surfaces(dump_path, cp_path):
    """DUMP + CPWR -> dizionario per 'dorso' e 'ventre' con x/c, Cp, H, cf, Ue (ordinati per x crescente).
    I primi N punti del DUMP sono il profilo (TE dorso -> LE -> TE ventre), poi la scia."""
    d, c = read_table(dump_path), read_table(cp_path)
    n = len(c)
    d = d[:n]
    if np.max(np.abs(d[:, 1] - c[:, 0])) > 1e-4:
        raise RuntimeError(f"DUMP e CPWR non allineati: {dump_path}")
    ile = int(np.argmin(d[:, 1]))
    # punto di ristagno: cambio di segno di Ue (Ue/Vinf con segno nel DUMP di 6.99)
    ue = d[:, 3]
    sgn = np.where(np.diff(np.sign(ue)) != 0)[0]
    ist = int(sgn[0]) + 1 if len(sgn) else ile
    out = {}
    for side, idx in (("dorso", np.arange(ist - 1, -1, -1)), ("ventre", np.arange(ist, n))):
        out[side] = {"x": d[idx, 1], "y": d[idx, 2], "Cp": c[idx, 2], "H": d[idx, 7], "cf": d[idx, 6],
                     "Ue": np.abs(ue[idx]), "theta": d[idx, 5], "dstar": d[idx, 4]}
    return out


def sep_regions(s, x_tr):
    """Zone con cf < 0 lungo il dorso (dal ristagno al TE): lista di (x_inizio, x_fine, tocca_TE).
    Inizio/fine interpolati linearmente dove cf cambia segno."""
    x, cf = s["x"], s["cf"]
    neg = cf < CF_SEP
    regs, i, n = [], 0, len(x)
    while i < n:
        if neg[i]:
            j = i
            while j + 1 < n and neg[j + 1]:
                j += 1
            xa = x[i] if i == 0 else x[i - 1] + (x[i] - x[i - 1]) * cf[i - 1] / (cf[i - 1] - cf[i])
            if j == n - 1:
                xb, te = 1.0, True
            else:
                xb, te = x[j] + (x[j + 1] - x[j]) * cf[j] / (cf[j] - cf[j + 1]), False
            regs.append((float(xa), float(xb), te))
            i = j + 1
        else:
            i += 1
    return regs


def classify(regs, x_tr):
    """Bolla laminare = zona che inizia prima della transizione; separazione turbolenta = zona che inizia
    dopo la transizione e arriva al TE."""
    bubble = next(((a, b) for a, b, te in regs if a <= x_tr + 1e-3 and not te), None)
    te_sep = next((a for a, b, te in regs if te and a > x_tr), None)
    lam_to_te = next((a for a, b, te in regs if te and a <= x_tr), None)
    return bubble, te_sep, lam_to_te


def sequence_cmds(alphas, ncrit, polar, dumps):
    c = head_cmds() + [f"VISC {RE}", "VPAR", f"N {ncrit}", "", f"ITER {ITER}", "PACC", polar, ""]
    for a in alphas:
        c.append(f"ALFA {a:g}")
        if dumps:
            c += [f"DUMP d_{tag(a)}.txt", f"CPWR c_{tag(a)}.txt"]
    return c + ["PACC", "", "QUIT"]


def run_polar(exe, ncrit, dumps):
    """Due sessioni (0 -> 18, 0 -> -4) con ALFA in continuazione; polare unita e punti non convergenti."""
    pos = list(np.arange(0.0, A_MAX + 1e-9, DA))
    neg = list(np.arange(0.0, A_MIN - 1e-9, -DA))
    rows = {}
    for name, seq in (("pos", pos), ("neg", neg)):
        pol = f"polar_N{ncrit}_{name}.txt"
        if os.path.exists(os.path.join(WORK, pol)):
            os.remove(os.path.join(WORK, pol))
        run_xfoil(exe, f"N{ncrit}_{name}", sequence_cmds(seq, ncrit, pol, dumps))
        for r in read_polar(os.path.join(WORK, pol)):
            rows.setdefault(round(r["alpha"], 3), r)
    wanted = sorted(set(round(a, 3) for a in pos + neg))
    missing = [float(a) for a in wanted if a not in rows]
    return [rows[a] for a in sorted(rows)], missing


def write_csv(path, rows, keys):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] if not isinstance(r[k], float) else f"{r[k]:.6g}" for k in keys])


def linfit(a, cl):
    p = np.polyfit(a, cl, 1)
    return p[0], -p[1] / p[0]          # pendenza [/deg], alfa a CL = 0 [deg]


def inviscid_check(exe):
    pol = "polar_inv.txt"
    if os.path.exists(os.path.join(WORK, pol)):
        os.remove(os.path.join(WORK, pol))
    run_xfoil(exe, "inviscido", head_cmds() + ["PACC", pol, "", "ASEQ -4 4 0.5", "PACC", "", "QUIT"])
    rows = read_polar(os.path.join(WORK, pol))
    a = np.array([r["alpha"] for r in rows]); cl = np.array([r["CL"] for r in rows])
    slope, a0 = linfit(a, cl)
    write_csv(os.path.join(HERE, "inviscido.csv"), rows, ["alpha", "CL", "CDp", "CM"])
    return a0, slope, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xfoil", default=XFOIL_DEFAULT)
    ap.add_argument("--only-check", action="store_true", help="solo il controllo di alfa0 inviscido")
    a = ap.parse_args()
    if not os.path.isfile(a.xfoil):
        sys.exit(f"xfoil.exe non trovato: {a.xfoil}")
    os.makedirs(WORK, exist_ok=True)
    shutil.copy(os.path.join(HERE, "vespa.dat"), os.path.join(WORK, "vespa.dat"))

    a0_inv, sl_inv, _ = inviscid_check(a.xfoil)
    print(f"alfa0 inviscido XFOIL = {a0_inv:+.3f} deg (FS Study_2 {ALPHA0_FS:+.2f}), "
          f"pendenza {sl_inv:.5f} /deg = {np.degrees(sl_inv):.3f} /rad")
    if abs(a0_inv - ALPHA0_FS) > ALPHA0_TOL:
        sys.exit(f"STOP: alfa0 differisce di {a0_inv - ALPHA0_FS:+.3f} deg (> {ALPHA0_TOL}): controllare il profilo")
    if a.only_check:
        return 0

    polars, missing = {}, {}
    for n in (9, 7, 11):
        polars[n], missing[n] = run_polar(a.xfoil, n, dumps=(n == 9))
        write_csv(os.path.join(HERE, f"polare_N{n}.csv"), polars[n],
                  ["alpha", "CL", "CD", "CDp", "CM", "Top_Xtr", "Bot_Xtr"])
        print(f"Ncrit {n}: {len(polars[n])} punti convergenti, non convergenti: {missing[n] or 'nessuno'}")

    # riepilogo per alfa (Ncrit 9) dai DUMP
    p9 = polars[9]
    summ = []
    for r in p9:
        al = r["alpha"]
        dp, cp = os.path.join(WORK, f"d_{tag(al)}.txt"), os.path.join(WORK, f"c_{tag(al)}.txt")
        if not (os.path.exists(dp) and os.path.exists(cp)):
            continue
        sf = surfaces(dp, cp)
        up = sf["dorso"]
        regs = sep_regions(up, r["Top_Xtr"])
        bub, te_sep, lam_te = classify(regs, r["Top_Xtr"])
        regs_lo = sep_regions(sf["ventre"], r["Bot_Xtr"])
        bub_lo, te_lo, _ = classify(regs_lo, r["Bot_Xtr"])
        summ.append({"alpha": al, "CL": r["CL"], "CD": r["CD"], "CM": r["CM"],
                     "xtr_dorso": r["Top_Xtr"], "xtr_ventre": r["Bot_Xtr"],
                     "bolla_dorso_inizio": bub[0] if bub else "", "bolla_dorso_fine": bub[1] if bub else "",
                     "sep_TE_dorso": te_sep if te_sep is not None else "",
                     "sep_lam_fino_TE_dorso": lam_te if lam_te is not None else "",
                     "x_sep_dorso_primo": regs[0][0] if regs else "",
                     "bolla_ventre_inizio": bub_lo[0] if bub_lo else "",
                     "bolla_ventre_fine": bub_lo[1] if bub_lo else "",
                     "sep_TE_ventre": te_lo if te_lo is not None else "",
                     "H_max_dorso": float(np.max(up["H"]))})
    keys = list(summ[0])
    write_csv(os.path.join(HERE, "riepilogo_N9.csv"), summ, keys)

    # cl_max e dump richiesti
    cl = np.array([r["CL"] for r in p9]); al = np.array([r["alpha"] for r in p9])
    k = int(np.argmax(cl))
    clmax, a_stall = cl[k], al[k]
    for a_d, lab in [(x, f"a{int(x):02d}") for x in DUMP_ALPHAS] + [(a_stall, "clmax")]:
        dp, cp = os.path.join(WORK, f"d_{tag(a_d)}.txt"), os.path.join(WORK, f"c_{tag(a_d)}.txt")
        if not os.path.exists(dp) or round(a_d, 3) in missing[9]:
            print(f"dump a {a_d} non disponibile o non convergente")
            continue
        sf = surfaces(dp, cp)
        with open(os.path.join(HERE, f"dump_N9_{lab}.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["lato", "x_c", "y_c", "Cp", "H", "cf", "Ue_Vinf", "theta_c", "dstar_c"])
            for side in ("dorso", "ventre"):
                s = sf[side]
                for j in range(len(s["x"])):
                    w.writerow([side] + [f"{s[c][j]:.6g}" for c in ("x", "y", "Cp", "H", "cf", "Ue", "theta", "dstar")])

    # numeri del summary
    lin = (al >= -2.0) & (al <= 6.0)
    sl_v, a0_v = linfit(al[lin], cl[lin])
    cd = np.array([r["CD"] for r in p9])
    kcd = int(np.argmin(cd))
    ld = cl / cd
    kld = int(np.argmax(ld))
    res = {"a0_inv": a0_inv, "sl_inv": sl_inv, "a0_v": a0_v, "sl_v": sl_v, "clmax": clmax, "a_stall": a_stall,
           "cdmin": cd[kcd], "a_cdmin": al[kcd], "cl_cdmin": cl[kcd], "ldmax": ld[kld], "a_ldmax": al[kld]}
    for n in (7, 11):
        c2 = np.array([r["CL"] for r in polars[n]]); a2 = np.array([r["alpha"] for r in polars[n]])
        k2 = int(np.argmax(c2))
        res[f"clmax_N{n}"], res[f"a_stall_N{n}"] = c2[k2], a2[k2]
    write_summary(res, summ, missing, polars)
    make_plots(polars, res)
    print(f"cl_max {clmax:.4f} a {a_stall:g} deg; cd_min {cd[kcd]:.5f} a {al[kcd]:g} deg")
    return 0


def fmt(v, nd=3):
    return "–" if v == "" or v is None else f"{v:.{nd}f}"


def write_summary(res, summ, missing, polars):
    L = ["# XFOIL 6.99 – riferimento 2D del profilo della semiala (vespa.dat)", "",
         "**SOLO RIFERIMENTO** per la diagnosi del modello di separazione di FlightStream (punto 4 bis). "
         f"Re = {RE}, M = {MACH}, PPAR N = {NPAN}, ITER {ITER}, Ncrit 9 (sensibilità 7 e 11), alfa da {A_MIN:g} a "
         f"{A_MAX:g}° con passo {DA:g}° in due sequenze da 0° (0 → 18, 0 → −4). TE tozzo (0,652 % c). "
         "Generato da `xfoil_ref.py`.", "",
         "| grandezza | valore |", "|---|---|",
         f"| α₀ inviscido | {res['a0_inv']:+.3f}° (FlightStream Study_2: −CL₀/CLα = {ALPHA0_FS:+.2f}°; scarto "
         f"{res['a0_inv'] - ALPHA0_FS:+.3f}°, tolleranza ±{ALPHA0_TOL}°: **OK**) |",
         f"| pendenza inviscida | {np.degrees(res['sl_inv']):.3f} /rad ({res['sl_inv']:.5f} /deg) |",
         f"| α₀ viscoso (fit −2…6°) | {res['a0_v']:+.3f}° |",
         f"| a₀ viscosa (fit −2…6°) | {np.degrees(res['sl_v']):.3f} /rad ({res['sl_v']:.5f} /deg) |",
         f"| cl_max (Ncrit 9) | {res['clmax']:.4f} a α = {res['a_stall']:g}° (α di stallo) |",
         f"| cl_max Ncrit 7 / 11 | {res['clmax_N7']:.4f} a {res['a_stall_N7']:g}° / {res['clmax_N11']:.4f} a {res['a_stall_N11']:g}° |",
         f"| cd_min | {res['cdmin']:.5f} a α = {res['a_cdmin']:g}° (cl = {res['cl_cdmin']:.3f}) |",
         f"| (l/d)_max | {res['ldmax']:.1f} a α = {res['a_ldmax']:g}° |", "",
         "Punti non convergenti (assenti dalla polare): " +
         "; ".join(f"Ncrit {n}: {', '.join(f'{a:g}' for a in missing[n]) or 'nessuno'}" for n in (9, 7, 11)), "",
         "## Strato limite del dorso per α (Ncrit 9)", "",
         "x/c da DUMP: transizione = Top_Xtr della polare; bolla = zona con cf < 0 che inizia prima della transizione "
         "e riattacca; separazione al TE = zona con cf < 0 che inizia dopo la transizione e arriva al TE.", "",
         "| α [°] | cl | cd | cm | x_tr dorso | bolla dorso (inizio–fine) | sep. TE dorso | x_tr ventre | bolla ventre |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in summ:
        bub = "–" if r["bolla_dorso_inizio"] == "" else f"{r['bolla_dorso_inizio']:.3f}–{r['bolla_dorso_fine']:.3f}"
        te = fmt(r["sep_TE_dorso"]) if r["sep_TE_dorso"] != "" else (
            f"lam. {r['sep_lam_fino_TE_dorso']:.3f}" if r["sep_lam_fino_TE_dorso"] != "" else "–")
        bl = "–" if r["bolla_ventre_inizio"] == "" else f"{r['bolla_ventre_inizio']:.3f}–{r['bolla_ventre_fine']:.3f}"
        L.append(f"| {r['alpha']:g} | {r['CL']:.4f} | {r['CD']:.5f} | {r['CM']:.4f} | {r['xtr_dorso']:.3f} | {bub} | {te} | "
                 f"{r['xtr_ventre']:.3f} | {bl} |")
    L += ["", "## Sensibilità a Ncrit (x_tr dorso)", "", "| α [°] | Ncrit 7 | Ncrit 9 | Ncrit 11 |", "|---|---|---|---|"]
    by = {n: {round(r["alpha"], 3): r for r in polars[n]} for n in (7, 9, 11)}
    for al in (0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0):
        L.append(f"| {al:g} | " + " | ".join(
            f"{by[n][al]['Top_Xtr']:.3f} (cl {by[n][al]['CL']:.3f})" if al in by[n] else "n.c." for n in (7, 9, 11)) + " |")
    L += ["", "File: `polare_N{7,9,11}.csv`, `inviscido.csv`, `riepilogo_N9.csv` (tutti gli α), "
          "`dump_N9_a{00,04,08,12,clmax}.csv` (x/c, Cp, H, cf per dorso e ventre), grafici `cl_alpha.png`, `cl_cd.png`, "
          "`cm_alpha.png`, `H_dorso.png`, `cf_dorso.png`. Comandi e output grezzi di XFOIL in `work\\` (non nel repo)."]
    text = re.sub(r"(?<=\d)\.(?=\d)", ",", "\n".join(L)).replace("XFOIL 6,99", "XFOIL 6.99")
    text = re.sub(r"(?<=[ (|/])-(?=\d)", "−", text)
    with open(os.path.join(HERE, "summary.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")


def make_plots(polars, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sty = {9: dict(color="#1f4e9c", lw=1.8, marker="o", ms=3), 7: dict(color="#d9822b", lw=1.0, ls="--"),
           11: dict(color="#3a8d4f", lw=1.0, ls=":")}

    def col(n, k):
        return np.array([r[k] for r in polars[n]])

    def fig(name, xk, yk, xl, yl, title):
        f, ax = plt.subplots(figsize=(6.4, 4.6))
        for n in (9, 7, 11):
            ax.plot(col(n, xk), col(n, yk), label=f"Ncrit {n}", **sty[n])
        if name == "cl_alpha.png":
            a = np.linspace(-4, 8, 2)
            ax.plot(a, res["sl_inv"] * (a - res["a0_inv"]), color="k", lw=0.8, label="inviscido (retta)")
            ax.axvline(res["a_stall"], color="#888", lw=0.6)
        ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(title); ax.grid(alpha=0.3); ax.legend()
        f.tight_layout(); f.savefig(os.path.join(HERE, name), dpi=150); plt.close(f)

    fig("cl_alpha.png", "alpha", "CL", "α [°]", "cl", f"XFOIL, Re {RE}: cl–α")
    fig("cl_cd.png", "CD", "CL", "cd", "cl", f"XFOIL, Re {RE}: polare cl–cd")
    fig("cm_alpha.png", "alpha", "CM", "α [°]", "cm (c/4)", f"XFOIL, Re {RE}: cm–α")
    for var, yl, name in (("H", "H", "H_dorso.png"), ("cf", "cf", "cf_dorso.png")):
        f, ax = plt.subplots(figsize=(6.4, 4.6))
        for al, c in ((4.0, "#1f4e9c"), (8.0, "#d9822b"), (12.0, "#b8322a")):
            dp, cp = os.path.join(WORK, f"d_{tag(al)}.txt"), os.path.join(WORK, f"c_{tag(al)}.txt")
            if os.path.exists(dp):
                s = surfaces(dp, cp)["dorso"]
                ax.plot(s["x"], s[var], color=c, lw=1.4, label=f"α = {al:g}°")
        if var == "cf":
            ax.axhline(0, color="k", lw=0.6)
            ax.set_ylim(-0.005, 0.015)
        ax.set_xlabel("x/c"); ax.set_ylabel(yl); ax.set_title(f"XFOIL Ncrit 9: {yl} sul dorso"); ax.grid(alpha=0.3)
        ax.legend(); f.tight_layout(); f.savefig(os.path.join(HERE, name), dpi=150); plt.close(f)


if __name__ == "__main__":
    sys.exit(main())
