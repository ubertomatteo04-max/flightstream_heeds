#!/usr/bin/env python3
"""
preflight.py - Controlli prima di lanciare uno studio HEEDS (non lancia FlightStream).

    preflight.bat                      (stesso interprete Python di run_fs.bat)
    python preflight.py [--config case_semiala_fixed.json --config case_semiala_ccs.json]

Stampa OK / ERRORE per ogni voce:
  - nessun FlightStream.exe attivo;
  - l'interprete Python indicato in run_fs.bat esiste (e quello di heeds_report.bat per i grafici);
  - i JSON dei casi esistono e i percorsi interni risolvono (.fsm o CCS, eseguibile di FlightStream);
  - heeds_inputs\\<modalita'>\\results.txt ha lo schema_version e l'elenco di chiavi del driver;
  - un --dry-run lanciato con run_fs.bat in una cartella temporanea risponde con FS_DRIVER_RESULT.
Codice di uscita 0 se tutto e' OK, altrimenti 1. Solo libreria standard.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fs_driver  # noqa: E402
import geometry  # noqa: E402

DEFAULT_CONFIGS = ["case_semiala_fixed.json", "case_semiala_ccs.json", "case_semiala_planform.json"]
INPUTS = {"fixed": os.path.join("heeds_inputs", "fixed"), "ccs_wing": os.path.join("heeds_inputs", "ccs"),
          "ccs_planform": os.path.join("heeds_inputs", "planform"),
          # ccs_planform con geometry.size_by = "S_half" (benchmark SHERPA, HEEDS_SHERPA_BENCH.md)
          "ccs_planform_S": os.path.join("heeds_inputs", "planform_S")}


def inputs_key(cfg):
    """Cartella di heeds_inputs per il JSON: dalla modalita' e, per ccs_planform, da geometry.size_by."""
    mode = cfg["geometry"]["mode"]
    if mode == "ccs_planform" and cfg["geometry"].get("size_by", "c_root") == "S_half":
        return "ccs_planform_S"
    return mode


class Report:
    def __init__(self):
        self.errors = 0

    def item(self, ok, what, detail=""):
        self.errors += 0 if ok else 1
        print(f"{'OK    ' if ok else 'ERRORE'}  {what}" + (f": {detail}" if detail else ""), flush=True)
        return ok


def bat_variable(bat, name):
    """Valore di 'set "NAME=valore"' in un .bat (None se manca)."""
    if not os.path.isfile(bat):
        return None
    with open(bat, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(rf'\s*set\s+"{name}=(.*)"\s*$', line, re.IGNORECASE)
            if m:
                return m.group(1)
    return None


def check_flightstream(r):
    found = fs_driver.running_flightstream(fs_driver.DEFAULTS["run"]["flightstream_process_names"])
    r.item(not found, "nessun FlightStream.exe attivo",
           "nessuno" if not found else ", ".join(f"{nm} PID {pid}" for pid, nm in found)
           + " (chiudere la GUI o il processo orfano)")


def check_pythons(r):
    py = bat_variable(os.path.join(HERE, "run_fs.bat"), "PY")
    ok = bool(py) and os.path.isfile(py)
    r.item(ok, "Python di run_fs.bat", py or "riga set \"PY=...\" non trovata")
    if ok and os.path.normcase(os.path.abspath(py)) != os.path.normcase(os.path.abspath(sys.executable)):
        print(f"        (preflight gira con {sys.executable}: usare preflight.bat per lo stesso interprete)")
    hpy = bat_variable(os.path.join(HERE, "heeds_report.bat"), "HPY")
    hexe = os.path.join(hpy, "python.exe") if hpy else None
    r.item(bool(hexe) and os.path.isfile(hexe), "Python di heeds_report.bat (grafici)", hexe or "riga set \"HPY=...\" non trovata")


def check_config(r, path):
    """JSON leggibile e percorsi interni risolti. Restituisce la configurazione o None."""
    name = os.path.basename(path)
    if not r.item(os.path.isfile(path), f"{name} esiste", path):
        return None
    try:
        cfg = fs_driver.load_config(path)
    except Exception as e:
        r.item(False, f"{name} leggibile", f"{type(e).__name__}: {e}")
        return None
    mode = cfg["geometry"]["mode"]
    if mode == "fixed":
        geo = geometry.fixed_template(cfg)
        r.item(os.path.isfile(geo), f"{name}: template .fsm", geo)
    elif mode == "ccs_wing":
        geo = geometry._path(cfg, cfg["geometry"].get("base_ccs", ""))
        r.item(os.path.isfile(geo), f"{name}: CCS di partenza", geo)
    elif mode == "ccs_planform":
        geo = geometry._path(cfg, cfg["geometry"].get("profile", ""))
        r.item(os.path.isfile(geo), f"{name}: profilo (Selig)", geo)
    try:
        r.item(True, f"{name}: eseguibile FlightStream", fs_driver.find_exe(None, cfg))
    except ValueError as e:
        r.item(False, f"{name}: eseguibile FlightStream", str(e))
    return cfg


def check_inputs(r, mode):
    folder = os.path.join(HERE, INPUTS[mode])
    res = os.path.join(folder, "results.txt")
    if not r.item(os.path.isfile(res), f"{INPUTS[mode]}\\results.txt esiste", res):
        return
    with open(res, encoding="utf-8") as f:
        items = [tuple(x.strip() for x in ln.split("=", 1)) for ln in f if "=" in ln]
    sv = dict(items).get("schema_version")
    r.item(sv == str(fs_driver.SCHEMA_VERSION), f"{INPUTS[mode]}\\results.txt: schema_version",
           f"{sv} (driver: {fs_driver.SCHEMA_VERSION})")
    keys, want = [k for k, _ in items], fs_driver.result_keys()
    diff = "" if keys == want else (f"{len(keys)} chiavi contro {len(want)}; prima differenza: "
                                    + next((f"riga {i + 1} '{a}' invece di '{b}'" for i, (a, b) in enumerate(zip(keys, want)) if a != b),
                                           "lunghezza diversa"))
    r.item(keys == want, f"{INPUTS[mode]}\\results.txt: chiavi e ordine di RESULTS_SCHEMA", diff or f"{len(keys)} chiavi uguali")


def check_dry_run(r, path, mode):
    """--dry-run con il comando di HEEDS (run_fs.bat) in una cartella temporanea, con il params.txt di heeds_inputs."""
    name = os.path.basename(path)
    params = os.path.join(HERE, INPUTS[mode], "params.txt")
    tmp = tempfile.mkdtemp(prefix="preflight ")
    try:
        shutil.copy(params, os.path.join(tmp, "params.txt"))
        cmd = ([os.path.join(HERE, "run_fs.bat")] if os.name == "nt"
               else [sys.executable, os.path.join(HERE, "fs_driver.py")]) + ["--config", path, "--dry-run"]
        p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=120)
        lines = p.stdout.strip().splitlines()
        last = lines[-1] if lines else ""
        info = os.path.join(tmp, "run_info.txt")
        dry = os.path.isfile(info) and "dry-run" in open(info, encoding="utf-8").read()
        script = os.path.isfile(os.path.join(tmp, "fs_script.txt"))
        ok = last.startswith("FS_DRIVER_RESULT status=1 success=0") and dry and script and p.returncode == 1
        r.item(ok, f"{name}: --dry-run con run_fs.bat", f"'{last}', codice di uscita {p.returncode}"
               + ("" if script else ", fs_script.txt mancante") + ("" if dry else ", run_info senza 'dry-run'"))
    except Exception as e:
        r.item(False, f"{name}: --dry-run con run_fs.bat", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Controlli prima di lanciare uno studio HEEDS (non lancia FlightStream).")
    ap.add_argument("--config", action="append", help="JSON del caso (ripetibile; default: i due JSON della semiala)")
    a = ap.parse_args(argv)
    configs = [os.path.abspath(c) if os.path.isabs(c) or os.path.exists(c) else os.path.join(HERE, c)
               for c in (a.config or DEFAULT_CONFIGS)]
    print(f"preflight - fs_driver v{fs_driver.__version__}, schema_version {fs_driver.SCHEMA_VERSION}, Python {sys.executable}")
    r = Report()
    check_flightstream(r)
    check_pythons(r)
    for path in configs:
        cfg = check_config(r, path)
        if cfg is None:
            continue
        mode = inputs_key(cfg)
        if mode in INPUTS:
            check_inputs(r, mode)
            check_dry_run(r, path, mode)
    print("PREFLIGHT OK" if r.errors == 0 else f"PREFLIGHT: {r.errors} ERRORI")
    return 0 if r.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
