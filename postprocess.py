"""
postprocess.py - Lettura dei risultati di FlightStream, in blocchi indipendenti:

  1. coefficienti (CL, CD, CM) dalla tabella dei carichi, con il log come riserva;
  2. convergenza dal log;
  3. strato limite (H, cf) dal VTK: metriche generiche su tutte le facce esportate e, solo per
     la semiala, la striscia in apertura con dorso/ventre;
  4. metriche di separazione di un'ala (dorso/ventre, x/c, strisce in apertura), solo se il JSON
     ha il blocco "wing_frame" (classificazione portata da diagnostica/diag_bl.py).

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
    """Tabelle delle iterazioni (Iter, ResVel, ResPres, CL, CDi, CM). Restituisce i valori dell'ultima
    riga e, in 'phases', l'ultima riga di ogni tabella: una tabella in modalita' disaccoppiata, due in
    modalita' accoppiata (run inviscido, poi run con lo strato limite accoppiato; la numerazione delle
    iterazioni continua nella seconda tabella, verificato su FlightStream 26.1).
    FlightStream ristampa l'intestazione ogni 100 iterazioni (riga di trattini, 'Iteration', trattini):
    quella NON e' una fase nuova. Una fase nuova si riconosce dalle due righe di trattini prima
    dell'intestazione (chiusura della tabella precedente + apertura della nuova)."""
    tables = [[]]
    dashes = 0                      # righe di trattini dall'ultima riga di dati
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            s = ln.strip().strip("\x00")
            if s.startswith("-----"):
                dashes += 1
                continue
            if s.startswith("Iteration"):
                if tables[-1] and dashes >= 2:
                    tables.append([])
                continue
            parts = ln.split()
            if len(parts) == 6 and parts[0].isdigit():
                try:
                    tables[-1].append([float("nan") if "*" in p else float(p) for p in parts])
                    dashes = 0
                except ValueError:
                    pass
    tables = [t for t in tables if t]
    if not tables:
        raise ValueError(f"nessuna tabella di iterazioni trovata in {path}")
    it, rv, rp, cl, cdi, cm = tables[-1][-1]
    phases = [{"iterations": int(t[-1][0]), "res_vel": t[-1][1], "res_pres": t[-1][2]} for t in tables]
    return {"iterations": int(it), "res_vel": rv, "res_pres": rp, "CL": cl, "CDi": cdi, "CMy": cm,
            "phases": phases}


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


def viscous_convergence(logd, coupled, threshold):
    """Fase viscosa (solo in modalita' accoppiata): iterazioni della fase inviscida e di quella accoppiata
    e convergenza di entrambe (residui finali finiti e sotto la soglia). In modalita' disaccoppiata
    iterations_viscous = 0 e converged_viscous = None (-999 in results.txt)."""
    if not logd:
        return {"iterations_inviscid": None, "iterations_viscous": None, "converged_viscous": None}
    ph = logd["phases"]
    out = {"iterations_inviscid": ph[0]["iterations"], "iterations_viscous": 0, "converged_viscous": None}
    if not coupled:
        return out
    if len(ph) < 2:
        out["converged_viscous"] = 0                    # nessuna fase accoppiata nel log
        return out

    def ok(p):
        r = (p["res_vel"], p["res_pres"])
        return all(math.isfinite(x) for x in r) and max(r) < threshold
    out["iterations_viscous"] = ph[-1]["iterations"] - ph[0]["iterations"]
    out["converged_viscous"] = int(ok(ph[0]) and ok(ph[-1]))
    return out


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


# --------------------------------------------------------------------------------------
# 4. Metriche di separazione di un'ala (blocco "wing_frame" del JSON)
# --------------------------------------------------------------------------------------
WING_KEYS = ["sep_frac_up_le", "x_sep_up", "H_max_attached_up", "x_H_max_attached_up", "sep_frac_lo_te",
             "sep_marker_frac_up"]
SEP_MARKER_ON = 0.5       # Separation_marker: 0 attaccato, 1 "fully separated turbulent flows" (manuale p. 245)
_AXES = {"x": 0, "y": 1, "z": 2}
_FRAME_KEYS = {"chord_axis", "span_axis", "up_axis", "span_root_m", "n_strips"}
TIP_NORMAL = 0.7          # |componente in apertura della normale| oltre cui una faccia e' d'estremita'


def _axis(text, key):
    """'+x', 'x', '-y' ... -> (indice della coordinata, segno)."""
    t = str(text).strip().lower()
    ax = t.lstrip("+-")
    if ax not in _AXES or len(t) - len(ax) > 1:
        raise ValueError(f"wing_frame.{key} = {text!r} non valido: usa x, y o z con segno opzionale (es. '+x', '-y')")
    return _AXES[ax], -1.0 if t.startswith("-") else 1.0


def parse_wing_frame(wf):
    """Blocco wing_frame del JSON -> assi e parametri. Forma minima:
        {"chord_axis": "+x", "span_axis": "+y", "up_axis": "+z"}
    chord_axis: verso dal bordo d'attacco al bordo d'uscita; span_axis: dalla radice all'estremita';
    up_axis: dal ventre al dorso. Opzionali: span_root_m (coordinata della radice lungo span_axis,
    default 0: si usano solo le facce con coordinata >= radice, cioe' una semiala; le facce
    specchiate della simmetria Mirror sono escluse) e n_strips (strisce in apertura, default 60)."""
    bad = sorted(set(wf) - _FRAME_KEYS)
    if bad:
        raise ValueError(f"chiavi non riconosciute in wing_frame: {bad} (ammesse: {sorted(_FRAME_KEYS)})")
    out = {k: _axis(wf.get(k, ""), k) for k in ("chord_axis", "span_axis", "up_axis")}
    if len({v[0] for v in out.values()}) != 3:
        raise ValueError("wing_frame: chord_axis, span_axis e up_axis devono essere tre assi diversi")
    out["span_root_m"] = float(wf.get("span_root_m", 0.0))
    out["n_strips"] = int(wf.get("n_strips", 60))
    if out["n_strips"] < 1:
        raise ValueError("wing_frame.n_strips deve essere >= 1")
    return out


def _newell(q):
    """Normale unitaria di un poligono (formula di Newell)."""
    n = [0.0, 0.0, 0.0]
    for a in range(len(q)):
        p0, p1 = q[a], q[(a + 1) % len(q)]
        n[0] += (p0[1] - p1[1]) * (p0[2] + p1[2])
        n[1] += (p0[2] - p1[2]) * (p0[0] + p1[0])
        n[2] += (p0[0] - p1[0]) * (p0[1] + p1[1])
    s = math.sqrt(sum(v * v for v in n)) or 1.0
    return [v / s for v in n]


def wing_cells(vtk, frame):
    """Classifica le facce della semiala (coordinata in apertura >= radice), come in
    diagnostica/diag_bl.py: lato 'up'/'lo' dal segno della normale lungo up_axis (verso della
    normale fissato dalla quota media: il dorso sta sopra), 'tip' se la normale e' quasi parallela
    all'apertura; x/c rispetto alla corda locale della striscia (estensione dei vertici lungo
    chord_axis); eta = posizione in apertura tra radice (0) ed estremita' (1)."""
    pts, polys = vtk["pts"], vtk["polys"]
    (ic, sc), (isp, ss), (iu, su) = frame["chord_axis"], frame["span_axis"], frame["up_axis"]
    root, nstrip = frame["span_root_m"], frame["n_strips"]
    cen = [[sum(pts[k][j] for k in p) / len(p) for j in range(3)] for p in polys]
    half = [i for i in range(len(polys)) if ss * cen[i][isp] >= root]
    if not half:
        raise ValueError("wing_frame: nessuna faccia con coordinata in apertura >= span_root_m")
    nrm = {i: _newell([pts[k] for k in polys[i]]) for i in half}
    pos = [i for i in half if su * nrm[i][iu] > 0]
    neg = [i for i in half if su * nrm[i][iu] < 0]
    if not pos or not neg:
        raise ValueError("wing_frame: impossibile distinguere dorso e ventre")
    zmean = lambda ks: sum(su * cen[i][iu] for i in ks) / len(ks)
    orient = 1.0 if zmean(pos) > zmean(neg) else -1.0
    span = {i: ss * cen[i][isp] - root for i in half}
    b = max(span.values())
    if b <= 0:
        raise ValueError("wing_frame: apertura nulla")
    strip = {i: min(int(span[i] / b * nstrip), nstrip - 1) for i in half}
    ext = {}
    for i in half:
        for k in polys[i]:
            c = sc * pts[k][ic]
            lo, hi = ext.get(strip[i], (math.inf, -math.inf))
            ext[strip[i]] = (min(lo, c), max(hi, c))
    cells = []
    for i in half:
        n_up, n_span = orient * su * nrm[i][iu], orient * ss * nrm[i][isp]
        side = "tip" if abs(n_span) > TIP_NORMAL else ("up" if n_up > 0 else "lo")
        c_le, c_te = ext[strip[i]]
        xc = (sc * cen[i][ic] - c_le) / (c_te - c_le) if c_te > c_le else math.nan
        cells.append({"i": i, "side": side, "xc": xc, "eta": span[i] / b, "strip": strip[i]})
    return cells


def wing_frame_metrics(vtk, frame, pp):
    """Metriche di separazione della semiala. Cella separata: cf < -pp['sep_cf'].
      sep_frac_up_le      area separata sul dorso a x/c < le_xc / area del dorso
      x_sep_up            minimo sulle strisce (centro in eta tra x_sep_eta) del primo x/c separato
                          sul dorso dal bordo d'attacco; 1.0 = nessuna separazione sul dorso
      H_max_attached_up   H massimo sul dorso dove cf > sep_cf e x/c <= h_attached_xc_max
      x_H_max_attached_up x/c di quella faccia
      sep_frac_lo_te      area separata sul ventre a x/c > lo_te_xc / area del ventre (diagnostica)
    Le facce d'estremita' non appartengono ne' al dorso ne' al ventre."""
    f = _bl_fields(vtk)
    thr = pp["sep_cf"]
    cells = wing_cells(vtk, frame)
    up = [c for c in cells if c["side"] == "up"]
    lo = [c for c in cells if c["side"] == "lo"]
    area = lambda cs: sum(f["area"][c["i"]] for c in cs)
    sep = lambda c: f["cf"][c["i"]] < -thr
    a_up, a_lo = area(up), area(lo)
    if a_up <= 0 or a_lo <= 0:
        raise ValueError("wing_frame: area del dorso o del ventre nulla")
    out = {"sep_frac_up_le": area([c for c in up if sep(c) and c["xc"] < pp["le_xc"]]) / a_up,
           "sep_frac_lo_te": area([c for c in lo if sep(c) and c["xc"] > pp["lo_te_xc"]]) / a_lo,
           # Separation_marker di FlightStream (diverso da 0 solo con un modello di separazione)
           "sep_marker_frac_up": area([c for c in up if f["sep"][c["i"]] >= SEP_MARKER_ON]) / a_up}
    e0, e1 = pp["x_sep_eta"]
    n = frame["n_strips"]
    first = [c["xc"] for c in up if sep(c) and e0 <= (c["strip"] + 0.5) / n <= e1]
    out["x_sep_up"] = min(first) if first else 1.0
    att = [c for c in up if f["cf"][c["i"]] > thr and c["xc"] <= pp["h_attached_xc_max"]
           and math.isfinite(f["H"][c["i"]])]
    if att:
        best = max(att, key=lambda c: f["H"][c["i"]])
        out["H_max_attached_up"], out["x_H_max_attached_up"] = f["H"][best["i"]], best["xc"]
    else:
        out["H_max_attached_up"] = out["x_H_max_attached_up"] = None
    return out


# --------------------------------------------------------------------------------------
# 5. Carico lungo l'apertura (v2.6.0): carichi di sezione di FlightStream
# --------------------------------------------------------------------------------------
SPANLOAD_KEYS = ["cl_sec_max", "eta_cl_sec_max", "cl_sec_root", "cl_sec_eta05"]
_SEC_COLS = ["offset", "chord", "x_qc", "z_qc", "CFx", "CFz", "CM"]


def spanload_stations(n):
    """Posizioni in apertura eta (0-1) delle sezioni: punti medi di n intervalli uguali in t,
    eta = sin(pi/2 t), cioe' addensate verso l'estremita' dove il carico cade rapidamente."""
    return [math.sin(0.5 * math.pi * (k - 0.5) / n) for k in range(1, n + 1)]


def parse_sectional_loads(path):
    """File di EXPORT_SURFACE_SECTIONAL_LOADS (FlightStream 26.1, verificato il 2026-10-05):
    intestazione, riga 'Offset, Chord, X_QC, Z_QC, CFx, CFz, CM', poi una riga per sezione con 7
    numeri separati da virgole (coefficienti 2D sulla corda locale e sulla q del flusso libero)."""
    rows, started = [], False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            s = ln.strip()
            if s.lower().startswith("offset, chord"):
                started = True
                continue
            if not started:
                continue
            t = [x for x in s.split(",") if x.strip()]
            if len(t) != len(_SEC_COLS):
                continue
            try:
                rows.append(dict(zip(_SEC_COLS, (float(x) for x in t))))
            except ValueError:
                continue
    if not rows:
        raise ValueError(f"nessuna sezione leggibile in {path}")
    return rows


def spanload_metrics(rows, aoa_deg, span, sref, factor):
    """cl(eta) dalle sezioni: cl = CFz cos(a) - CFx sin(a) (sezioni nel frame di riferimento, assi
    del corpo). span = {'root': coordinata della radice lungo l'asse in apertura (con il segno di
    wing_frame.span_axis), 'b_half': semiapertura, 'sign': +1/-1 (verso dell'asse rispetto a y)}.
    Restituisce (metriche SPANLOAD_KEYS, tabella per eta crescente, CL integrato).
    CL integrato = factor / Sref * integrale di cl c dy (trapezi; tra radice e prima sezione cl c
    costante, all'estremita' cl c = 0); factor = 2 con i carichi riportati all'ala intera (Mirror)."""
    a = math.radians(aoa_deg)
    tab = []
    for r in rows:
        eta = (span["sign"] * r["offset"] - span["root"]) / span["b_half"]
        tab.append({"eta": eta, "y_m": r["offset"], "chord_m": r["chord"],
                    "cl": r["CFz"] * math.cos(a) - r["CFx"] * math.sin(a), "CFx": r["CFx"], "CFz": r["CFz"],
                    "cm_qc": r["CM"]})
    tab.sort(key=lambda t: t["eta"])
    best = max(tab, key=lambda t: t["cl"])
    out = {"cl_sec_max": best["cl"], "eta_cl_sec_max": best["eta"], "cl_sec_root": tab[0]["cl"],
           "cl_sec_eta05": None}
    for t0, t1 in zip(tab, tab[1:]):
        if t0["eta"] <= 0.5 <= t1["eta"]:
            w = (0.5 - t0["eta"]) / (t1["eta"] - t0["eta"]) if t1["eta"] > t0["eta"] else 0.0
            out["cl_sec_eta05"] = t0["cl"] + w * (t1["cl"] - t0["cl"])
    ys = [0.0] + [t["eta"] * span["b_half"] for t in tab] + [span["b_half"]]
    fs = [tab[0]["cl"] * tab[0]["chord_m"]] + [t["cl"] * t["chord_m"] for t in tab] + [0.0]
    integral = sum(0.5 * (fs[i] + fs[i + 1]) * (ys[i + 1] - ys[i]) for i in range(len(ys) - 1))
    return out, tab, factor * integral / sref


def write_spanload(path, tab):
    """spanload.csv: una riga per sezione (eta crescente); Lp_N_m = L'(y) dai carichi in NEWTONS, se c'e'."""
    keys = ["eta", "y_m", "chord_m", "cl", "CFx", "CFz", "cm_qc"]
    if tab and all("Lp_N_m" in t for t in tab):
        keys.append("Lp_N_m")
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for t in tab:
            f.write(",".join(f"{t[k]:.6g}" for k in keys) + "\n")


# --------------------------------------------------------------------------------------
# 6. Carichi dimensionali, sezione critica (v2.7.0, Parte 7B)
# --------------------------------------------------------------------------------------
def spanload_newtons(rows, aoa_deg, span):
    """Carichi di sezione in NEWTONS (FlightStream: forze 2D per unita' di lunghezza, N/m; manuale p. 250):
    L'(y) = CFz cos(a) - CFx sin(a). Restituisce ({y: L'}, integrale di L' dy sulla semiala, M_root = integrale
    di L' y dy). Trapezi con L' costante tra radice e prima sezione e L' = 0 all'estremita' (come spanload_metrics)."""
    a = math.radians(aoa_deg)
    pts = sorted(((span["sign"] * r["offset"] - span["root"]),
                  r["CFz"] * math.cos(a) - r["CFx"] * math.sin(a)) for r in rows)
    ys = [0.0] + [p[0] for p in pts] + [span["b_half"]]
    lp = [pts[0][1]] + [p[1] for p in pts] + [0.0]
    lift = sum(0.5 * (lp[i] + lp[i + 1]) * (ys[i + 1] - ys[i]) for i in range(len(ys) - 1))
    mom = sum(0.5 * (lp[i] * ys[i] + lp[i + 1] * ys[i + 1]) * (ys[i + 1] - ys[i]) for i in range(len(ys) - 1))
    return {round(y, 9): v for y, v in pts}, lift, mom


def read_clmax_table(path):
    """File clmax_vs_Re.csv: righe 'Re,clmax' (le righe che iniziano con # sono commenti). Restituisce la
    funzione clmax(Re), lineare a tratti, costante fuori dall'intervallo."""
    pts = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#") or s.lower().startswith("re"):
                continue
            re_, cl = (float(t) for t in s.split(",")[:2])
            pts.append((re_, cl))
    if not pts:
        raise ValueError(f"nessuna riga Re,clmax in {path}")
    pts.sort()

    def clmax(re_):
        if re_ <= pts[0][0]:
            return pts[0][1]
        for (r0, c0), (r1, c1) in zip(pts, pts[1:]):
            if re_ <= r1:
                return c0 + (c1 - c0) * (re_ - r0) / (r1 - r0)
        return pts[-1][1]
    return clmax


def critical_section(tab1, tab2, CL1, CL2, clmax_of_chord):
    """Sezione critica dai due run ad alfa1 e alfa2 (stesse sezioni): per ogni sezione
    C_L*(eta) = CL1 + (clmax(eta) - cl1(eta)) (CL2 - CL1) / (cl2(eta) - cl1(eta)), cioe' il CL dell'ala a cui quella
    sezione arriva a clmax con cl lineare in CL. CLmax_wing = minimo, eta_stall = sua posizione.
    clmax_of_chord(c) = clmax della sezione di corda c (il Re dipende dalla corda). Sezioni con cl2 <= cl1: escluse."""
    best = None
    for s1, s2 in zip(tab1, tab2):
        dcl = s2["cl"] - s1["cl"]
        if dcl <= 1e-9:
            continue
        cls = CL1 + (clmax_of_chord(s1["chord_m"]) - s1["cl"]) * (CL2 - CL1) / dcl
        if best is None or cls < best[0]:
            best = (cls, s1["eta"])
    if best is None:
        raise ValueError("sezione critica: nessuna sezione con cl crescente fra alfa1 e alfa2")
    return best
