#!/usr/bin/env python3
"""
te_compare.py - Punto 3.4 (v2.6.0, SOLO DIAGNOSTICA): confronto delle varianti del bordo d'uscita in ccs_wing
(mesh medium): blended (attuale), sharp (te_type "sharp"), blunt (proto_te_blunt.py) a 4 e 12 gradi.
Per ognuna: CL e CMy (carichi, come in results.txt), geometria del TE sulla stazione a eta = 0,5, Cp vicino al TE e bolla sul
ventre (cf < 0) sulla striscia di celle a eta ~ 0,5. Scrive te.md e te_cp.png. Interprete: Python di HEEDS.
"""
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO)
import postprocess as pp  # noqa: E402

FRAME = pp.parse_wing_frame({"chord_axis": "+x", "span_axis": "+y", "up_axis": "+z", "span_root_m": 0.0})
VARIANTS = {"blended (attuale)": "medium/Design_{d}", "sharp": "te_sharp/Design_{d}", "blunt": "te_blunt/a{a}"}
DESIGN = {4: "001", 12: "002"}


def load(rel, aoa):
    d = os.path.join(HERE, "runs", rel.format(d=DESIGN[aoa], a=aoa))
    v = pp.read_vtk(os.path.join(d, "surface.vtk"))
    res = {}
    with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
        for ln in f:
            k, _, val = ln.strip().partition(" = ")
            res[k] = val
    cells = [c for c in pp.wing_cells(v, FRAME) if c["side"] in ("up", "lo")]
    pts, polys, f = v["pts"], v["polys"], v["cell"]
    # facce di base (blunt): normale quasi lungo x
    cells = [c for c in cells if abs(pp._newell([pts[k] for k in polys[c["i"]]])[0]) < 0.7]
    etas = sorted({round(c["eta"], 4) for c in cells})
    e0 = min(etas, key=lambda e: abs(e - 0.5))
    row = [c for c in cells if round(c["eta"], 4) == e0]
    prof = {}
    for side in ("up", "lo"):
        cs = sorted((c for c in row if c["side"] == side), key=lambda c: c["xc"])
        prof[side] = [(c["xc"], f["Cp_freestream"][c["i"]], f["skin_friction_coeff."][c["i"]]) for c in cs]
    ys = sorted({round(p[1], 6) for p in pts})
    y0 = min(ys, key=lambda y: abs(y - 1.32))
    st = [p for p in pts if abs(p[1] - y0) < 1e-6]
    xmax = max(p[0] for p in st)
    te_z = sorted(p[2] for p in st if abs(p[0] - xmax) < 1e-6)
    return {"CL": float(res["CL"]), "CMy": float(res["CMy"]), "res": res, "prof": prof, "te_z": te_z, "eta": e0}


def lower_bubble(prof):
    lo = prof["lo"]
    neg = [x for x, cp, cf in lo if cf < 0 and x > 0.5]
    return (min(neg), max(neg)) if neg else None


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = {(n, a): load(rel, a) for n, rel in VARIANTS.items() for a in (4, 12)}
    L = ["# Bordo d'uscita: varianti in ccs_wing (mesh medium), generato da te_compare.py", "",
         "| variante | α | CL | ΔCL vs blended | CMy | ΔCMy vs blended | z del TE a η 0,5 [m] | "
         "bolla ventre (cf < 0, x/c) | sep_frac_lo_te | Cp dorso / ventre a x/c ≈ 0,97 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for a in (4, 12):
        ref = data[("blended (attuale)", a)]
        for n in VARIANTS:
            d = data[(n, a)]
            b = lower_bubble(d["prof"])
            cp = []
            for side in ("up", "lo"):
                near = min(d["prof"][side], key=lambda t: abs(t[0] - 0.97))
                cp.append(f"{near[1]:+.3f}")
            dcl = 100 * (d["CL"] - ref["CL"]) / ref["CL"]
            dcm = 100 * (d["CMy"] - ref["CMy"]) / ref["CMy"]
            L.append(f"| {n} | {a} | {d['CL']:.4f} | {dcl:+.2f} % | {d['CMy']:.4f} | {dcm:+.2f} % | "
                     f"{', '.join(f'{z:.5f}' for z in d['te_z'])} | {('%.3f–%.3f' % b) if b else '–'} | "
                     f"{float(d['res']['sep_frac_lo_te']):.4f} | {cp[0]} / {cp[1]} |")
    L += ["", "CCS: TE del dorso z = 0,01708 m, del ventre z = 0,01483 m (spessore 0,652 % c), x = 0,3472 m."]
    with open(os.path.join(HERE, "te.md"), "w", encoding="utf-8") as fo:
        fo.write(re.sub(r"(?<=\d)\.(?=\d)", ",", "\n".join(L)) + "\n")
    f, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    cols = {"blended (attuale)": "#1f4e9c", "sharp": "#d9822b", "blunt": "#b8322a"}
    for ax, a in zip(axs, (4, 12)):
        for n, c in cols.items():
            p = data[(n, a)]["prof"]
            for side, ls in (("up", "-"), ("lo", "--")):
                xs = [t[0] for t in p[side] if t[0] > 0.7]
                ax.plot(xs, [t[1] for t in p[side] if t[0] > 0.7], color=c, ls=ls, lw=1.3,
                        label=f"{n} {'dorso' if side == 'up' else 'ventre'}")
        ax.invert_yaxis(); ax.grid(alpha=0.3); ax.set_xlabel("x/c"); ax.set_ylabel("Cp")
        ax.set_title(f"Cp vicino al TE, α = {a}°, η ≈ 0,5"); ax.legend(fontsize=7)
    f.tight_layout(); f.savefig(os.path.join(HERE, "te_cp.png"), dpi=150); plt.close(f)
    print("scritti te.md e te_cp.png")


if __name__ == "__main__":
    main()
