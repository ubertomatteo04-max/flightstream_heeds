#!/usr/bin/env python3
"""
estrai_vespa_root.py - Profilo di radice della semiala per la modalita' ccs_planform (Parte 7A).

Legge la PRIMA CrossSection (radice, y = 0) del CCS di ccs_wing e scrive vespa_root.dat in formato Selig:
riga del nome, poi x/c z/c dal TE del dorso al LE e al TE del ventre (stesso ordine del CCS), TE tozzo mantenuto.
Normalizzazione: corda = estensione in x della sezione (come geometry.wing_reference), LE = punto con x minima,
portato in (0, 0); nessuna rotazione (la corda geometrica e' inclinata di +0,037 gradi rispetto a x, trascurabile e
comunque identica alla baseline). Stampa la posizione del LE della radice nel CCS (per geometry.root_le_m).

Nota: reference/xfoil/vespa.dat usa invece il LE alla XFOIL (punto piu' lontano dal TE medio): differenza < 1e-5 c.

Uso:  python profiles\\estrai_vespa_root.py [--ccs ..\\..\\semiala_ccs_U120_V64_blended.csv]
"""
import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CCS = os.path.abspath(os.path.join(HERE, "..", "..", "semiala_ccs_U120_V64_blended.csv"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ccs", default=CCS)
    a = ap.parse_args()
    with open(a.ccs, encoding="utf-8-sig") as f:
        line = next(ln for ln in f if ln.strip().lower().startswith("crosssection"))
    v = [float(t) for t in line.strip().split(";")[1:] if t.strip()]
    pts = [v[i:i + 3] for i in range(0, len(v), 3)]
    xs = [p[0] for p in pts]
    i_le = xs.index(min(xs))
    x_le, y_le, z_le = pts[i_le]
    c = max(xs) - min(xs)
    with open(os.path.join(HERE, "vespa_root.dat"), "w", encoding="ascii", newline="\n") as f:
        f.write("VESPA root (CCS semiala_ccs_U120_V64_blended, sezione y=0; corda = estensione in x)\n")
        for x, _, z in pts:
            f.write(f"{(x - x_le) / c:.10f} {(z - z_le) / c:.10f}\n")
    te_t = (pts[0][2] - pts[-1][2]) / c
    print(f"{len(pts)} punti, LE indice {i_le}; corda {c:.9f} m; LE della radice (x, y, z) = "
          f"({x_le:.9g}, {y_le:.9g}, {z_le:.9g}) m; spessore al TE {100 * te_t:.3f} % c")


if __name__ == "__main__":
    main()
