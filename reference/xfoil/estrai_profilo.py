#!/usr/bin/env python3
"""
estrai_profilo.py - Punto 4 bis, Parte 2.1: profilo della semiala per XFOIL (SOLO RIFERIMENTO).

1. Legge la prima CrossSection del CCS di ccs_wing (..\\..\\..\\semiala_ccs_U120_V64_blended.csv; la semiala
   e' rettangolare e non svergolata, le due sezioni sono uguali a parte y).
2. Normalizza a c = 1 SENZA ruotare (x/c, z/c dal LE, corda lungo x): l'alfa di XFOIL resta l'alfa
   geometrico di FlightStream. LE = punto della spline piu' lontano dal punto medio del TE (come XFOIL).
3. Scrive vespa.dat (TE dorso -> LE -> TE ventre) mantenendo il TE tozzo.
4. Spessore e curvatura massimi (verticali, linea media rispetto alla corda LE - TE medio).
5. Controllo incrociato con la sezione a eta ~ 0,5 del surface.vtk del run fixed (D, aoa 4).
Scrive profilo.md con i numeri. Interprete: Python di HEEDS (numpy, scipy).
"""
import os
import sys

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize_scalar

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CCS = os.path.abspath(os.path.join(REPO, "..", "semiala_ccs_U120_V64_blended.csv"))
VTK = os.path.join(REPO, "mock_runs_visc_D", "Design_003", "surface.vtk")
sys.path.insert(0, REPO)
import postprocess as pp  # noqa: E402


def read_ccs_section(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("CrossSection;"):
                v = [float(t) for t in line.strip().split(";")[1:] if t]
                p = np.array(v).reshape(-1, 3)
                return p[:, 0], p[:, 1], p[:, 2]
    raise ValueError("nessuna CrossSection nel CCS")


def arc_spline(x, z):
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(z)))])
    return s, CubicSpline(s, x), CubicSpline(s, z)


def surface_interp(x, z, i_le):
    """Interpolatori z(x) di dorso e ventre (ordinati per x crescente)."""
    xu, zu = x[:i_le + 1][::-1], z[:i_le + 1][::-1]
    xl, zl = x[i_le:], z[i_le:]
    return (lambda q: np.interp(q, xu, zu)), (lambda q: np.interp(q, xl, zl))


def main():
    X, Y, Z = read_ccs_section(CCS)
    n = len(X)
    x_te_mid, z_te_mid = 0.5 * (X[0] + X[-1]), 0.5 * (Z[0] + Z[-1])
    s, sx, sz = arc_spline(X, Z)
    i0 = int(np.argmin(X))
    lo, hi = s[max(i0 - 3, 0)], s[min(i0 + 3, n - 1)]
    res = minimize_scalar(lambda t: -np.hypot(sx(t) - x_te_mid, sz(t) - z_te_mid), bounds=(lo, hi),
                          method="bounded", options={"xatol": 1e-12})
    x_le, z_le = float(sx(res.x)), float(sz(res.x))
    chord = x_te_mid - x_le
    tilt = np.degrees(np.arctan2(z_te_mid - z_le, x_te_mid - x_le))
    xn, zn = (X - x_le) / chord, (Z - z_le) / chord
    t_te = (Z[0] - Z[-1]) / chord

    with open(os.path.join(HERE, "vespa.dat"), "w", encoding="ascii") as f:
        f.write("VESPA\n")
        for a, b in zip(xn, zn):
            f.write(f"{a:12.8f} {b:12.8f}\n")

    # spessore e curvatura (verticali), su x/c fitto
    i_le = int(np.argmin(xn))
    up, lw = surface_interp(xn, zn, i_le)
    q = np.linspace(max(xn[i_le], 0.0) + 1e-4, 1.0, 20001)
    zu, zl = up(q), lw(q)
    chord_line = q * (z_te_mid - z_le) / chord / 1.0
    th = zu - zl
    cam = 0.5 * (zu + zl) - chord_line
    k_t, k_c = int(np.argmax(th)), int(np.argmax(cam))

    # controllo incrociato con la sezione del VTK fixed a eta ~ 0,5
    v = pp.read_vtk(VTK)
    P = np.array(v["pts"])
    ys = np.unique(np.round(P[:, 1], 6))
    ys = ys[ys >= 0]
    b2 = ys.max()
    y_s = ys[np.argmin(np.abs(ys - 0.5 * b2))]
    S = P[np.abs(P[:, 1] - y_s) < 1e-6]
    vx, vz = (S[:, 0] - x_le) / chord, (S[:, 2] - z_le) / chord
    # distanza normale (minima) dalla spline del CCS, positiva fuori dal profilo
    tt = np.linspace(0.0, s[-1], 200001)
    cx, cz = (sx(tt) - x_le) / chord, (sz(tt) - z_le) / chord
    dev = np.empty(len(vx))
    for j in range(len(vx)):
        d2 = (cx - vx[j]) ** 2 + (cz - vz[j]) ** 2
        k = int(np.argmin(d2))
        nx, nz = sz(tt[k], 1), -sx(tt[k], 1)          # normale esterna (percorso orario: dorso -> LE -> ventre)
        sg = np.sign((vx[j] - cx[k]) * nx + (vz[j] - cz[k]) * nz) or 1.0
        dev[j] = sg * np.sqrt(d2[k])
    is_up = vz >= 0.5 * (up(vx) + lw(vx))
    inner = vx < 0.95
    k_all = int(np.argmax(np.abs(dev)))
    k_in = int(np.argmax(np.abs(np.where(inner, dev, 0.0))))
    k_80 = int(np.argmax(np.abs(np.where(vx < 0.8, dev, 0.0))))
    x_blend = float(min(vx[(np.abs(dev) > 2e-4) & (vx > 0.5)], default=1.0))
    vte = S[np.argmax(S[:, 0])]

    lines = [
        "# Profilo della semiala per XFOIL (vespa.dat)", "",
        f"Fonte: `{os.path.relpath(CCS, REPO)}`, prima CrossSection (y = {Y[0]:g} m; quella a y = 2,64 m e' uguale).",
        f"Punti: {n} (TE dorso -> LE -> TE ventre), {i_le} sul dorso prima del LE.",
        "",
        "| grandezza | valore |", "|---|---|",
        f"| LE (x, z) [m] | {x_le:.6f}, {z_le:.6f} |",
        f"| TE medio (x, z) [m] | {x_te_mid:.6f}, {z_te_mid:.6f} |",
        f"| corda c [m] | {chord:.6f} (Lref dei JSON 0,345091) |",
        f"| inclinazione corda rispetto a x | {tilt:+.4f} deg (non ruotata: alfa XFOIL = alfa geometrico FS) |",
        f"| spessore al TE (tozzo) | {100 * t_te:.3f} % c ({1000 * (Z[0] - Z[-1]):.3f} mm) |",
        f"| spessore massimo | {100 * th[k_t]:.3f} % c a x/c = {q[k_t]:.3f} |",
        f"| curvatura massima | {100 * cam[k_c]:.3f} % c a x/c = {q[k_c]:.3f} |",
        "",
        f"## Controllo con il VTK fixed (`{os.path.relpath(VTK, REPO)}`)", "",
        f"Stazione di punti a y = {y_s:.4f} m (eta = {y_s / b2:.3f}), {len(S)} punti.",
        f"- scarto massimo (distanza normale / c) su tutta la sezione: {dev[k_all]:+.5f} a x/c = {vx[k_all]:.4f} "
        f"({'dorso' if is_up[k_all] else 'ventre'})",
        f"- scarto massimo (distanza normale / c) per x/c < 0,95: {dev[k_in]:+.6f} a x/c = {vx[k_in]:.4f} "
        f"({'dorso' if is_up[k_in] else 'ventre'})",
        f"- scarto massimo (distanza normale / c) per x/c < 0,8: {dev[k_80]:+.6f} a x/c = {vx[k_80]:.4f} "
        f"({'dorso' if is_up[k_80] else 'ventre'}); lo scarto supera 2e-4 da x/c = {x_blend:.3f} (raccordo del TE)",
        f"- TE della mesh FlightStream: x/c = {(vte[0] - x_le) / chord:.4f}, z/c = {(vte[2] - z_le) / chord:.5f} "
        f"(TE medio CCS z/c = {(z_te_mid - z_le) / chord:.5f}): la mesh chiude il TE (`Blend_trailing_edges` nel CCS), "
        "XFOIL usa invece il TE tozzo.",
    ]
    with open(os.path.join(HERE, "profilo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
