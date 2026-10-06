"""
geometry.py - UNICO file da modificare quando cambia la geometria.

Il driver (fs_driver.py) chiama build_geometry(params, cfg, workdir) e si aspetta un dizionario:
    "lines"           comandi FlightStream che aprono/creano la geometria
    "init_lines"      comando INITIALIZE_SOLVER (lista vuota se si usa l'inizializzazione del .fsm)
    "explicit_physics" True se il driver deve scrivere il modello fisico dal JSON (strato limite,
                      accoppiamento viscoso, vorticity drag boundaries); False = quello del .fsm
    "Sref", "Lref"    grandezze di riferimento calcolate dalla geometria (None = si usano quelle del JSON)

"lines" e "init_lines" sono LISTE DI COMANDI: ogni comando e' una lista di righe (il nome del
comando e i suoi parametri), es. [["NEW_SIMULATION"], ["CCS_IMPORT", "CLEAR_EXISTING ENABLE", ...]].
Il driver scrive una riga vuota dopo ogni comando: nel manuale di FlightStream una riga vuota
chiude i parametri di un comando su piu' righe (un commento non basta).

Tutte le impostazioni di geometria stanno nel blocco "geometry" del JSON; "geometry.mode" sceglie
la modalita'. I percorsi relativi sono rispetto alla cartella del JSON.

Modalita' disponibili:
    "fixed"     apre un .fsm gia' pronto (ala, fusoliera, velivolo completo...): la mesh viene dal
                file. Con geometry.reinitialize = true (default) modello fisico e INITIALIZE_SOLVER
                (superfici, scia, simmetria) vengono dal JSON; con false restano quelli salvati
                nel .fsm. Nessuna variabile geometrica.
    "ccs_wing"  semiala da file CCS con la corda scalata da 'chord_scale', simmetria Mirror sul
                piano XZ, radice su y = 0. Un solo componente portante.
    "ccs_planform" (v2.7.0) semiala parametrica generata da un profilo (geometry.profile, formato Selig):
                c_root (oppure S_half con geometry.size_by = "S_half"), taper, twist_tip_deg (lineare in eta,
                positivo a cabrare, rotazione attorno a c/4), b_half; geometry.n_sections sezioni uguali in
                apertura, linea dei quarti di corda dritta e perpendicolare al flusso. Mirror come ccs_wing.

COME AGGIUNGERE UNA MODALITA'
 1. In GEOMETRY_VARIABLES aggiungi il nome della modalita' con la lista delle variabili che HEEDS
    potra' variare: diventano chiavi ammesse in params.txt (oltre a aoa, velocity, altitude, sideslip).
 2. In POSTPROC indica il post-processing: "generic" vale per qualsiasi corpo; "wing_strip" solo
    per una semiala con radice su y = 0 (striscia in apertura, dorso/ventre).
 3. In NEW_SIMULATION indica True se la modalita' crea la simulazione da zero (il driver scrive
    allora FLUID_PROPERTIES con i valori del blocco fluid del JSON, o dall'ISA con
    override_fluid) oppure False se il fluido viene da un .fsm.
 4. Scrivi una funzione _nome(params, cfg, workdir) che restituisce il dizionario descritto sopra
    e registrala in _MODES (in fondo al file).
 Esempi di partenza:
  - trasformare un .fsm: parti da open_lines(...) come in _fixed e aggiungi comandi come
    SURFACE_SCALE o SURFACE_ROTATE con i valori di params (sintassi dal manuale FlightStream,
    da verificare). Se la geometria cambia dopo l'OPEN serve una nuova inizializzazione:
    "init_lines" = initialize_solver_lines(cfg["solver"]) ed "explicit_physics" = True;
    NEW_SIMULATION resta False (il fluido e' nel .fsm).
  - importare da OpenVSP: genera il file geometria con OpenVSP nella cartella workdir
    (per esempio con subprocess) e restituisci le righe di import di FlightStream e
    l'inizializzazione, come fa _ccs_wing per il CCS.
"""
import math
import os

GEOMETRY_VARIABLES = {
    "fixed": [],
    "ccs_wing": ["chord_scale"],
    # unione delle variabili possibili (per lo schema di results.txt); quelle ammesse in un caso dipendono da
    # geometry.size_by (allowed_variables): c_root OPPURE S_half
    "ccs_planform": ["c_root", "taper", "twist_tip_deg", "b_half", "S_half"],
}

POSTPROC = {
    "fixed": "generic",
    "ccs_wing": "wing_strip",
    "ccs_planform": "wing_strip",
}

NEW_SIMULATION = {
    "fixed": False,
    "ccs_wing": True,
    "ccs_planform": True,
}

PLANFORM_SIZE_BY = ("c_root", "S_half")


def allowed_variables(cfg):
    """Variabili geometriche ammesse in params.txt / blocco case per il caso del JSON."""
    mode = cfg["geometry"]["mode"]
    if mode != "ccs_planform":
        return list(GEOMETRY_VARIABLES[mode])
    size = cfg["geometry"].get("size_by", "c_root")
    if size not in PLANFORM_SIZE_BY:
        raise ValueError(f"geometry.size_by = {size!r} non valido: 'c_root' oppure 'S_half'")
    return [size, "taper", "twist_tip_deg", "b_half"]

# Bordo d'uscita in ccs_wing (manuale 26.1 p. 84; prove in STATO.md, v2.6.0):
#   blended  default: raccordo del TE tozzo (0,652 % c) verso il punto medio, da x/c ~0,9; risultati validati
#   sharp    sezioni chiuse: FlightStream porta il vertice del ventre su quello del dorso -> NON fedele (CL -33 %)
#   blunt    TE tozzo fedele con base region (vedi _ccs_wing); CL -4 %, CMy -6 % rispetto a blended
TE_PARAMS = {                     # parole chiave del formato CCS (manuale 26.1), senza prefisso
    "blended": ["Open_Cross_Sections", "Blend_trailing_edges", "Mark_trailing_edges"],
    "sharp": ["Mark_trailing_edges"],
    "blunt": ["Open_Cross_Sections", "Blunt_trailing_edges"],
}


def _fmt(x):
    """Numero in forma compatta per lo script FlightStream."""
    return f"{x:.9g}"


def _onoff(flag):
    """True/False -> ENABLE/DISABLE."""
    return "ENABLE" if flag else "DISABLE"


def _path(cfg, p):
    """Percorso assoluto: i percorsi relativi sono rispetto alla cartella del JSON."""
    return p if os.path.isabs(p) else os.path.abspath(os.path.join(cfg["_dir"], p))


def build_geometry(params, cfg, workdir):
    """Punto d'ingresso chiamato dal driver: smista sulla modalita' scelta nel JSON."""
    mode = cfg["geometry"]["mode"]
    if mode not in _MODES:
        raise ValueError(f"geometry.mode '{mode}' sconosciuta. Disponibili: {sorted(_MODES)}")
    return _MODES[mode](params, cfg, workdir)


# --------------------------------------------------------------------------------------
# Modalita' "fixed": template .fsm gia' pronto
# --------------------------------------------------------------------------------------
def fixed_template(cfg):
    """Percorso assoluto del template .fsm (anche per gli script di prova del driver)."""
    return _path(cfg, cfg["geometry"].get("template_fsm", ""))


def open_lines(fsm_path, options):
    """Comando OPEN (lista con un solo comando): file e poi le opzioni (fixed_open_options).
    Manuale 26.1: OPEN vuole il file e LOAD_SOLVER_INITIALIZATION (RESET_PARALLEL_CORES non esiste)."""
    return [["OPEN", fsm_path] + list(options)]


def fixed_reinitialize(cfg):
    """geometry.reinitialize (default True): inizializzazione e modello fisico dal JSON, cosi' i
    risultati non dipendono dallo stato in cui e' stato salvato il .fsm (con l'inizializzazione
    salvata la semiala dava CL +2,8 % rispetto al riferimento). False = quelli del .fsm."""
    g = cfg["geometry"]
    if "open_options" in g:
        raise ValueError("geometry.open_options non e' piu' usata: OPEN dipende da geometry.reinitialize "
                         "(true = LOAD_SOLVER_INITIALIZATION DISABLE, false = ENABLE). Toglila dal JSON.")
    return bool(g.get("reinitialize", True))


def fixed_open_options(cfg):
    """Opzioni di OPEN: l'inizializzazione salvata nel .fsm si carica solo senza reinitialize."""
    return [f"LOAD_SOLVER_INITIALIZATION {_onoff(not fixed_reinitialize(cfg))}"]


def initialize_solver_lines(sol):
    """INITIALIZE_SOLVER dal blocco 'solver' del JSON (manuale 26.1, Solver Initialization):
    SURFACES -1 = tutte (nessuna riga per superficie), altrimenti una riga 'indice,ENABLE/DISABLE'
    per superficie con il flag del quad mesher."""
    surf, sym = sol.get("init_surfaces"), sol.get("symmetry")
    if surf is None or sym is None:
        raise ValueError("solver.init_surfaces e solver.symmetry sono obbligatorie quando la simulazione "
                         "viene inizializzata dallo script (es. [[1, true]] e \"MIRROR\").")
    if surf == -1:
        rows = ["SURFACES -1"]
    else:
        rows = [f"SURFACES {len(surf)}"] + [f"{int(i)},{_onoff(quad)}" for i, quad in surf]
    wake = sol["wake_termination_x"]
    wake = wake.upper() if isinstance(wake, str) else _fmt(float(wake))
    return [["INITIALIZE_SOLVER", f"SOLVER_MODEL {sol['model']}"] + rows +
            [f"WAKE_TERMINATION_X {wake}", f"SYMMETRY {str(sym).upper()}",
             f"WALL_COLLISION_AVOIDANCE {_onoff(sol['wall_collision_avoidance'])}"]]


def _fixed(params, cfg, workdir):
    """Apre il .fsm: nessun tappo da togliere, nessuna mesh da rifare. Con reinitialize il solver
    viene reinizializzato dal JSON, cosi' i risultati non dipendono dallo stato salvato nel .fsm."""
    fsm = fixed_template(cfg)
    if not os.path.isfile(fsm):
        raise ValueError(f"geometry.template_fsm non trovato: {fsm}")
    reinit = fixed_reinitialize(cfg)
    return {"lines": open_lines(fsm, fixed_open_options(cfg)),
            "init_lines": initialize_solver_lines(cfg["solver"]) if reinit else [],
            "explicit_physics": reinit, "Sref": None, "Lref": None}


# --------------------------------------------------------------------------------------
# Modalita' "ccs_wing": semiala da CCS con corda scalata
# --------------------------------------------------------------------------------------
def _ccs_wing(params, cfg, workdir):
    """Ricostruisce la semiala dal CCS scalato e prepara l'inizializzazione Mirror."""
    g, sol = cfg["geometry"], cfg["solver"]
    if abs(params.get("sideslip", 0.0)) > 1e-12:
        raise ValueError("ccs_wing usa la simmetria Mirror: sideslip deve essere 0.")
    if params["chord_scale"] <= 0:
        raise ValueError(f"chord_scale deve essere > 0 (ricevuto {params['chord_scale']}).")
    src = _path(cfg, g.get("base_ccs", ""))
    if not os.path.isfile(src):
        raise ValueError(f"geometry.base_ccs non trovato: {src}")
    dst = os.path.join(workdir, "case_ccs.csv")
    sections = prepare_ccs(src, dst, params["chord_scale"], mesh_lines(cfg), g["te_type"])
    ref = wing_reference(sections)
    tol = g["root_cap_tol_m"]
    if abs(ref["y_root"]) > tol:
        raise ValueError(f"La radice non e' su y=0 (y={ref['y_root']:.6f} m): Mirror non applicabile.")
    lines = ccs_import_lines(dst, ref["b_half"], tol)
    if g["te_type"].lower() == "blunt":
        # TE tozzo fedele (v2.6.0, opzione): Blunt_trailing_edges crea le facce di base in un boundary proprio
        # (manuale 26.1 p. 84); i bordi d'uscita (Kutta) si marcano sulla base region (p. 316). La base e' una
        # superficie in piu': INITIALIZE_SOLVER deve includere tutte le superfici. Rispetto a "blended" (default):
        # CL -4 %, CMy -6 % a 4-12 gradi (STATO.md, v2.6.0).
        if sol.get("init_surfaces") != -1:
            raise ValueError("geometry.te_type \"blunt\" richiede solver.init_surfaces = -1 (la base del bordo "
                             "d'uscita e' una superficie a parte)")
        lines += [["AUTO_DETECT_BASE_REGIONS"], ["SET_BASE_REGION_TRAILING_EDGES -1"]]
    if str(sol.get("symmetry")).upper() != "MIRROR":
        raise ValueError("ccs_wing costruisce solo la semiala: solver.symmetry deve essere \"MIRROR\".")
    factor = 2.0 if cfg["reference"]["symmetry_loads"] else 1.0
    return {"lines": lines, "init_lines": initialize_solver_lines(sol), "explicit_physics": True,
            "Sref": factor * ref["S_half"], "Lref": ref["MAC"],
            "span": {"y_root": ref["y_root"], "b_half": ref["b_half"], "c_tip": ref["chord_tip"]}}


def ccs_import_lines(dst, b_half, tol):
    """Simulazione nuova, import del CCS e rimozione del tappo di radice (radice aperta sul piano XZ)."""
    return [["NEW_SIMULATION"], ["SET_SIMULATION_LENGTH_UNITS METER"],
            ["CCS_IMPORT", "CLOSE_COMPONENT_ENDS ENABLE", "UPDATE_PROPERTIES DISABLE",
             "CLEAR_EXISTING ENABLE", f"FILE {dst}"],
            ["# tappo di radice: rimosso (radice aperta sul piano di simmetria XZ)",
             "SURFACE_SELECT_BY_THRESHOLD", "FRAME 1", "THRESHOLD Y",
             f"MIN_VALUE {_fmt(-(b_half + 1.0))}", f"MAX_VALUE {_fmt(tol)}",
             "RANGE BELOW_MAX", "SUBSET ALL_FACES"],
            ["DELETE_SELECTED_FACES"]]


# --------------------------------------------------------------------------------------
# Modalita' "ccs_planform": semiala parametrica (v2.7.0)
# --------------------------------------------------------------------------------------
def read_selig(path):
    """Profilo in formato Selig: riga del nome, poi 'x z' dal TE del dorso al LE e al TE del ventre."""
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = [ln.split() for ln in f.read().splitlines()[1:] if ln.strip()]
    pts = [(float(r[0]), float(r[1])) for r in rows]
    if len(pts) < 10:
        raise ValueError(f"profilo con meno di 10 punti: {path}")
    return pts


def planform_geometry(c_root, taper, twist_tip_deg, b_half, n_sections, le_root):
    """Grandezze in pianta: corda lineare in eta, linea dei quarti di corda dritta (x costante).
    S_half = b c_root (1 + taper) / 2;  MAC = 2/3 c_root (1 + t + t^2) / (1 + t);  c_tip = taper c_root."""
    if c_root <= 0 or taper <= 0 or b_half <= 0:
        raise ValueError(f"c_root, taper e b_half devono essere > 0 (ricevuti {c_root}, {taper}, {b_half})")
    if abs(twist_tip_deg) > 20:
        raise ValueError(f"twist_tip_deg = {twist_tip_deg}: oltre +/-20 gradi")
    if int(n_sections) != n_sections or n_sections < 2:
        raise ValueError(f"geometry.n_sections = {n_sections}: intero >= 2")
    t = taper
    return {"c_root": c_root, "c_tip": t * c_root, "S_half": b_half * c_root * (1 + t) / 2,
            "MAC": 2.0 / 3.0 * c_root * (1 + t + t * t) / (1 + t), "x_c4": le_root[0] + c_root / 4,
            "b_half": b_half}


def planform_sections(prof, geo, taper, twist_tip_deg, n_sections, le_root):
    """Sezioni del CCS: profilo scalato alla corda locale, LE sulla linea x_c4 - c/4, poi rotazione di
    twist(eta) attorno al punto a c/4 sulla quota del LE della radice (positivo a cabrare: LE su, TE giu').
    Stesso numero di punti in ogni sezione; sezioni equidistanti in apertura."""
    x0, y0, z0 = le_root
    xc4 = geo["x_c4"]
    out = []
    for k in range(int(n_sections)):
        eta = k / (n_sections - 1)
        c = geo["c_root"] * (1 + (taper - 1) * eta)
        th = math.radians(twist_tip_deg * eta)
        ct, st = math.cos(th), math.sin(th)
        sec = []
        for xh, zh in prof:
            dx, dz = (xc4 - c / 4 + c * xh) - xc4, c * zh
            sec.append([xc4 + dx * ct + dz * st, y0 + eta * geo["b_half"], z0 - dx * st + dz * ct])
        out.append(sec)
    return out


def write_planform_ccs(dst, sections, mesh, te_type, s_full, mac):
    """CCS con intestazione 26.1 (manuale p. 77: ReferenceArea, ReferenceLength, Units; riga vuota dopo
    l'intestazione). Sref/Lref effettivi vengono comunque da SOLVER_SET_REF_AREA/LENGTH dello script;
    come FlightStream usi ReferenceArea/ReferenceLength del CCS (ala intera o semiala): DA VERIFICARE."""
    if te_type.lower() not in TE_PARAMS:
        raise ValueError(f"geometry.te_type '{te_type}' non valido. Ammessi: {sorted(TE_PARAMS)}")
    out = ["Aircraft;Vespa_planform", f"ReferenceArea;{_fmt(s_full)}", f"ReferenceLength;{_fmt(mac)}",
           "Units;Meter", "", "Component;Semiala", "LiftingSurface;true"] + list(mesh)
    out += TE_PARAMS[te_type.lower()] + ["V_Loft_C0", "U_Loft_C2"]
    out += ["CrossSection;" + ";".join(_fmt(c) for p in sec for c in p) for sec in sections]
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def _ccs_planform(params, cfg, workdir):
    """Semiala parametrica: CCS generato dal profilo e dai parametri di pianta, poi come ccs_wing."""
    g, sol = cfg["geometry"], cfg["solver"]
    if abs(params.get("sideslip", 0.0)) > 1e-12:
        raise ValueError("ccs_planform usa la simmetria Mirror: sideslip deve essere 0.")
    if str(sol.get("symmetry")).upper() != "MIRROR":
        raise ValueError("ccs_planform costruisce solo la semiala: solver.symmetry deve essere \"MIRROR\".")
    prof_path = _path(cfg, g.get("profile", ""))
    if not os.path.isfile(prof_path):
        raise ValueError(f"geometry.profile non trovato: {prof_path}")
    le_root = g.get("root_le_m")
    if not isinstance(le_root, list) or len(le_root) != 3 or abs(float(le_root[1])) > 1e-12:
        raise ValueError("geometry.root_le_m = [x, 0, z] del LE della radice (m) e' obbligatoria (y = 0)")
    le_root = [float(v) for v in le_root]
    taper, twist, b_half = params["taper"], params["twist_tip_deg"], params["b_half"]
    if g.get("size_by", "c_root") == "S_half":
        if params["S_half"] <= 0 or taper <= 0 or b_half <= 0:
            raise ValueError("S_half, taper e b_half devono essere > 0")
        c_root = 2.0 * params["S_half"] / (b_half * (1.0 + taper))
    else:
        c_root = params["c_root"]
    n = g.get("n_sections", 7)
    geo = planform_geometry(c_root, taper, twist, b_half, n, le_root)
    sections = planform_sections(read_selig(prof_path), geo, taper, twist, n, le_root)
    dst = os.path.join(workdir, "case_ccs.csv")
    factor = 2.0 if cfg["reference"]["symmetry_loads"] else 1.0
    write_planform_ccs(dst, sections, mesh_lines(cfg), g.get("te_type", "blended"), factor * geo["S_half"], geo["MAC"])
    lines = ccs_import_lines(dst, b_half, g.get("root_cap_tol_m", 1e-4))
    if g.get("te_type", "blended").lower() == "blunt":
        if sol.get("init_surfaces") != -1:
            raise ValueError("geometry.te_type \"blunt\" richiede solver.init_surfaces = -1")
        lines += [["AUTO_DETECT_BASE_REGIONS"], ["SET_BASE_REGION_TRAILING_EDGES -1"]]
    return {"lines": lines, "init_lines": initialize_solver_lines(sol), "explicit_physics": True,
            "Sref": factor * geo["S_half"], "Lref": geo["MAC"],
            "span": {"y_root": 0.0, "b_half": b_half, "c_tip": geo["c_tip"]},
            "echo": {"c_root": c_root, "S_half": geo["S_half"], "taper": taper, "twist_tip_deg": twist,
                     "b_half": b_half}}


def _section_points(line):
    """Punti [x, y, z] di una riga 'CrossSection;x;y;z;...'."""
    vals = [float(t) for t in line.split(";")[1:] if t.strip() != ""]
    if len(vals) % 3:
        raise ValueError("Riga CrossSection con numero di coordinate non multiplo di 3.")
    return [vals[i:i + 3] for i in range(0, len(vals), 3)]


def _split_components(lines):
    """Divide il CCS in blocchi: intestazione e poi un blocco per ogni riga 'Component;'."""
    blocks = [[]]
    for ln in lines:
        if ln.strip().lower().startswith("component;"):
            blocks.append([])
        blocks[-1].append(ln)
    return blocks


def _is_lifting(block):
    """True se il blocco contiene 'LiftingSurface;true'."""
    return any(ln.strip().lower().startswith("liftingsurface;true") for ln in block)


MESH_KEYS = {"u_pts": int, "u_growth_type": int, "u_growth_rate": float, "u_periodicity": int,
             "v_pts": int, "v_growth_type": int, "v_growth_rate": float, "v_periodicity": int}


def mesh_lines(cfg):
    """Righe Mesh_U / Mesh_V del CCS dal blocco 'mesh' del JSON (manuale 26.1 p. 82):
    Mesh_U;u_pts;growth_type;growth_rate;periodicity (in corda), Mesh_V;... (in apertura).
    growth_type: 1 uniforme, 2 successiva, 3 successiva su due lati (addensa a LE e TE con
    periodicity 2), 4 successiva inversa. Default = mesh del CCS di partenza (120;3;1.1;2 e 64;1;1.0;1)."""
    if "mesh_u" in cfg["geometry"] or "mesh_v" in cfg["geometry"]:
        raise ValueError("geometry.mesh_u/mesh_v non sono piu' usate (v2.6.0): usa il blocco 'mesh' "
                         "(u_pts, u_growth_type, u_growth_rate, u_periodicity, v_pts, ...)")
    m = cfg["mesh"]
    for k, typ in MESH_KEYS.items():
        v = m.get(k)
        if v is None or (typ is int and (not float(v).is_integer())):
            raise ValueError(f"mesh.{k} = {v!r} non valido")
    if int(m["u_pts"]) < 2 or int(m["v_pts"]) < 2:
        raise ValueError("mesh.u_pts e mesh.v_pts devono essere > 1")
    for d in "uv":
        if int(m[f"{d}_growth_type"]) not in (1, 2, 3, 4):
            raise ValueError(f"mesh.{d}_growth_type deve essere 1, 2, 3 o 4")
        if float(m[f"{d}_growth_rate"]) <= 0 or int(m[f"{d}_periodicity"]) < 1:
            raise ValueError(f"mesh.{d}_growth_rate deve essere > 0 e mesh.{d}_periodicity >= 1")
    return [f"Mesh_{d.upper()};{int(m[d + '_pts'])};{int(m[d + '_growth_type'])};{float(m[d + '_growth_rate'])!r};"
            f"{int(m[d + '_periodicity'])}" for d in "uv"]


def _scale_lifting_block(block, chord_scale, mesh, te_type):
    """Scala la corda di ogni sezione attorno al suo bordo d'attacco (x e z scalati, y invariata)
    e riscrive Mesh_U/Mesh_V e i parametri del bordo d'uscita. Restituisce (righe, sezioni)."""
    if te_type.lower() not in TE_PARAMS:
        raise ValueError(f"geometry.te_type '{te_type}' non valido. Ammessi: {sorted(TE_PARAMS)}")
    drop = ("mesh_u;", "mesh_v;") + tuple(p.lower() for p in sum(TE_PARAMS.values(), []))
    out, sections = [], []
    for ln in block:
        low = ln.strip().lower()
        if low.startswith(drop):
            continue                                   # riscritti sotto in forma controllata
        if low.startswith("crosssection"):
            pts = _section_points(ln)
            xs = [p[0] for p in pts]
            xle, zle = pts[xs.index(min(xs))][0], pts[xs.index(min(xs))][2]
            new = [[xle + chord_scale * (x - xle), y, zle + chord_scale * (z - zle)] for x, y, z in pts]
            sections.append(new)
            out.append("CrossSection;" + ";".join(_fmt(c) for p in new for c in p))
            continue
        out.append(ln)
        if low.startswith("liftingsurface;true"):
            out.extend(mesh)
            out.extend(TE_PARAMS[te_type.lower()])
    return out, sections


def prepare_ccs(src, dst, chord_scale, mesh, te_type):
    """Copia il CCS scalando solo il componente portante (gli altri restano identici).
    Restituisce le sezioni scalate del componente portante."""
    with open(src, "r", encoding="utf-8-sig") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    if not any(ln.strip().lower().startswith("crosssection") for ln in lines):
        raise ValueError(f"Nessuna riga 'CrossSection' in {src}: non sembra un file CCS.")
    blocks = _split_components(lines)
    n_lift = sum(_is_lifting(b) for b in blocks)
    if n_lift != 1:
        raise ValueError(f"ccs_wing richiede esattamente un componente 'LiftingSurface;true' (trovati {n_lift}).")
    out, sections = [], []
    for b in blocks:
        if _is_lifting(b):
            new_lines, sections = _scale_lifting_block(b, chord_scale, mesh, te_type)
            out += new_lines
        else:
            out += b
    if len(sections) < 2:
        raise ValueError("Il componente portante ha meno di 2 sezioni.")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return sections


def wing_reference(sections):
    """Grandezze della semiala: corda = estensione in x di ogni sezione, ordinate per y medio."""
    st = sorted((sum(p[1] for p in s) / len(s), max(p[0] for p in s) - min(p[0] for p in s))
                for s in sections)
    pairs = list(zip(st, st[1:]))
    s_half = sum(0.5 * (c0 + c1) * (y1 - y0) for (y0, c0), (y1, c1) in pairs)
    int_c2 = sum((y1 - y0) * (c0 * c0 + c0 * c1 + c1 * c1) / 3.0 for (y0, c0), (y1, c1) in pairs)
    if s_half <= 0:
        raise ValueError("Area della semiala nulla: le sezioni non si estendono in y.")
    return {"y_root": st[0][0], "b_half": st[-1][0] - st[0][0], "chord_root": st[0][1],
            "chord_tip": st[-1][1], "S_half": s_half, "MAC": int_c2 / s_half}


_MODES = {
    "fixed": _fixed,
    "ccs_wing": _ccs_wing,
    "ccs_planform": _ccs_planform,
}
