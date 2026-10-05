#!/usr/bin/env python3
"""
fs_driver.py - Unico comando che HEEDS lancia, nella cartella del design:

    python <percorso>/fs_driver.py --config <percorso>/case.json

Passi: params.txt -> geometry.py -> script FlightStream -> run senza interfaccia
       -> postprocess.py -> results.txt (scritto SEMPRE, chiavi fisse, -999 = valore mancante).

status in results.txt:  0 ok | 1 errore generico/setup | 2 timeout | 3 solver non convergente
                        4 H/cf non estraibili (CL/CD validi) | 5 risultati non fisici
                        6 FlightStream non disponibile: licenza (dopo run.license_retries
                          tentativi) oppure FlightStream gia' attivo prima del lancio
Codice di uscita del processo: 0 se lo status e' in heeds.success_statuses del JSON (default [0]),
altrimenti 1. Il motivo di uno status diverso da 0 e' scritto in run_info.txt, che termina sempre
con la riga 'FS_DRIVER_RESULT status=<n> success=<0|1>' (anche ultima riga dell'output).
results.txt contiene 'schema_version = <n>' (versione dell'elenco e dell'ordine delle chiavi).

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
import re
import shutil
import subprocess
import sys
import time
import traceback

import geometry
import postprocess as pp

__version__ = "2.4.1"

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
                 "xtr_threshold": 0.99, "te_window": [0.90, 0.98], "exclude_le": 0.05,
                 # metriche di separazione con wing_frame (postprocess.wing_frame_metrics)
                 "sep_cf": 1.0e-5, "le_xc": 0.15, "lo_te_xc": 0.8, "x_sep_eta": [0.05, 0.95],
                 "h_attached_xc_max": 0.95},
    # assi dell'ala per dorso/ventre, x/c e strisce: null = metriche di separazione a -999
    # (es. fusoliera). Forma: {"chord_axis": "+x", "span_axis": "+y", "up_axis": "+z"}
    "wing_frame": None,
    # license_retries: nuovi tentativi (oltre al primo) se la licenza non e' disponibile,
    # ciascuno dopo license_wait_s secondi; se fallisce anche l'ultimo, status 6
    # flightstream_process_names: nomi dei processi di FlightStream (controllo prima del lancio e
    # pulizia dopo); kill_stale_flightstream: se true, prima del lancio chiude i processi di
    # FlightStream gia' attivi (GUI aperta, processi orfani); se false (default) il run da' status 6
    "run": {"timeout_s": 1800, "save_fsm": False, "license_retries": 2, "license_wait_s": 60,
            "flightstream_process_names": ["FlightStream.exe"], "kill_stale_flightstream": False},
    # codice di uscita del processo: 0 se lo status e' in success_statuses, altrimenti 1
    # ([0] per l'ottimizzazione, [0, 4] per DOE in cui H/cf non sono obiettivi)
    "heeds": {"success_statuses": [0]},
    "validation": {"CL": None, "CDi": None, "CDo": None, "CMy": None, "Re_ref": None,
                   "iterations": None, "rel_tol": 0.01},
}

FLIGHT_VARS = ["aoa", "velocity", "altitude", "sideslip"]
REQUIRED = ["CL", "CDi", "CDo", "CMy"]
MISSING = -999
STATUS_TEXT = {0: "ok", 1: "errore generico/setup", 2: "timeout", 3: "solver non convergente",
               4: "H/cf non estraibili (CL/CD validi)", 5: "risultati non fisici",
               6: "FlightStream non disponibile (licenza o processo gia' attivo)"}
# Checkout della licenza in fs_stdout.txt: FlightStream prova le Altair units, poi EDU, poi la
# licenza a feature. Se falliscono tutte, in modalita' -hidden resta aperto senza fare nulla.
LICENSE_FAIL = "checking out altair units...not available"
LICENSE_OK = ("success", "running script file")
LICENSE_GRACE_S = 15      # attesa dopo "Not available": un fallback (EDU, feature) puo' ancora riuscire
POLL_S = 1.0
STALE_WAIT_S = 10         # prima del lancio: attesa che un FlightStream appena chiuso sparisca


class FlightStreamUnavailable(Exception):
    """FlightStream non utilizzabile ora, per motivi della macchina e non del design (status 6)."""


class LicenseUnavailable(FlightStreamUnavailable):
    """Il checkout della licenza di FlightStream e' fallito."""


class FlightStreamBusy(FlightStreamUnavailable):
    """C'e' gia' un processo FlightStream attivo (GUI aperta o processo orfano)."""
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


# Schema di results.txt: UNICO punto in cui si decidono chiavi e ordine. Stesso elenco per tutte
# le modalita' (unione delle chiavi di fixed e ccs_wing); le chiavi non pertinenti valgono -999.
# HEEDS legge le risposte per posizione: una chiave nuova si aggiunge SOLO in fondo al file, cioe'
# in coda all'ultima sezione (vedi README, "Contratto con HEEDS"); mai in mezzo, mai riordinare o
# togliere chiavi. Ogni modifica dello schema incrementa SCHEMA_VERSION (scritto in results.txt).
SCHEMA_VERSION = 2
RESULTS_SCHEMA = (
    ("stato", ["schema_version", "status", "converged", "iterations"]),
    ("carichi", ["CL", "CD", "CDi", "CDo", "CMx", "CMy", "CMz", "L_over_D", "L_N", "D_N"]),
    ("riferimenti", ["Sref_m2", "Lref_m", "Re_ref", "q_Pa"]),
    ("strato_limite", ["xtr_up", "xtr_lo", "H_te_up", "H_te_lo", "H_max_up", "H_max_lo",
                       "cf_min_up", "cf_min_lo", "area_frac_cf_neg", "H_max", "sep_max",
                       "sep_frac_up_le", "x_sep_up", "H_max_attached_up", "x_H_max_attached_up",
                       "sep_frac_lo_te"]),
    ("ingressi", ["aoa", "velocity", "altitude", "sideslip", "chord_scale"]),
)


def result_keys():
    """Chiavi di results.txt nell'ordine di RESULTS_SCHEMA."""
    return [k for _, keys in RESULTS_SCHEMA for k in keys]


def _check_schema():
    """Ogni variabile di ingresso (anche quelle geometriche di tutte le modalita') e ogni metrica
    dell'ala deve avere il suo posto nello schema: una modalita' nuova senza aggiornare lo schema
    blocca il driver invece di spostare in silenzio le posizioni lette da HEEDS."""
    keys = result_keys()
    if len(keys) != len(set(keys)):
        raise RuntimeError("RESULTS_SCHEMA contiene chiavi duplicate")
    need = set(FLIGHT_VARS) | set(pp.WING_KEYS)
    for names in geometry.GEOMETRY_VARIABLES.values():
        need |= set(names)
    missing = sorted(need - set(keys))
    if missing:
        raise RuntimeError(f"RESULTS_SCHEMA non contiene {missing}: aggiungile in fondo all'ultima sezione")


_check_schema()


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
        elif isinstance(val, dict) and sec not in ("geometry", "case", "wing_frame"):   # wing_frame: postprocess
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
    ok = cfg["heeds"]["success_statuses"]
    if not isinstance(ok, list) or not ok or any(s not in STATUS_TEXT for s in ok):
        raise ValueError(f"heeds.success_statuses = {ok!r} non valido: lista non vuota di status "
                         f"tra {sorted(STATUS_TEXT)} (es. [0] oppure [0, 4])")
    exe = cfg.get("flightstream_exe")
    if exe and not os.path.isabs(exe):
        cfg["flightstream_exe"] = os.path.join(cfg["_dir"], exe)
    return cfg


_PARAM_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PARAM_FLOAT = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


def read_params(path):
    """File 'chiave = valore' scritto da HEEDS. Righe vuote e testo dopo # ignorati; CRLF/LF, BOM,
    spazi attorno e ultima riga senza a capo accettati. Valore: qualsiasi numero decimale nei
    formati di stampa di HEEDS (4, 4.0, 4.000000E+00, 4.0e0, -1.5E-01). Errore (status 1) per righe
    senza '=' o con piu' '=', chiave non valida, valore non numerico o non finito, chiave ripetuta."""
    out = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for n, raw in enumerate(f, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.count("=") != 1:
                raise ValueError(f"params.txt riga {n}: attesa una riga 'chiave = valore' ({raw.strip()!r})")
            k, v = (s.strip() for s in line.split("="))
            if not _PARAM_KEY.fullmatch(k):
                raise ValueError(f"params.txt riga {n}: nome di variabile non valido ({k!r})")
            if not _PARAM_FLOAT.fullmatch(v):
                raise ValueError(f"params.txt riga {n}: valore non numerico per '{k}' ({v!r})")
            if k in out:
                raise ValueError(f"params.txt riga {n}: '{k}' compare piu' di una volta")
            out[k] = float(v)
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


def list_processes():
    """Processi attivi come {pid: (ppid, nome)}. Windows: snapshot Toolhelp32 via ctypes (solo
    libreria standard). Altri sistemi: {} (controlli sui processi disattivati)."""
    if os.name != "nt":
        return {}
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)                      # TH32CS_SNAPPROCESS
    if snap in (None, wintypes.HANDLE(-1).value):
        return {}
    out, e = {}, PROCESSENTRY32W()
    e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            out[e.th32ProcessID] = (e.th32ParentProcessID, e.szExeFile)
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return out


def _descendants(root, procs):
    """PID di root e di tutti i suoi discendenti in un'istantanea di list_processes()."""
    tree, changed = {root}, True
    while changed:
        new = {pid for pid, (ppid, _) in procs.items() if ppid in tree and pid not in tree}
        tree |= new
        changed = bool(new)
    return tree


def running_flightstream(names):
    """Processi attivi con uno dei nomi indicati (confronto senza maiuscole): [(pid, nome)]."""
    wanted = {n.lower() for n in names}
    return sorted((pid, nm) for pid, (_, nm) in list_processes().items() if nm.lower() in wanted)


def _taskkill(pid, tree=True):
    """Chiude un processo (e con tree il suo albero) senza chiedere conferma."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F"] + (["/T"] if tree else []) + ["/PID", str(pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def preflight_flightstream(run_cfg, notes):
    """Prima del lancio: nessun FlightStream deve essere attivo (GUI aperta, processo orfano,
    run di un altro design). Si aspetta fino a STALE_WAIT_S che sparisca; poi, se
    kill_stale_flightstream e' attivo, lo si chiude, altrimenti FlightStreamBusy (status 6).
    I processi vengono chiusi solo con kill_stale_flightstream = true."""
    names = run_cfg["flightstream_process_names"]
    t0 = time.time()
    found = running_flightstream(names)
    while found and time.time() - t0 < STALE_WAIT_S:
        time.sleep(POLL_S)
        found = running_flightstream(names)
    if not found:
        return
    desc = ", ".join(f"{nm} PID {pid}" for pid, nm in found)
    if not run_cfg["kill_stale_flightstream"]:
        raise FlightStreamBusy(f"FlightStream gia' attivo ({desc}): non lanciato. Chiudere la GUI o i "
                               "processi orfani, oppure run.kill_stale_flightstream = true")
    for pid, _ in found:
        _taskkill(pid)
    time.sleep(2 * POLL_S)
    left = running_flightstream(names)
    notes.append(f"kill_stale_flightstream: chiusi {desc}" + (f"; ancora attivi: {left}" if left else ""))
    if left:
        raise FlightStreamBusy(f"FlightStream ancora attivo dopo la chiusura forzata: {left}")


def _close_run_tree(proc, seen, notes, force):
    """Dopo un run: con force chiude l'albero di FlightStream (taskkill /T /F); poi chiude i processi
    visti nell'albero durante il run e ancora vivi con lo stesso nome (sono del run) e verifica che
    non ne resti nessuno."""
    if force and proc.poll() is None:
        _taskkill(proc.pid)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        _taskkill(proc.pid, tree=False)
    for _ in range(3):
        alive = list_processes()
        left = {pid: nm for pid, nm in seen.items()
                if pid != proc.pid and pid in alive and alive[pid][1] == nm}
        if not left:
            return
        for pid in left:
            _taskkill(pid)
        time.sleep(POLL_S)
    notes.append(f"ATTENZIONE: processi del run ancora attivi dopo la chiusura: {left}")


def _kill_tree(proc):
    """Termina FlightStream e gli eventuali processi figli (taskkill /T /F)."""
    _taskkill(proc.pid)
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


def run_flightstream(exe, script, workdir, timeout, notes):
    """Lancia FlightStream senza interfaccia, controlla fs_stdout.txt e registra l'albero dei
    processi mentre gira. Solleva subprocess.TimeoutExpired se non finisce entro timeout e
    LicenseUnavailable se il checkout della licenza fallisce: in entrambi i casi l'albero viene
    chiuso e si verifica che non resti nessun processo del run."""
    cmd = [exe, "-hidden", "-script", script] if platform.system() == "Windows" else [exe, script]
    log("Comando: " + " ".join(f'"{x}"' if " " in x else x for x in cmd))
    stdout_path = os.path.join(workdir, FILES["stdout"])
    t0, lic, fail_t, seen = time.time(), "pending", None, {}
    with open(stdout_path, "w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen(cmd, cwd=workdir, stdout=out, stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None:
                procs = list_processes()
                seen.update({pid: procs[pid][1] for pid in _descendants(proc.pid, procs) if pid in procs})
                now = time.time()
                if now - t0 > timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)
                if lic != "ok":
                    lic = license_state(stdout_path)
                    fail_t = (fail_t or now) if lic == "failed" else None
                    if fail_t is not None and now - fail_t >= LICENSE_GRACE_S:
                        raise LicenseUnavailable("licenza FlightStream non disponibile (fs_stdout.txt: "
                                                 "'Checking out Altair units...Not available')")
                time.sleep(POLL_S)
        except BaseException:
            _close_run_tree(proc, seen, notes, force=True)
            raise
        finally:
            if seen:
                notes.append("processi del run: " + ", ".join(f"{nm} (PID {pid})" for pid, nm in sorted(seen.items())))
    _close_run_tree(proc, seen, notes, force=False)
    log(f"FlightStream terminato in {time.time() - t0:.1f} s (codice {proc.returncode}).")
    return proc.returncode


def run_with_license_retries(exe, script, workdir, run_cfg, notes):
    """run_flightstream con nuovi tentativi se la licenza non e' disponibile: license_retries
    tentativi oltre al primo, ciascuno dopo license_wait_s secondi; poi LicenseUnavailable.
    Prima di ogni tentativo: nessun FlightStream gia' attivo (preflight_flightstream)."""
    retries, wait = int(run_cfg["license_retries"]), float(run_cfg["license_wait_s"])
    for attempt in range(retries + 1):
        preflight_flightstream(run_cfg, notes)
        try:
            return run_flightstream(exe, script, workdir, run_cfg["timeout_s"], notes)
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


def read_boundary_layer(files, mode, ppcfg, frame, notes):
    """Blocco 2: strato limite dal VTK. Restituisce (metriche, ok); un errore qui non tocca CL/CD
    (status 4) e le metriche gia' calcolate restano. frame = wing_frame interpretato, oppure None
    (metriche di separazione dell'ala a -999)."""
    out = {}
    try:
        if not files.get("vtk") or not os.path.isfile(files["vtk"]):
            raise ValueError(f"file VTK assente ({files.get('vtk')})")
        vtk = pp.read_vtk(files["vtk"])
        out.update(pp.generic_metrics(vtk))
        if geometry.POSTPROC[mode] == "wing_strip":
            strip, prof = pp.wing_strip_metrics(vtk, ppcfg)
            out.update(strip)
            pp.write_profiles(files["profiles"], prof)
        if frame is not None:
            out.update(pp.wing_frame_metrics(vtk, frame, ppcfg))
        return out, True
    except Exception as e:
        notes.append(f"H/cf: {type(e).__name__}: {e}")
        return out, False


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
    bl, bl_ok = read_boundary_layer(files, mode, cfg["postproc"], cfg["_wing_frame"], notes)
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


def result_line(status, ok_statuses):
    """Riga fissa per la condizione 'File contains' di HEEDS: status e success (1 se lo status e'
    in heeds.success_statuses, cioe' se il codice di uscita e' 0)."""
    return f"FS_DRIVER_RESULT status={status} success={int(status in ok_statuses)}"


def write_run_info(workdir, status, notes, ok_statuses):
    """run_info.txt: status in chiaro e motivi; l'ultima riga e' sempre quella di result_line."""
    with open(os.path.join(workdir, FILES["info"]), "w", encoding="utf-8") as f:
        f.write(f"status = {status} ({STATUS_TEXT.get(status, '?')})\n")
        f.write(f"fs_driver v{__version__}, {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n")
        for n in notes:
            f.write(f"- {n}\n")
        f.write(result_line(status, ok_statuses) + "\n")


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
    # wing_frame controllato subito: un errore nel JSON e' un errore di setup (status 1)
    cfg["_wing_frame"] = pp.parse_wing_frame(cfg["wing_frame"]) if cfg["wing_frame"] else None
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
        # percorsi con spazi nello script FlightStream (senza virgolette): verificati con run reali
        # fixed e ccs_wing in C:\fs test\... (FlightStream 26.1, 2026-10-04)
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
    res, notes, status, ok_statuses = {}, [], 1, DEFAULTS["heeds"]["success_statuses"]
    try:
        cfg = load_config(a.config)
        ok_statuses = cfg["heeds"]["success_statuses"]
        status = run(a, cfg, workdir, res, notes)
    except subprocess.TimeoutExpired as e:
        status = 2
        notes.append(f"FlightStream non ha terminato entro {e.timeout} s")
    except LicenseUnavailable as e:
        status = 6
        notes.append(f"{e}: FlightStream chiuso, nessun risultato")
    except FlightStreamBusy as e:
        status = 6
        notes.append(f"{e}")
    except Exception as e:
        status = 1
        notes.append(f"{type(e).__name__}: {e}")
        if not isinstance(e, (ValueError, OSError)):
            notes.append(traceback.format_exc())
    finally:
        res["schema_version"], res["status"] = SCHEMA_VERSION, status
        write_results(workdir, res)
        write_run_info(workdir, status, notes, ok_statuses)
    log(f"status = {status} ({STATUS_TEXT[status]})" + "".join(f"\n    - {n}" for n in notes[:6]))
    print(result_line(status, ok_statuses), flush=True)    # ultima riga dell'output del driver
    return 0 if status in ok_statuses else 1


if __name__ == "__main__":
    sys.exit(main())
