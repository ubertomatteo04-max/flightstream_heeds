"""
postprocess.py - Lettura dei risultati di FlightStream, in blocchi indipendenti:

  1. coefficienti (CL, CD, CM) dalla tabella dei carichi, con il log come riserva;
  2. convergenza dal log;
  3. strato limite (H, cf) dal VTK: metriche generiche su tutte le facce esportate e, solo per
     la semiala, la striscia in apertura con dorso/ventre.

Ogni funzione solleva ValueError con un messaggio chiaro se il file non e' nel formato atteso:
il driver decide lo status. Valori mancanti = None (il driver li scrive come -999).

Formati NON ancora verificati su file reali di FlightStream 26.1 (vedi README):
tabella dei carichi (intestazione con CL/CDi e riga 'Total'), tabella delle iterazioni nel log
(6 colonne: Iter, ResVel, ResPres, CL, CDi, CM), nomi delle variabili nel VTK.
"""
import math
import re

_NUM = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[Ee][+-]?\d+)?"
COEFFS = ["Cx", "Cy", "Cz", "CL", "CDi", "CDo", "CMx", "CMy", "CMz"]


# --------------------------------------------------------------------------------------
# 1-2. Carichi, log, convergenza
# --------------------------------------------------------------------------------------
def _loads_header(lines):
    """Numeri dell'intestazione della tabella dei carichi (righe 'etichetta   valore').
    Restituisce 'reynolds' e, se FlightStream la scrive, 'density' (26.1 non la scrive)."""
    out = {}
    for ln in lines:
        m = re.match(r"^\s*([A-Za-z][^:]*?)\s*:?\s{2,}(" + _NUM + r")\.?\s*$", ln)
        if not m:
            continue
        label = m.group(1).lower()
        if "reynolds" in label:
            out["reynolds"] = float(m.group(2))
        elif "density" in label:
            out["density"] = float(m.group(2))
    return out


def parse_loads(path):
    """Tabella dei carichi: cerca l'intestazione con i nomi dei coefficienti e la riga 'Total'.
    In '_header' restituisce anche i numeri utili dell'intestazione (Reynolds, densita')."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    header = None
    for ln in lines:
        names = [t for t in re.split(r"[\s,;\t]+", ln.strip()) if t in COEFFS]
        if {"CL", "CDi"} <= set(names):
            header = names
        elif header and ln.strip().lower().startswith("total"):
            vals = [float(v) for v in re.findall(_NUM, ln)]
            if len(vals) >= len(header):
                out = dict(zip(header, vals[-len(header):]))
                out["_header"] = _loads_header(lines)
                return out
    raise ValueError(f"formato non riconosciuto in {path} (manca intestazione CL/CDi o riga 'Total')")


def parse_log(path):
    """Ultima riga della tabella delle iterazioni: Iter, ResVel, ResPres, CL, CDi, CM."""
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            parts = ln.split()
            if len(parts) == 6 and parts[0].isdigit():
                try:
                    rows.append([float("nan") if "*" in p else float(p) for p in parts])
                except ValueError:
                    pass
    if not rows:
        raise ValueError(f"nessuna tabella di iterazioni trovata in {path}")
    it, rv, rp, cl, cdi, cm = rows[-1]
    return {"iterations": int(it), "res_vel": rv, "res_pres": rp, "CL": cl, "CDi": cdi, "CMy": cm}


def coefficients(loads, logd):
    """Coefficienti finali: dalla tabella dei carichi se c'e', altrimenti dal log (che non ha CDo)."""
    if loads:
        src = loads
    else:
        src = {k: logd.get(k) for k in ("CL", "CDi", "CMy")}
    c = {k: src.get(k) for k in ("CL", "CDi", "CDo", "CMx", "CMy", "CMz")}
    c["CD"] = c["CDi"] + c["CDo"] if c["CDi"] is not None and c["CDo"] is not None else None
    c["L_over_D"] = c["CL"] / c["CD"] if c["CL"] is not None and c["CD"] else None
    return c


def convergence(logd, iter_max, threshold):
    """converged = 1 se i residui finali sono sotto la soglia, oppure se il solver si e' fermato
    prima del massimo di iterazioni con residui finiti (criterio da verificare su un log reale)."""
    if not logd:
        return {"converged": None, "iterations": None}
    res = (logd["res_vel"], logd["res_pres"])
    finite = all(math.isfinite(r) for r in res)
    below = finite and max(res) < threshold
    early = finite and logd["iterations"] < iter_max
    return {"converged": int(below or early), "iterations": logd["iterations"]}


def check_physics(res):
    """Controlli di sanita' sui coefficienti. Restituisce l'elenco dei problemi (vuoto = ok)."""
    bad = [f"{k} non finito" for k in ("CL", "CD", "CMy")
           if res.get(k) is not None and not math.isfinite(res[k])]
    if bad:
        return bad
    if res.get("CD") is not None and res["CD"] <= 0:
        bad.append(f"CD = {res['CD']:.6g} <= 0")
    if res.get("CDo") is not None and res["CDo"] < 0:
        bad.append(f"CDo = {res['CDo']:.6g} < 0")
    return bad


# --------------------------------------------------------------------------------------
# 3. VTK (ASCII POLYDATA) e strato limite
# --------------------------------------------------------------------------------------
def read_vtk(path):
    """Legge punti, poligoni e variabili di cella. Restituisce {'pts', 'polys', 'cell'}."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        tok = f.read().split()
    i, n = 0, len(tok)
    pts, polys, cell, ncell, section = [], [], {}, 0, None
    while i < n:
        t = tok[i]
        if t == "POINTS":
            npt = int(tok[i + 1]); i += 3
            vals = list(map(float, tok[i:i + 3 * npt])); i += 3 * npt
            pts = [vals[k:k + 3] for k in range(0, len(vals), 3)]
        elif t == "POLYGONS":
            npoly = int(tok[i + 1]); i += 3
            for _ in range(npoly):
                m = int(tok[i]); polys.append(list(map(int, tok[i + 1:i + 1 + m]))); i += 1 + m
        elif t == "CELL_DATA":
            section, ncell = "cell", int(tok[i + 1]); i += 2
        elif t == "POINT_DATA":
            section = "point"; i += 2
        elif t == "SCALARS":
            name = tok[i + 1]; i += 3
            if tok[i] != "LOOKUP_TABLE" and i + 1 < n and tok[i + 1] == "LOOKUP_TABLE":
                i += 1                                 # numero di componenti (opzionale nel formato VTK)
            if tok[i] == "LOOKUP_TABLE":
                i += 2
            cnt = ncell if section == "cell" else len(pts)
            vals = list(map(float, tok[i:i + cnt])); i += cnt
            if section == "cell":
                cell[name] = vals
        else:
            i += 1
    if not polys or not cell:
        raise ValueError(f"VTK non valido o senza variabili di cella: {path}")
    return {"pts": pts, "polys": polys, "cell": cell}


def _field(cell, *names):
    """Prima variabile presente tra i nomi indicati."""
    for nm in names:
        if nm in cell:
            return cell[nm]
    raise ValueError(f"variabile mancante nel VTK (cercate: {names}); presenti: {sorted(cell)}")


def _bl_fields(vtk):
    """Variabili di strato limite usate dalle metriche."""
    c = vtk["cell"]
    return {"H": _field(c, "BL_shape_factor"), "cf": _field(c, "skin_friction_coeff.", "skin_friction_coeff"),
            "tr": _field(c, "Transition_marker"), "sep": _field(c, "Separation_marker"),
            "area": _field(c, "Area")}


def generic_metrics(vtk):
    """Metriche valide per qualsiasi corpo, su tutte le facce esportate:
    frazione d'area con cf < 0, H massimo, massimo del Separation_marker."""
    f = _bl_fields(vtk)
    a_tot = sum(f["area"])
    if a_tot <= 0:
        raise ValueError("area totale nulla nel VTK")
    H = [h for h in f["H"] if math.isfinite(h)]
    if not H:
        raise ValueError("BL_shape_factor senza valori finiti")
    return {"area_frac_cf_neg": sum(a for a, c in zip(f["area"], f["cf"]) if c < 0) / a_tot,
            "H_max": max(H), "sep_max": max(f["sep"])}


def _centroids_and_nz(vtk):
    """Baricentro di ogni faccia e componente z della normale (formula di Newell)."""
    pts, cen, nz = vtk["pts"], [], []
    for p in vtk["polys"]:
        q = [pts[k] for k in p]
        m = len(q)
        cen.append([sum(v[j] for v in q) / m for j in range(3)])
        nz.append(sum((q[a][0] - q[(a + 1) % m][0]) * (q[a][1] + q[(a + 1) % m][1]) for a in range(m)))
    return cen, nz


def _split_upper_lower(strip, cen, nz):
    """Dorso/ventre dal segno della normale, separatamente per y >= 0 e y < 0 (le facce specchiate
    hanno l'ordine dei vertici invertito); il verso si fissa con la quota media (il dorso sta sopra)."""
    zmean = lambda ks: sum(cen[k][2] for k in ks) / max(1, len(ks))
    up, lo = [], []
    for half in (lambda y: y >= 0, lambda y: y < 0):
        ks = [k for k in strip if half(cen[k][1])]
        a = [k for k in ks if nz[k] > 0]
        b = [k for k in ks if nz[k] <= 0]
        if a and b and zmean(a) < zmean(b):
            a, b = b, a
        up += a
        lo += b
    if not up or not lo:
        raise ValueError("impossibile separare dorso e ventre nella striscia scelta")
    return up, lo


def _chord_profile(ks, cen, f, x_le, chord, bw):
    """Profilo in corda mediato sull'area in fasce larghe bw: (x/c, H, cf, transizione)."""
    bins = {}
    for k in ks:
        b = min(int((cen[k][0] - x_le) / chord / bw), int(1 / bw) - 1)
        acc = bins.setdefault(b, [0.0, 0.0, 0.0, 0.0])
        a = f["area"][k]
        acc[0] += a; acc[1] += a * f["H"][k]; acc[2] += a * f["cf"][k]; acc[3] += a * f["tr"][k]
    return [((b + 0.5) * bw, v[1] / v[0], v[2] / v[0], v[3] / v[0]) for b, v in sorted(bins.items()) if v[0] > 0]


def _side_metrics(ks, cen, f, x_le, chord, pp):
    """xtr, H al bordo d'uscita, H massimo e cf minimo per un lato (dorso o ventre)."""
    prof = _chord_profile(ks, cen, f, x_le, chord, pp["bin_width"])
    thr = pp["xtr_threshold"]
    xtr = 1.0                                          # 1.0 = transizione non raggiunta prima del TE
    for (xa, _, _, ta), (xb, _, _, tb) in zip(prof, prof[1:]):
        if ta < thr <= tb:
            xtr = xa + (thr - ta) * (xb - xa) / (tb - ta)
            break
    else:
        if prof and prof[0][3] >= thr:
            xtr = prof[0][0]
    body = [r for r in prof if pp["exclude_le"] <= r[0] <= pp["te_window"][1]]
    if not body:
        raise ValueError("profilo in corda vuoto tra exclude_le e te_window")
    te = [k for k in ks if pp["te_window"][0] <= (cen[k][0] - x_le) / chord <= pp["te_window"][1]]
    a_te = sum(f["area"][k] for k in te)
    h_te = sum(f["area"][k] * f["H"][k] for k in te) / a_te if a_te else None
    return {"xtr": xtr, "H_te": h_te, "H_max": max(r[1] for r in body),
            "cf_min": min(r[2] for r in body)}, prof


def wing_strip_metrics(vtk, pp):
    """Solo per la semiala (radice su y = 0): striscia tra pp['strip'] della semiapertura,
    metriche di dorso (_up) e ventre (_lo). Restituisce (metriche, profili)."""
    f = _bl_fields(vtk)
    cen, nz = _centroids_and_nz(vtk)
    b_half = max(abs(c[1]) for c in cen)
    lo_y, hi_y = pp["strip"][0] * b_half, pp["strip"][1] * b_half
    strip = [k for k, c in enumerate(cen) if lo_y <= abs(c[1]) <= hi_y]
    if not strip:
        raise ValueError("nessuna faccia nella striscia di apertura richiesta")
    xs = [vtk["pts"][v][0] for k in strip for v in vtk["polys"][k]]
    x_le, chord = min(xs), max(xs) - min(xs)
    if chord <= 0:
        raise ValueError("corda nulla nella striscia di apertura")
    up, lo = _split_upper_lower(strip, cen, nz)
    m_up, prof_up = _side_metrics(up, cen, f, x_le, chord, pp)
    m_lo, prof_lo = _side_metrics(lo, cen, f, x_le, chord, pp)
    out = {f"{k}_up": v for k, v in m_up.items()}
    out.update({f"{k}_lo": v for k, v in m_lo.items()})
    return out, {"up": prof_up, "lo": prof_lo}


def write_profiles(path, prof):
    """Profili in corda di dorso e ventre in CSV (solo diagnostica, HEEDS non li legge)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("side,x_c,H,cf,transition\n")
        for side in ("up", "lo"):
            for x, h, c, t in prof[side]:
                f.write(f"{side},{x:.4f},{h:.5f},{c:.6f},{t:.4f}\n")
