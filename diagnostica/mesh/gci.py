#!/usr/bin/env python3
"""
gci.py - Analisi della convergenza di mesh (v2.6.0) dai run di run_mesh.py: numero di pannelli, primo pannello
al LE (x/c), tempo per run e GCI secondo Celik et al. (2008), "Procedure for Estimation and Reporting of
Uncertainty Due to Discretization in CFD Applications", J. Fluids Eng. 130(7):078001.

    r21 = (N1/N2)^(1/2), r32 = (N2/N3)^(1/2)   (mesh di superficie: 2 direzioni; 1 fine, 2 medium, 3 coarse)
    e21 = phi2 - phi1, e32 = phi3 - phi2, s = segno(e32/e21)
    p = |ln|e32/e21| + q(p)| / ln r21,  q(p) = ln((r21^p - s) / (r32^p - s))   (iterazione a punto fisso)
    phi_ext = (r21^p phi1 - phi2) / (r21^p - 1),  e_a = |(phi1 - phi2)/phi1|,  GCI_fine = Fs e_a / (r21^p - 1), Fs 1,25
    convergenza: R = e21/e32; 0 < R < 1 monotona, -1 < R < 0 oscillante, |R| > 1 divergente

Uso:  python diagnostica\\mesh\\gci.py   (scrive gci.md e gci.csv in questa cartella)
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
import postprocess as pp  # noqa: E402


QTY = ["CL", "CDi", "CDo", "CMy", "cl_sec_max", "sep_frac_up_le", "x_sep_up"]
LOADS = ["CL", "CDi", "CDo", "CMy", "cl_sec_max"]
FS = 1.25
LIMIT = 2.0          # % differenza medium-fine ammessa sui carichi


def read_kv(path):
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            if "=" in ln:
                k, v = (s.strip() for s in ln.split("=", 1))
                out[k] = v
    return out


def mesh_info(vtk_path):
    """Pannelli (poligoni del VTK = semiala) e primo pannello al LE in x/c sulla stazione di punti piu' vicina
    a eta = 0,5 (distanza media fra il punto di LE e i due punti adiacenti, divisa per la corda)."""
    v = pp.read_vtk(vtk_path)
    pts = v["pts"]
    ys = sorted({round(p[1], 6) for p in pts if p[1] >= 0})
    b = ys[-1]
    y0 = min(ys, key=lambda y: abs(y - 0.5 * b))
    st = [p for p in pts if abs(p[1] - y0) < 1e-6]
    xs = [p[0] for p in st]
    chord = max(xs) - min(xs)
    le = st[xs.index(min(xs))]
    d = sorted(math.dist((p[0], p[2]), (le[0], le[2])) for p in st if p is not le)
    return len(v["polys"]), 0.5 * (d[0] + d[1]) / chord, y0 / b


def gci(phi1, phi2, phi3, n1, n2, n3):
    r21, r32 = math.sqrt(n1 / n2), math.sqrt(n2 / n3)
    e21, e32 = phi2 - phi1, phi3 - phi2
    out = {"r21": r21, "r32": r32, "diff_mf_pct": 100 * (phi2 - phi1) / phi1 if phi1 else None}
    if e21 == 0 and e32 == 0:
        out.update(p=None, tipo="costante", gci=0.0, ext=phi1)
        return out
    if e21 == 0 or e32 == 0:
        out.update(p=None, tipo="non determinabile (una differenza nulla)", gci=None, ext=None)
        return out
    R = e21 / e32
    tipo = "monotona" if 0 < R < 1 else ("oscillante" if -1 < R < 0 else "divergente")
    s = 1.0 if e32 / e21 > 0 else -1.0
    p, q = 1.0, 0.0
    for _ in range(200):
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        try:
            q = math.log((r21 ** p_new - s) / (r32 ** p_new - s))
        except ValueError:
            break
        if abs(p_new - p) < 1e-10:
            p = p_new
            break
        p = p_new
    rp = r21 ** p
    ext = (rp * phi1 - phi2) / (rp - 1) if rp != 1 else None
    ea = abs((phi1 - phi2) / phi1) if phi1 else None
    out.update(p=p, tipo=tipo, R=R, ext=ext, gci=100 * FS * ea / (rp - 1) if ea is not None and rp != 1 else None)
    return out


def fmt(v, nd=4):
    if v is None:
        return "–"
    return f"{v:.{nd}f}".replace(".", ",").replace("-", "−")


FAMILIES = {
    "A": ("growth rate in corda 1,1 fisso (il primo pannello al LE scala di 3–4,5)", ["coarse", "medium", "fine"]),
    "B": ("growth rate in corda scalato 1,1^(120/u_pts) (famiglia geometricamente simile, Celik)",
          ["coarse_g", "medium", "fine_g"]),
}
MESH_TXT = {"coarse": "80 / 43, 1,1", "medium": "120 / 64, 1,1", "fine": "180 / 96, 1,1",
            "coarse_g": "80 / 43, 1,15369", "fine_g": "180 / 96, 1,0656"}


def load_level(lev):
    """Risultati di un livello: CL e CDi dal log (5 cifre significative), il resto da results.txt."""
    out = {}
    folder = os.path.join(HERE, "runs", lev)
    with open(os.path.join(folder, "summary.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        d = os.path.join(folder, r["design"])
        res = read_kv(os.path.join(d, "results.txt"))
        vals = {k: float(res[k]) for k in QTY}
        lg = pp.parse_log(os.path.join(d, "fs_log.txt"))
        vals["CL"], vals["CDi"] = lg["CL"], lg["CDi"]
        n, le, eta = mesh_info(os.path.join(d, "surface.vtk"))
        out[float(r["aoa"])] = {"v": vals, "N": n, "le": le, "t": float(r["wall_s"]), "status": res["status"]}
    return out


def main():
    data = {lev: load_level(lev) for lev in MESH_TXT}
    L = ["# Convergenza di mesh – configurazione D, ccs_wing (chord_scale 1), generato da gci.py", "",
         "CL e CDi dal log (5 cifre significative); CDo, CMy, cl_sec_max, sep_frac_up_le, x_sep_up da results.txt "
         "(CDo e CMy a 4 decimali). Celik et al. (2008): r = (N_i/N_j)^(1/2), Fs = 1,25.", "",
         "| livello | Mesh_U / Mesh_V, growth rate U | pannelli (semiala) | primo pannello al LE [x/c] | "
         "tempo per run [s] (4° / 12°) | status |", "|---|---|---|---|---|---|"]
    for lev in ["coarse", "coarse_g", "medium", "fine_g", "fine"]:
        a, b = data[lev][4.0], data[lev][12.0]
        L.append(f"| {lev} | {MESH_TXT[lev]} | {a['N']} | {fmt(a['le'], 5)} | {fmt(a['t'], 1)} / {fmt(b['t'], 1)} | "
                 f"{a['status']} / {b['status']} |")
    rows_csv, verdicts = [], {}
    for fam, (desc, levs) in FAMILIES.items():
        c, m, fi = levs
        verdict = []
        L += ["", f"## Famiglia {fam}: {desc}"]
        for aoa in (4.0, 12.0):
            n = [data[x][aoa]["N"] for x in (fi, m, c)]
            L += ["", f"### α = {aoa:g}°", "",
                  "| grandezza | coarse | medium | fine | medium–fine [%] | R | convergenza | p | φ_ext | GCI_fine [%] |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for k in QTY:
                ph = {x: data[x][aoa]["v"][k] for x in levs}
                g = gci(ph[fi], ph[m], ph[c], *n)
                nd = 5 if k in ("CL", "CDi") else 4
                L.append(f"| {k} | {fmt(ph[c], nd)} | {fmt(ph[m], nd)} | {fmt(ph[fi], nd)} | {fmt(g['diff_mf_pct'], 2)} | "
                         f"{fmt(g.get('R'), 3)} | {g['tipo']} | {fmt(g['p'], 2)} | {fmt(g['ext'], nd)} | {fmt(g['gci'], 2)} |")
                rows_csv.append({"famiglia": fam, "aoa": aoa, "grandezza": k, "coarse": ph[c], "medium": ph[m],
                                 "fine": ph[fi], **{kk: g.get(kk) for kk in
                                                    ("diff_mf_pct", "R", "tipo", "p", "ext", "gci", "r21", "r32")}})
                if k in LOADS:
                    verdict.append((aoa, k, g["diff_mf_pct"]))
        worst = max(verdict, key=lambda t: abs(t[2] or 0))
        ok = all(t[2] is not None and abs(t[2]) < LIMIT for t in verdict)
        bad = [f"{k} {fmt(d, 2)} % (α {a:g}°)" for a, k, d in verdict if d is None or abs(d) >= LIMIT]
        verdicts[fam] = (ok, worst, bad)
        r21 = next(r["r21"] for r in rows_csv if r["famiglia"] == fam)
        r32 = next(r["r32"] for r in rows_csv if r["famiglia"] == fam)
        L += ["", f"r21 = {fmt(r21, 3)}, r32 = {fmt(r32, 3)}. **Criterio (|medium − fine| < {LIMIT:g} % su CL, CDi, CDo, "
                  f"CMy, cl_sec_max): {'SUPERATO' if ok else 'NON SUPERATO'}**"
              + (f" — oltre il limite: {'; '.join(bad)}." if bad else f" — massimo {fmt(worst[2], 2)} % ({worst[1]}).")]
    with open(os.path.join(HERE, "gci.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(HERE, "gci.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_csv[0]))
        w.writeheader()
        w.writerows(rows_csv)
    for fam, (ok, worst, bad) in verdicts.items():
        print(f"famiglia {fam}: {'SUPERATO' if ok else 'NON SUPERATO'} ({len(bad)} carichi oltre il limite)")
    return 0 if all(v[0] for v in verdicts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
