#!/usr/bin/env python3
"""
fs_driver.py - Unico comando che HEEDS lancia, nella cartella del design:

    python <percorso>/fs_driver.py --config <percorso>/case.json

Passi: params.txt -> geometry.py -> script FlightStream -> run senza interfaccia
       -> postprocess.py -> results.txt (scritto SEMPRE, chiavi fisse, -999 = valore mancante).

status in results.txt:  0 ok | 1 errore generico/setup | 2 timeout | 3 solver non convergente
                        4 H/cf non estraibili (CL/CD validi) | 5 risultati non fisici
                        6 licenza FlightStream non disponibile (dopo run.license_retries tentativi)
Codice di uscita del processo: 0 se status = 0, altrimenti 1.
Il motivo di uno status diverso da 0 e' scritto in run_info.txt.

Opzioni per l'uso locale:
    --dry-run        scrive solo fs_script.txt (FlightStream non viene lanciato; status = 1)
    --extract-only   rilegge file gia' esistenti (--loads, --log, --vtk), senza lanciare nulla
    --validate       confronta CL/CDi/CDo/CMy con il blocco "validation" del JSON
    --probes         scrive in probes/ gli script di prova per OPEN e per il sistema dei momenti

Solo libreria standard di Python (>= 3.8).
"""
import argparse
import datetime as _dt
import glob
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback

import geometry
import postprocess as pp

__version__ = "2.2.0"

DEFAULTS = {
    "flightstream_exe": "",
    "geometry": {"mode": "fixed"},
    "case": {"aoa": 4.0, "velocity": 20.0, "sideslip": 0.0},
    "solver": {"iterations": 500, "convergence": 1.0e-5, "threads": 0,
               # modello fisico e INITIALIZE_SOLVER: usati solo se lo script inizializza la
               # simulazione (ccs_wing, oppure fixed con geometry.reinitialize = true)
               "model": "INCOMPRESSIBLE", "bl_type": "TRANSITIONAL", "roughness_nm": 0.0,
               "viscous_coupling": False, "wall_collision_avoidance": False,
               "init_surfaces": None, "wake_termination_x": "DEFAULT", "symmetry": None,
               "vorticity_drag_boundaries": -1},
    # fluido: valori del blocco (gli stessi del .fsm di riferimento) in tutte le modalita';
    # override_fluid = true = ISA alla quota 'altitude', in tutte le modalita'. Con un template
    # .fsm il fluido non viene riscritto (vale quello del file; i valori del JSON servono per
    # q, L, D: il 26.1 non scrive la densita' nella tabella dei carichi); con una simulazione
    # nuova (ccs_wing) lo script scrive FLUID_PROPERTIES con questi valori.
    "fluid": {"override_fluid": False, "density": None, "viscosity": None, "pressure": None,
              "temperature": None, "specific_heat_ratio": None},
    "reference": {"sref_m2": None, "lref_m": None, "symmetry_loads": True,
                  "moment_point_m": None, "moment_frame_index": 2},
    "postproc": {"vtk_surfaces": [], "strip": [0.45, 0.55], "bin_width": 0.02,
                 "xtr_threshold": 0.99, "te_window": [0.90, 0.98], "exclude_le": 0.05},
    # license_retries: nuovi tentativi (oltre al primo) se la licenza non e' disponibile,
    # ciascuno dopo license_wait_s secondi; se fallisce anche l'ultimo, status 6
    "run": {"timeout_s": 1800, "save_fsm": False, "license_retries": 2, "license_wait_s": 60},
    "validation": {"CL": None, "CDi": None, "CDo": None, "CMy": None, "Re_ref": None,
                   "iterations": None, "rel_tol": 0.01},
}

FLIGHT_VARS = ["aoa", "velocity", "altitude", "sideslip"]
REQUIRED = ["CL", "CDi", "CDo", "CMy"]
MISSING = -999
STATUS_TEXT = {0: "ok", 1: "errore generico/setup", 2: "timeout", 3: "solver non convergente",
               4: "H/cf non estraibili (CL/CD validi)", 5: "risultati non fisici",
               6: "licenza FlightStream non disponibile"}
# Checkout della licenza in fs_stdout.txt: FlightStream prova le Altair units, poi EDU, poi la
# licenza a feature. Se falliscono tutte, in modalita' -hidden resta aperto senza fare nulla.
LICENSE_FAIL = "checking out altair units...not available"
LICENSE_OK = ("success", "running script file")
LICENSE_GRACE_S = 15      # attesa dopo "Not available": un fallback (EDU, feature) puo' ancora riuscire
POLL_S = 1.0


class LicenseUnavailable(Exception):
    """Il checkout della licenza di FlightStream e' fallito (status 6)."""
FILES = {"script": "fs_script.txt", "ccs": "case_ccs.csv", "loads": "loads.txt",
         "vtk": "surface.vtk", "log": "fs_log.txt", "stdout": "fs_stdout.txt",
         "results": "results.txt", "info": "run_info.txt", "profiles": "bl_profiles.csv",
         "fsm_out": "case.fsm"}


def log(msg):
    """Messaggio a schermo con orario."""
    print(f"[fs_driver {_dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def _fmt(x):
    """Numero in forma compatta per lo script FlightStream."""
    return f"{x:.9g}"


def _onoff(flag):
    """True/False -> ENABLE/DISABLE."""
    return "ENABLE" if flag else "DISABLE"


def result_keys():
    """Chiavi di results.txt, sempre le stesse e nello stesso ordine per qualsiasi caso
    (le variabili geometriche di tutte le modalita' compaiono sempre, -999 se non usate)."""
    geo = []
    for names in geometry.GEOMETRY_VARIABLES.values():
        geo += [n for n in names if n not in geo]
    return (["status", "converged", "iterations",
             "CL", "CD", "CDi", "CDo", "CMx", "CMy", "CMz", "L_over_D", "L_N", "D_N", "q_Pa",
             "xtr_up", "xtr_lo", "H_te_up", "H_te_lo", "H_max_up", "H_max_lo", "cf_min_up", "cf_min_lo",
             "area_frac_cf_neg", "H_max", "sep_max"]
            + FLIGHT_VARS + geo + ["Sref_m2", "Lref_m", "Re_ref"])


# --------------------------------------------------------------------------------------
# Configurazione e parametri
# --------------------------------------------------------------------------------------
def _strip_notes(d):
    """Toglie le chiavi che iniziano con '_' (commenti nel JSON), a ogni livello."""
    if not isinstance(d, dict):
        return d
    return {k: _strip_notes(v) for k, v in d.items() if not k.startswith("_")}


def _merge(base, over):
    """Unisce due dizionari annidati: i valori di 'over' vincono."""
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def _warn_unknown(user):
    """Avvisa delle chiavi del JSON che il driver non conosce (probabili errori di battitura)."""
    for sec, val in user.items():
        if sec not in DEFAULTS:
            log(f"ATTENZIONE: sezione '{sec}' del JSON non riconosciuta (ignorata).")
        elif isinstance(val, dict) and sec not in ("geometry", "case"):
            for k in val:
                if k not in DEFAULTS[sec]:
                    log(f"ATTENZIONE: chiave '{sec}.{k}' del JSON non riconosciuta (ignorata).")


def load_config(path):
    """Legge il JSON del caso e lo completa con i valori di default."""
    with open(path, "r", encoding="utf-8") as f:
        user = _strip_notes(json.load(f))
    _warn_unknown(user)
    cfg = _merge(json.loads(json.dumps(DEFAULTS)), user)
    cfg["_dir"] = os.path.dirname(os.path.abspath(path))
    exe = cfg.get("flightstream_exe")
    if exe and not os.path.isabs(exe):
        cfg["flightstream_exe"] = os.path.join(cfg["_dir"], exe)
    return cfg


def read_params(path):
    """File 'chiave = valore' scritto da HEEDS (righe vuote e testo dopo # ignorati)."""
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if "=" not in line:
                raise ValueError(f"params.txt riga {n}: manca '=' ({line!r})")
            k, v = (s.strip() for s in line.split("=", 1))
            try:
                out[k] = float(v)
            except ValueError:
                raise ValueError(f"params.txt riga {n}: valore non numerico per '{k}' ({v!r})")
    return out


def uses_isa(cfg):
    """True se il fluido viene dall'ISA alla quota 'altitude' (solo con fluid.override_fluid)."""
    return bool(cfg["fluid"]["override_fluid"])


FLUID_KEYS = ["density", "viscosity", "pressure", "temperature", "specific_heat_ratio"]


def json_fluid(cfg, keys):
    """Valori del blocco fluid del JSON; errore chiaro se ne manca qualcuno."""
    missing = [k for k in keys if cfg["fluid"].get(k) is None]
    if missing:
        raise ValueError(f"mancano nel JSON {['fluid.' + k for k in missing]}: senza override_fluid servono i "
                         "valori del fluido del .fsm di riferimento (es. density 1.225, viscosity 1.78e-5, "
                         "pressure 101324.02, temperature 288.166, specific_heat_ratio 1.4).")
    return {k: float(cfg["fluid"][k]) for k in keys}


def make_case(cfg, params):
    """Valori del caso: blocco 'case' del JSON, sovrascritto da params.txt.
    Ogni chiave non ammessa per la modalita' geometrica scelta e' un errore."""
    mode = cfg["geometry"]["mode"]
    if mode not in geometry.GEOMETRY_VARIABLES:
        raise ValueError(f"geometry.mode '{mode}' sconosciuta. Disponibili: {sorted(geometry.GEOMETRY_VARIABLES)}")
    flight = [v for v in FLIGHT_VARS if v != "altitude" or uses_isa(cfg)]
    allowed = flight + geometry.GEOMETRY_VARIABLES[mode]
    case = {"altitude": 0.0} if "altitude" in allowed else {}
    for name, src in (("'case' del JSON", cfg["case"]), ("params.txt", params)):
        if "altitude" in src and "altitude" not in allowed:
            raise ValueError(f"'altitude' non ammessa in {name}: il fluido e' quello del blocco fluid del "
                             "JSON. Per imporre la quota (ISA) metti fluid.override_fluid = true nel JSON.")
        bad = [k for k in src if k not in allowed]
        if bad:
            raise ValueError(f"chiavi non ammesse in {name}: {bad}. Ammesse con mode='{mode}': {allowed}")
        case.update({k: float(v) for k, v in src.items()})
    missing = [k for k in allowed if k not in case]
    if missing:
        raise ValueError(f"valori mancanti (ne' in params.txt ne' in 'case' del JSON): {missing}")
    return case


def isa(alt_m):
    """Atmosfera standard ISA (troposfera) + legge di Sutherland, unita' SI."""
    T = 288.15 - 0.0065 * alt_m
    p = 101325.0 * (T / 288.15) ** 5.255877
    R = 287.05287
    return {"rho": p / (R * T), "p": p, "T": T, "a": math.sqrt(1.4 * R * T),
            "mu": 1.458e-6 * T ** 1.5 / (T + 110.4)}


def fluid_state(cfg, case):
    """Densita' e viscosita' usate per q, L, D e Re prima di leggere i risultati: ISA con
    override_fluid, altrimenti il blocco fluid del JSON (density obbligatoria)."""
    if uses_isa(cfg):
        atm = isa(case["altitude"])
        return {"rho": atm["rho"], "mu": atm["mu"], "source": f"ISA a {case['altitude']:g} m"}
    rho = json_fluid(cfg, ["density"])["density"]
    mu = cfg["fluid"].get("viscosity")
    return {"rho": rho, "mu": float(mu) if mu else None, "source": "JSON fluid"}


# --------------------------------------------------------------------------------------
# Script FlightStream
# --------------------------------------------------------------------------------------
def render(commands):
    """Testo dello script: ogni comando (lista di righe) seguito da una riga vuota. Manuale
    FlightStream: la riga vuota chiude i parametri di un comando su piu' righe, un commento no."""
    return "".join("\n".join(c) + "\n\n" for c in commands)


def fluid_lines(cfg, case):
    """FLUID_PROPERTIES (sintassi del manuale 26.1: SONIC_VELOCITY non e' piu' supportato, serve
    SPECIFIC_HEAT_RATIO): ISA alla quota del caso con override_fluid, altrimenti il blocco fluid
    del JSON se la simulazione nasce da zero. Con un template .fsm e senza override nessun
    comando: vale il fluido salvato nel file."""
    if uses_isa(cfg):
        atm = isa(case["altitude"])
        f = {"density": atm["rho"], "pressure": atm["p"], "temperature": atm["T"],
             "viscosity": atm["mu"], "specific_heat_ratio": 1.4}
    elif geometry.NEW_SIMULATION[cfg["geometry"]["mode"]]:
        f = json_fluid(cfg, FLUID_KEYS)
    else:
        return []
    return [["FLUID_PROPERTIES", f"DENSITY {_fmt(f['density'])}", f"PRESSURE {_fmt(f['pressure'])}",
             f"TEMPERATURE {_fmt(f['temperature'])}", f"VISCOSITY {_fmt(f['viscosity'])}",
             f"SPECIFIC_HEAT_RATIO {_fmt(f['specific_heat_ratio'])}"]]


def physics_lines(sol):
    """Modello fisico del solver, tutto esplicito (anche rugosita' 0 = superficie liscia), cosi'
    non resta nulla dello stato salvato in un .fsm. Il modello del solver (INCOMPRESSIBLE, ...)
    non e' qui: nel 26.1 e' un parametro di INITIALIZE_SOLVER (geometry.py)."""
    s = ["SET_SOLVER_STEADY", f"SET_BOUNDARY_LAYER_TYPE {sol['bl_type']}",
         f"SET_SURFACE_ROUGHNESS {_fmt(float(sol['roughness_nm'] or 0.0))}",
         f"SET_SOLVER_VISCOUS_COUPLING {_onoff(sol['viscous_coupling'])}"]
    return [[c] for c in s]


def vorticity_lines(sol):
    """Superfici per la resistenza indotta di vorticita' (CDi): -1 = tutte, altrimenti la lista
    degli indici. E' un comando di analisi: va dopo START_SOLVER, come nello script di riferimento."""
    ids = sol["vorticity_drag_boundaries"]
    if ids == -1:
        return [["SET_VORTICITY_DRAG_BOUNDARIES -1"]]
    return [[f"SET_VORTICITY_DRAG_BOUNDARIES {len(ids)}", ",".join(str(int(i)) for i in ids)]]


def moment_frame_lines(rf):
    """Sistema di riferimento per i momenti: assi paralleli al frame 1, origine nel punto del JSON.
    Restituisce (comandi, indice del frame dei carichi). Senza punto: nessun frame nuovo, frame 1."""
    if rf["moment_point_m"] is None:
        return [], 1
    n = int(rf["moment_frame_index"])
    x, y, z = (_fmt(float(v)) for v in rf["moment_point_m"])
    cmds = [["# sistema dei momenti: unita' di ORIGIN_* non documentate (da verificare),",
             "# l'origine viene poi reimpostata con SET_COORDINATE_SYSTEM_ORIGIN in METER",
             "CREATE_NEW_COORDINATE_SYSTEM"],
            ["EDIT_COORDINATE_SYSTEM", f"FRAME {n}", "NAME MOMENT_REF",
             f"ORIGIN_X {x}", f"ORIGIN_Y {y}", f"ORIGIN_Z {z}",
             "VECTOR_X_X 1", "VECTOR_X_Y 0", "VECTOR_X_Z 0",
             "VECTOR_Y_X 0", "VECTOR_Y_Y 1", "VECTOR_Y_Z 0",
             "VECTOR_Z_X 0", "VECTOR_Z_Y 0", "VECTOR_Z_Z 1"],
            [f"SET_COORDINATE_SYSTEM_ORIGIN {n} {x} {y} {z} METER"]]
    return cmds, n


def surfaces_lines(ids):
    """Selezione delle superfici per l'export VTK: lista vuota = tutte (SURFACES -1)."""
    if not ids:
        return ["SURFACES -1"]
    return [f"SURFACES {len(ids)}"] + [str(int(i)) for i in ids]


def build_script(cfg, case, geo, files, ref):
    """Script FlightStream completo: geometria, fluido, modello fisico, condizioni di volo,
    inizializzazione, run, export. L'ordine (condizioni prima di INITIALIZE_SOLVER, vorticity
    drag boundaries dopo START_SOLVER) e' quello dello script che ha prodotto il riferimento."""
    sol, rf = cfg["solver"], cfg["reference"]
    threads = sol["threads"] or max(1, (os.cpu_count() or 2) // 2)
    csys, frame = moment_frame_lines(rf)
    explicit = geo.get("explicit_physics", False)
    s = [["#", f"# Generato da fs_driver.py v{__version__} il {_dt.datetime.now():%Y-%m-%d %H:%M:%S}",
          f"# geometry.mode = {cfg['geometry']['mode']}", "#"]]
    s += geo["lines"]
    s += fluid_lines(cfg, case)
    if explicit:
        s += physics_lines(sol)
    s += csys
    s += [[c] for c in (
        f"SOLVER_SET_AOA {_fmt(case['aoa'])}", f"SOLVER_SET_SIDESLIP {_fmt(case['sideslip'])}",
        f"SOLVER_SET_VELOCITY {_fmt(case['velocity'])}", f"SOLVER_SET_REF_VELOCITY {_fmt(case['velocity'])}",
        f"SOLVER_SET_REF_AREA {_fmt(ref['Sref'])}", f"SOLVER_SET_REF_LENGTH {_fmt(ref['Lref'])}",
        f"SOLVER_SET_ITERATIONS {int(sol['iterations'])}", f"SOLVER_SET_CONVERGENCE {sol['convergence']:.3E}",
        f"SET_MAX_PARALLEL_THREADS {threads}")]
    s += geo["init_lines"]
    s += [[c] for c in ("CLEAR_SOLUTION", "CLEAR_LOG", "START_SOLVER")]
    if explicit:
        s += vorticity_lines(sol)
    s += [[c] for c in (
        f"SET_SOLVER_ANALYSIS_LOADS_FRAME {frame}", "SET_LOADS_AND_MOMENTS_UNITS COEFFICIENTS",
        f"SET_ANALYSIS_SYMMETRY_LOADS {_onoff(rf['symmetry_loads'])}")]
    s.append(["EXPORT_SOLVER_ANALYSIS_SPREADSHEET", files["loads"]])
    s.append(["SET_VTK_EXPORT_VARIABLES -1 DISABLE"])
    s.append(["EXPORT_SOLVER_ANALYSIS_VTK", files["vtk"]] + surfaces_lines(cfg["postproc"]["vtk_surfaces"]))
    s.append(["EXPORT_LOG", files["log"]])
    if cfg["run"]["save_fsm"]:
        s.append(["SAVEAS", files["fsm_out"]])
    s.append(["CLOSE_FLIGHTSTREAM"])
    return render(s)


# --------------------------------------------------------------------------------------
# Esecuzione di FlightStream
# --------------------------------------------------------------------------------------
def find_exe(cli_exe, cfg):
    """Eseguibile: --exe, poi FLIGHTSTREAM_EXE, poi JSON, poi PATH, poi Program Files\\Altair."""
    cands = [cli_exe, os.environ.get("FLIGHTSTREAM_EXE"), cfg.get("flightstream_exe"),
             shutil.which("FlightStream"), shutil.which("FlightStream.exe")]
    for c in cands:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    if platform.system() == "Windows":
        for r in filter(None, [os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432")]):
            hits = sorted(glob.glob(os.path.join(r, "Altair", "**", "FlightStream*.exe"), recursive=True))
            hits = [h for h in hits if os.path.basename(h).lower() == "flightstream.exe"] or hits
            if hits:
                return hits[-1]
    raise ValueError("eseguibile FlightStream non trovato: usa --exe, la variabile d'ambiente "
                     "FLIGHTSTREAM_EXE o 'flightstream_exe' nel JSON")


def _kill_tree(proc):
    """Termina FlightStream e gli eventuali processi figli."""
    if platform.system() == "Windows":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.kill()
    proc.wait()


def license_state(stdout_path):
    """Esito del checkout della licenza letto da fs_stdout.txt: 'ok', 'failed' o 'pending'."""
    try:
        with open(stdout_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().lower()
    except OSError:
        return "pending"
    if any(k in text for k in LICENSE_OK):
        return "ok"
    return "failed" if LICENSE_FAIL in text else "pending"


def run_flightstream(exe, script, workdir, timeout):
    """Lancia FlightStream senza interfaccia e controlla fs_stdout.txt mentre gira. Solleva
    subprocess.TimeoutExpired se non finisce entro timeout e LicenseUnavailable se il checkout
    della licenza fallisce (in entrambi i casi FlightStream viene chiuso)."""
    cmd = [exe, "-hidden", "-script", script] if platform.system() == "Windows" else [exe, script]
    log("Comando: " + " ".join(f'"{x}"' if " " in x else x for x in cmd))
    stdout_path = os.path.join(workdir, FILES["stdout"])
    t0, lic, fail_t = time.time(), "pending", None
    with open(stdout_path, "w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen(cmd, cwd=workdir, stdout=out, stderr=subprocess.STDOUT)
        while proc.poll() is None:
            now = time.time()
            if now - t0 > timeout:
                _kill_tree(proc)
                raise subprocess.TimeoutExpired(cmd, timeout)
            if lic != "ok":
                lic = license_state(stdout_path)
                fail_t = (fail_t or now) if lic == "failed" else None
                if fail_t is not None and now - fail_t >= LICENSE_GRACE_S:
                    _kill_tree(proc)
                    raise LicenseUnavailable("licenza FlightStream non disponibile (fs_stdout.txt: "
                                             "'Checking out Altair units...Not available')")
            time.sleep(POLL_S)
    log(f"FlightStream terminato in {time.time() - t0:.1f} s (codice {proc.returncode}).")
    return proc.returncode


def run_with_license_retries(exe, script, workdir, run_cfg, notes):
    """run_flightstream con nuovi tentativi se la licenza non e' disponibile: license_retries
    tentativi oltre al primo, ciascuno dopo license_wait_s secondi; poi LicenseUnavailable."""
    retries, wait = int(run_cfg["license_retries"]), float(run_cfg["license_wait_s"])
    for attempt in range(retries + 1):
        try:
            return run_flightstream(exe, script, workdir, run_cfg["timeout_s"])
        except LicenseUnavailable:
            notes.append(f"licenza non disponibile al tentativo {attempt + 1} di {retries + 1}")
            if attempt == retries:
                raise
            log(f"Licenza non disponibile: nuovo tentativo tra {wait:g} s ({attempt + 1}/{retries}).")
            time.sleep(wait)


# --------------------------------------------------------------------------------------
# Risultati
# --------------------------------------------------------------------------------------
def read_coefficients(files, notes):
    """Blocco 1: carichi (con il log come riserva) e convergenza. Errore solo se mancano entrambi."""
    loads = logd = None
    for key in ("loads", "log"):
        path = files.get(key)
        if not path or not os.path.isfile(path):
            notes.append(f"{key}: file assente ({path})")
            continue
        try:
            if key == "loads":
                loads = pp.parse_loads(path)
            else:
                logd = pp.parse_log(path)
        except ValueError as e:
            notes.append(f"{key}: {e}")
    if loads is None and logd is None:
        raise ValueError("nessun risultato leggibile (ne' loads ne' log): vedi fs_stdout.txt e fs_script.txt")
    if loads is None:
        notes.append("coefficienti presi dal log: CDo non disponibile")
    elif logd and loads.get("CL") is not None and abs(loads["CL"] - logd["CL"]) > 2e-3:
        notes.append(f"ATTENZIONE: CL tabella {loads['CL']} diverso da CL log {logd['CL']}")
    return loads, logd


def read_boundary_layer(files, mode, ppcfg, notes):
    """Blocco 2: strato limite dal VTK. Restituisce (metriche, ok); un errore qui non tocca CL/CD."""
    try:
        if not files.get("vtk") or not os.path.isfile(files["vtk"]):
            raise ValueError(f"file VTK assente ({files.get('vtk')})")
        vtk = pp.read_vtk(files["vtk"])
        out = pp.generic_metrics(vtk)
        if geometry.POSTPROC[mode] == "wing_strip":
            strip, prof = pp.wing_strip_metrics(vtk, ppcfg)
            out.update(strip)
            pp.write_profiles(files["profiles"], prof)
        return out, True
    except Exception as e:
        notes.append(f"H/cf: {type(e).__name__}: {e}")
        return {}, False


def dimensional(res, case, ref, fluid, header=None):
    """Pressione dinamica, L e D in newton, Reynolds sulla lunghezza di riferimento.
    Se la tabella dei carichi riporta densita' o Reynolds, valgono quelli di FlightStream."""
    header = header or {}
    rho = header.get("density") or fluid["rho"]
    q = 0.5 * rho * case["velocity"] ** 2
    out = {"q_Pa": q, "Re_ref": header.get("reynolds")}
    if out["Re_ref"] is None and ref["Lref"] and fluid["mu"]:
        out["Re_ref"] = rho * case["velocity"] * ref["Lref"] / fluid["mu"]
    for coef, force in (("CL", "L_N"), ("CD", "D_N")):
        ok = res.get(coef) is not None and ref["Sref"]
        out[force] = res[coef] * q * ref["Sref"] if ok else None
    return out


def decide_status(res, bl_ok, notes):
    """Priorita': 1 coefficienti mancanti > 3 non convergente > 5 non fisico > 4 H/cf > 0."""
    missing = [k for k in REQUIRED if res.get(k) is None]
    if missing:
        notes.append(f"coefficienti mancanti: {missing}")
        return 1
    if res.get("converged") != 1:
        notes.append("convergenza non raggiunta o non verificabile dal log")
        return 3
    bad = pp.check_physics(res)
    if bad:
        notes.extend(bad)
        return 5
    return 0 if bl_ok else 4


def extract(files, mode, cfg, case, ref, fluid, res, notes):
    """Legge tutti i risultati in blocchi indipendenti, aggiorna res e restituisce lo status."""
    loads, logd = read_coefficients(files, notes)
    res.update(pp.coefficients(loads, logd))
    res.update(pp.convergence(logd, cfg["solver"]["iterations"], cfg["solver"]["convergence"]))
    header = (loads or {}).get("_header", {})
    res.update(dimensional(res, case, ref, fluid, header))
    notes.append(f"densita' per q, L, D: {header.get('density') or fluid['rho']:.6g} kg/m^3 "
                 f"({'tabella dei carichi' if header.get('density') else fluid['source']})")
    bl, bl_ok = read_boundary_layer(files, mode, cfg["postproc"], notes)
    res.update(bl)
    return decide_status(res, bl_ok, notes)


def _value(v):
    """Valore per results.txt: numeri finiti, altrimenti -999."""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float) and math.isfinite(v):
        return f"{v + 0.0:.6g}"                        # + 0.0 trasforma -0.0 in 0
    return str(MISSING)


def write_results(workdir, res):
    """results.txt: tutte le chiavi, sempre nello stesso ordine, formato 'chiave = valore'."""
    with open(os.path.join(workdir, FILES["results"]), "w", encoding="utf-8") as f:
        for k in result_keys():
            f.write(f"{k} = {_value(res.get(k))}\n")


def write_run_info(workdir, status, notes):
    """run_info.txt: status in chiaro e motivi (per le persone, HEEDS non lo legge)."""
    with open(os.path.join(workdir, FILES["info"]), "w", encoding="utf-8") as f:
        f.write(f"status = {status} ({STATUS_TEXT.get(status, '?')})\n")
        f.write(f"fs_driver v{__version__}, {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        for n in notes:
            f.write(f"- {n}\n")


def clean_old(workdir, keep_inputs):
    """Cancella i risultati di run precedenti (con --extract-only si tengono loads/log/vtk)."""
    names = ["results", "info", "profiles"] + ([] if keep_inputs else ["loads", "vtk", "log", "stdout"])
    for k in names:
        p = os.path.join(workdir, FILES[k])
        if os.path.exists(p):
            os.remove(p)


def validate(res, val):
    """Confronto con il run manuale di riferimento (solo stampa, non cambia lo status)."""
    ok = True
    log("Validazione rispetto al run manuale:")
    for k in ("CL", "CDi", "CDo", "CMy", "Re_ref", "iterations"):
        refv, got = val.get(k), res.get(k)
        if refv is None:
            continue
        err = abs(got - refv) / max(abs(refv), 1e-12) if got is not None else float("inf")
        ok &= err <= val["rel_tol"]
        fmt = "{: .5f}" if abs(refv) < 10 else "{: .0f}"
        shown = fmt.format(got) if got is not None else "  manca"
        print(f"   {'OK ' if err <= val['rel_tol'] else 'NO '} {k:10s} riferimento {fmt.format(refv)}  "
              f"ottenuto {shown}  scarto {100 * err:6.2f} %")
    print("   ESITO:", "SUPERATA" if ok else "NON SUPERATA")


# --------------------------------------------------------------------------------------
# Script di prova
# --------------------------------------------------------------------------------------
PROBES = {
    "probe_1_solo_file": [],
    "probe_2_entrambi": ["RESET_PARALLEL_CORES ENABLE", "LOAD_SOLVER_INITIALIZATION ENABLE"],
    "probe_3_solo_loadinit": ["LOAD_SOLVER_INITIALIZATION ENABLE"],
}


def write_probes(cfg, workdir, exe_arg):
    """Scrive in probes/ gli script minimi per provare a mano la sintassi di OPEN (1-3) e il
    sistema di riferimento dei momenti (4, OPEN con l'inizializzazione del .fsm), piu' un .bat che li lancia."""
    fsm = geometry.fixed_template(cfg)
    if not os.path.isfile(fsm):
        log(f"ATTENZIONE: template .fsm non trovato ({fsm}); gli script vengono scritti lo stesso.")
    out = os.path.join(workdir, "probes")
    os.makedirs(out, exist_ok=True)
    rf = dict(cfg["reference"])
    rf["moment_point_m"] = rf["moment_point_m"] or [0.0, 0.0, 0.0]
    scripts = {name: geometry.open_lines(fsm, opts) for name, opts in PROBES.items()}
    scripts["probe_4_csys"] = (geometry.open_lines(fsm, ["LOAD_SOLVER_INITIALIZATION ENABLE"])
                               + moment_frame_lines(rf)[0])
    try:
        exe = find_exe(exe_arg, cfg)
    except ValueError:
        exe = r"C:\percorso\di\FlightStream.exe"
    bat = ["@echo off", f'cd /d "{out}"']
    for name, cmds in scripts.items():
        cmds = [[f"# {name}"]] + cmds + [["EXPORT_LOG", os.path.join(out, name + "_log.txt")],
                                         ["CLOSE_FLIGHTSTREAM"]]
        with open(os.path.join(out, name + ".txt"), "w", encoding="utf-8") as f:
            f.write(render(cmds))
        bat += [f"echo {name}", f'"{exe}" -hidden -script "{os.path.join(out, name + ".txt")}"',
                f'if exist FlightStreamLog.txt move /y FlightStreamLog.txt {name}_FlightStreamLog.txt >nul']
    with open(os.path.join(out, "run_probes.bat"), "w", encoding="utf-8") as f:
        f.write("\n".join(bat) + "\n")
    log(f"Script di prova scritti in {out} (lancia run_probes.bat).")


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def parse_args(argv):
    """Opzioni da riga di comando."""
    ap = argparse.ArgumentParser(description="FlightStream in batch per HEEDS.")
    ap.add_argument("--config", required=True, help="JSON del caso")
    ap.add_argument("--params", default="params.txt", help="file dei parametri, relativo a --workdir (default: params.txt)")
    ap.add_argument("--workdir", default=".", help="cartella del design (default: cartella corrente)")
    ap.add_argument("--exe", help="percorso di FlightStream (altrimenti FLIGHTSTREAM_EXE o JSON)")
    ap.add_argument("--dry-run", action="store_true", help="scrive solo lo script FlightStream")
    ap.add_argument("--validate", action="store_true", help="confronta con il blocco 'validation'")
    ap.add_argument("--extract-only", action="store_true", help="rilegge loads/log/VTK gia' esistenti")
    ap.add_argument("--loads"); ap.add_argument("--log"); ap.add_argument("--vtk")
    ap.add_argument("--probes", action="store_true", help="scrive gli script di prova in probes/")
    return ap.parse_args(argv)


def run(a, cfg, workdir, res, notes):
    """Esegue il caso: aggiorna res e notes e restituisce lo status."""
    mode = cfg["geometry"]["mode"]
    params_path = os.path.join(workdir, a.params)          # un percorso assoluto resta invariato
    if not os.path.isfile(params_path):
        raise ValueError(f"file dei parametri non trovato: {params_path}")
    case = make_case(cfg, read_params(params_path))
    res.update(case)
    fluid = fluid_state(cfg, case)
    rf = cfg["reference"]
    if a.extract_only:
        files = {"loads": a.loads, "log": a.log, "vtk": a.vtk,
                 "profiles": os.path.join(workdir, FILES["profiles"])}
        ref = {"Sref": rf["sref_m2"], "Lref": rf["lref_m"]}
    else:
        files = {k: os.path.join(workdir, v) for k, v in FILES.items()}
        geo = geometry.build_geometry(case, cfg, workdir)
        ref = {"Sref": rf["sref_m2"] or geo["Sref"], "Lref": rf["lref_m"] or geo["Lref"]}
        if not ref["Sref"] or not ref["Lref"]:
            raise ValueError("Sref/Lref mancanti: con questa modalita' vanno nel JSON "
                             "(reference.sref_m2, reference.lref_m)")
        if " " in workdir:
            notes.append("percorso di lavoro con spazi: se FlightStream non trova i file, usare cartelle senza spazi")
        with open(files["script"], "w", encoding="utf-8") as f:
            f.write(build_script(cfg, case, geo, files, ref))
        log(f"Script scritto: {files['script']}")
    res.update({"Sref_m2": ref["Sref"], "Lref_m": ref["Lref"]})
    res.update(dimensional(res, case, ref, fluid))
    if a.dry_run and not a.extract_only:
        notes.append("dry-run: FlightStream non lanciato")
        return 1
    if not a.extract_only:
        rc = run_with_license_retries(find_exe(a.exe, cfg), files["script"], workdir, cfg["run"], notes)
        if rc != 0:
            notes.append(f"FlightStream ha restituito il codice {rc}")
    status = extract(files, mode, cfg, case, ref, fluid, res, notes)
    if a.validate:
        validate(res, cfg["validation"])
    return status


def main(argv=None):
    """Punto d'ingresso: results.txt e run_info.txt vengono scritti in ogni caso."""
    a = parse_args(argv)
    workdir = os.path.abspath(a.workdir)
    os.makedirs(workdir, exist_ok=True)
    if a.probes:
        write_probes(load_config(a.config), workdir, a.exe)
        return 0
    clean_old(workdir, a.extract_only)
    res, notes, status = {}, [], 1
    try:
        cfg = load_config(a.config)
        status = run(a, cfg, workdir, res, notes)
    except subprocess.TimeoutExpired as e:
        status = 2
        notes.append(f"FlightStream non ha terminato entro {e.timeout} s")
    except LicenseUnavailable as e:
        status = 6
        notes.append(f"{e}: FlightStream chiuso, nessun risultato")
    except Exception as e:
        status = 1
        notes.append(f"{type(e).__name__}: {e}")
        if not isinstance(e, (ValueError, OSError)):
            notes.append(traceback.format_exc())
    finally:
        res["status"] = status
        write_results(workdir, res)
        write_run_info(workdir, status, notes)
    log(f"status = {status} ({STATUS_TEXT[status]})" + "".join(f"\n    - {n}" for n in notes[:6]))
    return 0 if status == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
