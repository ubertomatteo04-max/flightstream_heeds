"""Diagnosi degli indicatori di strato limite sui surface.vtk del DOE fixed (solo analisi).
Uso: python diagnostica/diag_bl.py, dopo
     python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8,10,12   (in mock_runs)."""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # cartella fs_heeds_pipeline
sys.path.insert(0, ROOT)
import postprocess as pp  # noqa: E402

DESIGNS = {0: "Design_001", 4: "Design_003", 8: "Design_005", 12: "Design_007"}
HCAP = 3.9155
XBINS = [(0.0, 0.05), (0.05, 0.20), (0.20, 0.80), (0.80, 1.0001)]
EBINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.95), (0.95, 1.0001)]
NSTRIP = 60


def newell(q):
    n = [0.0, 0.0, 0.0]
    m = len(q)
    for a in range(m):
        p0, p1 = q[a], q[(a + 1) % m]
        n[0] += (p0[1] - p1[1]) * (p0[2] + p1[2])
        n[1] += (p0[2] - p1[2]) * (p0[0] + p1[0])
        n[2] += (p0[0] - p1[0]) * (p0[1] + p1[1])
    s = math.sqrt(sum(v * v for v in n)) or 1.0
    return [v / s for v in n]


def load(aoa):
    v = pp.read_vtk(os.path.join(ROOT, "mock_runs", DESIGNS[aoa], "surface.vtk"))
    c = v["cell"]
    pts, polys = v["pts"], v["polys"]
    cen = [[sum(pts[k][j] for k in p) / len(p) for j in range(3)] for p in polys]
    nrm = [newell([pts[k] for k in p]) for p in polys]
    half = [i for i, ce in enumerate(cen) if ce[1] >= 0]
    # orientamento: sul dorso (z alto) la normale esterna ha nz > 0
    up = [i for i in half if nrm[i][2] > 0]
    dn = [i for i in half if nrm[i][2] < 0]
    zu = sum(cen[i][2] for i in up) / len(up)
    zd = sum(cen[i][2] for i in dn) / len(dn)
    sgn = 1.0 if zu > zd else -1.0
    b_half = max(cen[i][1] for i in half)
    # corda locale per fascia in apertura, dai vertici
    xs = {}
    for i in half:
        s = min(int(cen[i][1] / b_half * NSTRIP), NSTRIP - 1)
        for k in polys[i]:
            lo, hi = xs.get(s, (1e9, -1e9))
            xs[s] = (min(lo, pts[k][0]), max(hi, pts[k][0]))
    d = {"aoa": aoa, "half": half, "b_half": b_half}
    rows = []
    for i in half:
        s = min(int(cen[i][1] / b_half * NSTRIP), NSTRIP - 1)
        x_le, x_te = xs[s]
        n = [sgn * v for v in nrm[i]]
        if abs(n[1]) > 0.7:
            side = "estremita"
        else:
            side = "dorso" if n[2] > 0 else "ventre"
        rows.append({"i": i, "strip": s, "xc": (cen[i][0] - x_le) / (x_te - x_le), "eta": cen[i][1] / b_half,
                     "side": side, "cf": c["skin_friction_coeff."][i], "H": c["BL_shape_factor"][i],
                     "tr": c["Transition_marker"][i], "sep": c["Separation_marker"][i], "A": c["Area"][i],
                     "Cp": c["Cp_freestream"][i], "Vx": c["Vx"][i], "nx": n[0]})
    d["rows"] = rows
    d["A_tot"] = sum(r["A"] for r in rows)
    return d


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def describe(d, sel, name):
    rows = [r for r in d["rows"] if sel(r)]
    A = sum(r["A"] for r in rows)
    out = {"name": name, "n": len(rows), "frac": pct(A, d["A_tot"])}
    for s in ("dorso", "ventre", "estremita"):
        out[s] = pct(sum(r["A"] for r in rows if r["side"] == s), A)
    out["x"] = [pct(sum(r["A"] for r in rows if lo <= r["xc"] < hi and r["side"] != "estremita"), A) for lo, hi in XBINS]
    out["eta"] = [pct(sum(r["A"] for r in rows if lo <= r["eta"] < hi), A) for lo, hi in EBINS]
    return out, rows


def stagnation(d):
    """Per ogni fascia in apertura: cella con Cp massimo (esclusa l'estremita'). Coordinata con segno
    s = +x/c sul dorso, -x/c sul ventre."""
    best = {}
    for r in d["rows"]:
        if r["side"] == "estremita":
            continue
        if r["strip"] not in best or r["Cp"] > best[r["strip"]]["Cp"]:
            best[r["strip"]] = r
    return best


def sgn_s(r):
    return r["xc"] if r["side"] == "dorso" else -r["xc"]


def main():
    data = {a: load(a) for a in DESIGNS}
    print("celle (meta' y>=0):", {a: len(d["rows"]) for a, d in data.items()},
          " b_half:", round(data[0]["b_half"], 4))

    for title, sel in (("cf < 0", lambda r: r["cf"] < 0), ("H al tetto 3,9155", lambda r: abs(r["H"] - HCAP) < 1e-3)):
        print(f"\n### {title}")
        print("| aoa | n celle | % area | % dorso | % ventre | % estremita | x/c 0-5 | 5-20 | 20-80 | 80-100 |"
              " eta 0-.2 | .2-.4 | .4-.6 | .6-.8 | .8-.95 | .95-1 |")
        print("|" + "---|" * 16)
        for a, d in data.items():
            o, _ = describe(d, sel, title)
            f = lambda v: "-" if v != v else f"{v:.0f}"
            print(f"| {a} | {o['n']} | {o['frac']:.2f} | {f(o['dorso'])} | {f(o['ventre'])} | {f(o['estremita'])} | "
                  + " | ".join(f(v) for v in o["x"]) + " | " + " | ".join(f(v) for v in o["eta"]) + " |")

    print("\n### (b) cf < 0 al bordo d'attacco e punto di ristagno")
    print("| aoa | x/c ristagno (mediana, lato) | celle cf<0 con x/c<5% | di cui tra ristagno e bordo d'attacco |"
          " cf<0 con Vx<0 (tutte) | Vx<0 con cf<0 (tutte) | cf<0 a valle del 5% |")
    print("|---|---|---|---|---|---|---|")
    for a, d in data.items():
        st = stagnation(d)
        sides = [r["side"] for r in st.values()]
        xst = sorted(r["xc"] for r in st.values())
        le = [r for r in d["rows"] if r["cf"] < 0 and r["xc"] < 0.05 and r["side"] != "estremita"]
        between = 0
        for r in le:
            s0, s = sgn_s(st[r["strip"]]), sgn_s(r)
            if (s0 < 0 and s0 <= s <= 0) or (s0 > 0 and 0 <= s <= s0):
                between += 1
        neg = [r for r in d["rows"] if r["cf"] < 0]
        vneg = [r for r in d["rows"] if r["Vx"] < 0]
        aft = [r for r in neg if r["xc"] >= 0.05 and r["side"] != "estremita"]
        side = max(set(sides), key=sides.count)
        print(f"| {a} | {xst[len(xst) // 2]:.4f} ({side}) | {len(le)} | {between} | "
              f"{sum(r['Vx'] < 0 for r in neg)}/{len(neg)} | {sum(r['cf'] < 0 for r in vneg)}/{len(vneg)} | {len(aft)} |")
        if aft:
            ex = sorted(aft, key=lambda r: r["xc"])
            print("    celle cf<0 a valle del 5%: lato", {s: sum(r['side'] == s for r in aft) for s in ('dorso', 'ventre')},
                  " x/c min/max", round(ex[0]["xc"], 3), round(ex[-1]["xc"], 3),
                  " eta min/max", round(min(r['eta'] for r in aft), 3), round(max(r['eta'] for r in aft), 3),
                  " Vx<0:", sum(r['Vx'] < 0 for r in aft))

    print("\n### (c) celle con H al tetto per Transition_marker")
    print("| aoa | n | laminari (tr<0,01) | transizionali | turbolente (tr>0,99) | % area lam. dorso | x/c mediano lam. dorso |")
    print("|---|---|---|---|---|---|---|")
    for a, d in data.items():
        cap = [r for r in d["rows"] if abs(r["H"] - HCAP) < 1e-3]
        lam = [r for r in cap if r["tr"] < 0.01]
        tur = [r for r in cap if r["tr"] > 0.99]
        mid = [r for r in cap if 0.01 <= r["tr"] <= 0.99]
        A = sum(r["A"] for r in cap) or 1.0
        ld = sorted(r["xc"] for r in lam if r["side"] == "dorso")
        print(f"| {a} | {len(cap)} | {len(lam)} | {len(mid)} | {len(tur)} | "
              f"{pct(sum(r['A'] for r in lam if r['side'] == 'dorso'), A):.0f} | {ld[len(ld) // 2] if ld else float('nan'):.3f} |")
    print("\n    valori di Transition_marker (tutte le celle):")
    for a, d in data.items():
        trs = [r["tr"] for r in d["rows"]]
        print(f"    aoa {a}: =0 {sum(t == 0 for t in trs)}, (0,1) {sum(0 < t < 1 for t in trs)}, =1 {sum(t == 1 for t in trs)},"
              f" min {min(trs):.3g} max {max(trs):.3g}")

    print("\n### (d) Separation_marker")
    for a, d in data.items():
        sp = [r["sep"] for r in d["rows"]]
        print(f"    aoa {a}: max {max(sp):.3g}, min {min(sp):.3g}, celle != 0: {sum(s != 0 for s in sp)} su {len(sp)}")

    print("\n### extra: sovrapposizione cf<0 / H al tetto, H massimo esclusi i tetti")
    for a, d in data.items():
        neg = {r["i"] for r in d["rows"] if r["cf"] < 0}
        cap = {r["i"] for r in d["rows"] if abs(r["H"] - HCAP) < 1e-3}
        hs = sorted(r["H"] for r in d["rows"] if abs(r["H"] - HCAP) >= 1e-3)
        print(f"    aoa {a}: cf<0 {len(neg)}, tetto {len(cap)}, entrambi {len(neg & cap)}; H max sotto il tetto {hs[-1]:.4f}")


if __name__ == "__main__":
    main()
