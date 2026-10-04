#!/usr/bin/env python3
"""
heeds_report.py - Riepilogo di uno studio HEEDS (o di un DOE di heeds_mock.py) letto direttamente dai
results.txt delle cartelle dei design, senza usare l'export di HEEDS.

    python heeds_report.py --study "C:\\Users\\UtenteLocale\\Desktop\\heeds\\semiala_fixed\\semiala_Study_2"
    heeds_report.bat --study "..."        (stesso comando con il Python di HEEDS, che ha matplotlib)

Cerca ogni results.txt sotto --study in una cartella di design (Design1, Design_001, Design_1\\Analysis_1,
Design3-ERROR, ...). Scrive in --out (default <study>\\report):
    report.csv     un design per riga (solo status = 0), ordinato per la variabile --x (default aoa)
    scartati.txt   i design con status diverso da 0 o results.txt illeggibile, con il motivo
    CL_alpha.png   CL in funzione di --x, con la retta di pendenza --slope [1/rad] e i punti del DOE mock
    LD_alpha.png   L/D in funzione di --x, con i punti del DOE mock
    verifica.md    solo con --check-against-mock: confronto design per design con il DOE mock (CL, CD,
                   CMy, L_over_D, tolleranza relativa --rtol), numero di design (--expect-n), valori di
                   aoa (--expect-aoa), design in errore, nessun FlightStream.exe attivo; ultima riga
                   VERIFICA OK / VERIFICA FALLITA e codice di uscita 0 / 1
I grafici richiedono matplotlib: se manca, si scrivono solo CSV ed elenco degli scartati.
Esempio di verifica dello sweep HEEDS su aoa:
    heeds_report.bat --study "...\\semiala_Study_2" --check-against-mock mock_runs\\summary.csv
                     --expect-n 7 --expect-aoa 0,2,4,6,8,10,12
Il DOE mock (summary.csv di heeds_mock.py) si indica con --mock; per default si usa
<cartella di questo file>\\mock_runs\\summary.csv se esiste.
Solo libreria standard (+ matplotlib per i grafici). Python >= 3.8.
"""
import argparse
import csv
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN_DIR = re.compile(r"^Design_?(\d+)(-ERROR)?$", re.IGNORECASE)
SLOPE_HELMBOLD = 5.515          # 1/rad: Helmbold, AR 15,3 (coincide con il DOE fixed 0-8 gradi)


def read_results(path):
    """results.txt -> lista ordinata di (chiave, testo del valore)."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "=" in line:
                k, v = (x.strip() for x in line.split("=", 1))
                out.append((k, v))
    return out


def number(text):
    """Valore numerico di results.txt; -999 e testo non numerico -> None."""
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return None if v == -999 or not math.isfinite(v) else v


def design_name(path, study):
    """Nome del design: la cartella piu' vicina al file che si chiama Design<N> (anche -ERROR)."""
    parts = os.path.relpath(os.path.dirname(path), study).split(os.sep)
    for part in reversed(parts):
        if DESIGN_DIR.match(part):
            return part
    return None


def find_designs(study):
    """[(nome del design, percorso di results.txt)] sotto la cartella dello studio."""
    found = []
    for root, dirs, files in os.walk(study):
        dirs[:] = [d for d in dirs if d.lower() not in ("report",)]
        if "results.txt" in files:
            path = os.path.join(root, "results.txt")
            name = design_name(path, study)
            if name:
                found.append((name, path))

    def key(item):
        m = DESIGN_DIR.match(item[0])
        return (int(m.group(1)), item[0])
    return sorted(found, key=key)


def collect(study, xkey):
    """Legge tutti i design: (buoni, scartati, chiavi nell'ordine dei file). Un design in una cartella
    Design<N>-ERROR e' sempre scartato (HEEDS l'ha marcato come errore), qualunque sia lo status."""
    good, bad, keys = [], [], []
    for name, path in find_designs(study):
        try:
            items = read_results(path)
        except OSError as e:
            bad.append((name, path, f"results.txt illeggibile: {e}"))
            continue
        res = dict(items)
        keys += [k for k, _ in items if k not in keys]
        status = number(res.get("status"))
        if name.upper().endswith("-ERROR"):
            bad.append((name, path, f"cartella -ERROR (design in errore per HEEDS), status = {res.get('status', 'mancante')}"))
            continue
        if status is None or int(status) != 0:
            reason = f"status = {res.get('status', 'mancante')}"
            info = os.path.join(os.path.dirname(path), "run_info.txt")
            if os.path.isfile(info):
                with open(info, encoding="utf-8", errors="replace") as f:
                    notes = [ln[2:].strip() for ln in f if ln.startswith("- ")]
                if notes:
                    reason += f" ({notes[-1]})"
            bad.append((name, path, reason))
            continue
        if number(res.get(xkey)) is None:
            bad.append((name, path, f"{xkey} mancante in results.txt"))
            continue
        good.append({"design": name, "path": path, **res})
    good.sort(key=lambda r: number(r[xkey]))
    return good, bad, keys


def read_mock(path, xkey):
    """Punti (x, CL, L/D) dal summary.csv di heeds_mock.py, solo status = 0."""
    pts = []
    if not path or not os.path.isfile(path):
        return pts
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            x, cl, ld = (number(r.get(k)) for k in (xkey, "CL", "L_over_D"))
            if number(r.get("status")) == 0 and x is not None and cl is not None:
                pts.append((x, cl, ld))
    return sorted(pts)


CHECK_KEYS = ["CL", "CD", "CMy", "L_over_D"]


def read_mock_rows(path, xkey):
    """summary.csv di heeds_mock.py -> {x: riga} per i design a status 0."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            x = number(r.get(xkey))
            if number(r.get("status")) == 0 and x is not None:
                out[x] = r
    return out


def lift_slope(rows, xkey, x_max=8.0):
    """dCL/dx [1/rad] ai minimi quadrati sui design con 0 <= x <= x_max; None con meno di 2 punti."""
    pts = [(math.radians(number(r[xkey])), number(r.get("CL"))) for r in rows
           if number(r.get("CL")) is not None and 0.0 <= number(r[xkey]) <= x_max]
    if len(pts) < 2:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx > 0 else None


def flightstream_running():
    """Processi FlightStream.exe attivi [(pid, nome)], con la funzione del driver; None se non verificabile."""
    try:
        sys.path.insert(0, HERE)
        import fs_driver
        return fs_driver.running_flightstream(["FlightStream.exe"])
    except Exception:
        return None


def verify(rows, bad, xkey, mock_path, rtol, expect_n, expect_x):
    """Verifica dello studio contro il DOE mock e i valori attesi. Restituisce (ok, righe Markdown, motivi)."""
    reasons, md = [], []
    mock = read_mock_rows(mock_path, xkey)
    md += [f"Riferimento: `{mock_path}` ({len(mock)} punti a status 0); tolleranza relativa {rtol:g} su "
           + ", ".join(CHECK_KEYS) + ".", "",
           f"| {xkey} | CL HEEDS | CL mock | diff CL (rel.) | max diff rel. CD, CMy, L/D | esito |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        x = number(r[xkey])
        m = next((v for k, v in mock.items() if abs(k - x) < 1e-6), None)
        if m is None:
            md.append(f"| {r[xkey]} | {r.get('CL')} | – | – | – | FAIL (non nel mock) |")
            reasons.append(f"{xkey} = {r[xkey]} non presente nel DOE mock")
            continue
        rel = {}
        for k in CHECK_KEYS:
            h, ref = number(r.get(k)), number(m.get(k))
            rel[k] = abs(h - ref) / max(abs(ref), 1e-12) if h is not None and ref is not None else math.inf
        ok = all(v <= rtol for v in rel.values())
        if not ok:
            reasons.append(f"{xkey} = {r[xkey]}: " + ", ".join(f"{k} diff {v:.2e}" for k, v in rel.items() if v > rtol))
        others = max(rel[k] for k in CHECK_KEYS if k != "CL")
        md.append(f"| {r[xkey]} | {r.get('CL')} | {m.get('CL')} | {rel['CL']:.1e} | {others:.1e} | {'PASS' if ok else 'FAIL'} |")
    md.append("")
    found = len(rows) + len(bad)
    if expect_n is not None:
        line = f"design trovati {found} (validi {len(rows)}), attesi {expect_n}"
        md.append(f"- {'OK  ' if found == expect_n and len(rows) == expect_n else 'FAIL'} {line}")
        if not (found == expect_n and len(rows) == expect_n):
            reasons.append(line)
    if expect_x is not None:
        got = sorted(number(r[xkey]) for r in rows)
        same = len(got) == len(expect_x) and all(abs(a - b) < 1e-6 for a, b in zip(got, sorted(expect_x)))
        line = f"{xkey} trovati {[f'{v:g}' for v in got]}, attesi {[f'{v:g}' for v in sorted(expect_x)]}"
        md.append(f"- {'OK  ' if same else 'FAIL'} {line}")
        if not same:
            reasons.append(f"valori di {xkey} diversi dagli attesi")
    err = [n for n, _, _ in bad]
    md.append(f"- {'OK  ' if not err else 'FAIL'} design in errore o scartati: {err or 'nessuno'}")
    if err:
        reasons.append(f"design in errore o scartati: {', '.join(err)}")
    fs = flightstream_running()
    if fs is None:
        md.append("- ??   FlightStream attivo: non verificabile su questo sistema")
    else:
        md.append(f"- {'OK  ' if not fs else 'FAIL'} FlightStream.exe attivi: {fs or 'nessuno'}")
        if fs:
            reasons.append(f"FlightStream.exe ancora attivo: {fs}")
    return not reasons, md, reasons


def write_csv(path, rows, keys, xkey):
    cols = ["design", xkey] + [k for k in keys if k != xkey] + ["path"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def slope_line(points, slope, x_max_fit=8.0):
    """Retta CL = CL0 + slope * x[rad] con la pendenza fissata; CL0 dal minimo quadrato sui punti con
    x <= x_max_fit (zona lineare). Restituisce CL0, oppure None se non ci sono punti."""
    sel = [(x, cl) for x, cl in points if x <= x_max_fit]
    if not sel:
        return None
    return sum(cl - slope * math.radians(x) for x, cl in sel) / len(sel)


def make_plots(out, rows, mock, xkey, slope, label):
    """CL-alpha e L/D-alpha in PNG. Restituisce l'elenco dei file scritti ([] senza matplotlib)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib non disponibile: grafici non creati (usa heeds_report.bat, Python di HEEDS).")
        return []
    xs = [number(r[xkey]) for r in rows]
    cls = [number(r.get("CL")) for r in rows]
    lds = [number(r.get("L_over_D")) for r in rows]
    written = []

    fig, ax = plt.subplots(figsize=(7, 5))
    pts = [(x, c) for x, c in zip(xs, cls) if c is not None] + [(x, c) for x, c, _ in mock]
    cl0 = slope_line(pts, slope)
    if cl0 is not None:
        allx = [p[0] for p in pts]
        xx = [min(allx + [0.0]), max(allx + [12.0])]
        ax.plot(xx, [cl0 + slope * math.radians(x) for x in xx], "--", color="0.45", lw=1.2,
                label=f"retta {slope:g} /rad (CL0 = {cl0:.4f})")
    if mock:
        ax.plot([p[0] for p in mock], [p[1] for p in mock], "s", ms=9, mfc="none", mec="tab:orange",
                label="DOE mock (heeds_mock.py)")
    ax.plot(xs, cls, "o-", color="tab:blue", ms=6, label=label)
    ax.set_xlabel(f"{xkey} [deg]")
    ax.set_ylabel("CL")
    ax.set_title("CL in funzione dell'incidenza")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = os.path.join(out, "CL_alpha.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    fig, ax = plt.subplots(figsize=(7, 5))
    mld = [(x, ld) for x, _, ld in mock if ld is not None]
    if mld:
        ax.plot([p[0] for p in mld], [p[1] for p in mld], "s", ms=9, mfc="none", mec="tab:orange",
                label="DOE mock (heeds_mock.py)")
    ax.plot(xs, lds, "o-", color="tab:green", ms=6, label=label)
    ax.set_xlabel(f"{xkey} [deg]")
    ax.set_ylabel("L/D")
    ax.set_title("Efficienza in funzione dell'incidenza")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    p = os.path.join(out, "LD_alpha.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description="Riepilogo di uno studio HEEDS dai results.txt dei design.")
    ap.add_argument("--study", required=True, help="cartella dello studio HEEDS (o del DOE mock)")
    ap.add_argument("--out", help="cartella dei risultati (default: <study>\\report)")
    ap.add_argument("--mock", help="summary.csv di heeds_mock.py da sovrapporre (default: mock_runs\\summary.csv)")
    ap.add_argument("--no-mock", action="store_true", help="non sovrapporre i punti del DOE mock")
    ap.add_argument("--x", default="aoa", help="variabile in ascissa (default: aoa)")
    ap.add_argument("--slope", type=float, default=SLOPE_HELMBOLD, help="pendenza della retta [1/rad]")
    ap.add_argument("--label", default="studio HEEDS", help="etichetta dei punti dello studio nei grafici")
    ap.add_argument("--check-against-mock", metavar="SUMMARY_CSV",
                    help="verifica: confronta CL, CD, CMy, L_over_D con il DOE mock allo stesso --x; "
                         "scrive verifica.md e esce con 1 se la verifica fallisce")
    ap.add_argument("--rtol", type=float, default=1e-4, help="tolleranza relativa della verifica (default 1e-4)")
    ap.add_argument("--expect-n", type=int, help="verifica: numero di design atteso")
    ap.add_argument("--expect-aoa", help="verifica: valori attesi di --x, es. 0,2,4,6,8,10,12")
    a = ap.parse_args(argv)

    study = os.path.abspath(a.study)
    if not os.path.isdir(study):
        print(f"cartella dello studio non trovata: {study}")
        return 1
    out = os.path.abspath(a.out or os.path.join(study, "report"))
    os.makedirs(out, exist_ok=True)
    rows, bad, keys = collect(study, a.x)
    mock_path = None if a.no_mock else (a.mock or a.check_against_mock
                                        or os.path.join(HERE, "mock_runs", "summary.csv"))
    mock = read_mock(mock_path, a.x)
    slope = lift_slope(rows, a.x)

    write_csv(os.path.join(out, "report.csv"), rows, keys, a.x)
    with open(os.path.join(out, "scartati.txt"), "w", encoding="utf-8") as f:
        for name, path, reason in bad:
            f.write(f"{name}\t{reason}\t{path}\n")

    print(f"Studio: {study}")
    print(f"Design validi (status 0): {len(rows)}; scartati: {len(bad)}")
    for name, _, reason in bad:
        print(f"  SCARTATO {name}: {reason}")
    if rows:
        print(f"  {'design':>12s} {a.x:>8s} {'CL':>8s} {'CD':>8s} {'CMy':>8s} {'L/D':>8s}")
        for r in rows:
            print(f"  {r['design']:>12s} " + " ".join(f"{r.get(k, ''):>8s}" for k in (a.x, "CL", "CD", "CMy", "L_over_D")))
    print(f"DOE mock sovrapposto: {len(mock)} punti" + (f" ({mock_path})" if mock else ""))
    if slope is not None:
        print(f"dCL/d{a.x} (0-8 gradi, minimi quadrati): {slope:.4f} /rad = {math.radians(1) * slope:.5f} /deg")
    files = make_plots(out, rows, mock, a.x, a.slope, a.label) if rows else []
    written = [os.path.join(out, "report.csv"), os.path.join(out, "scartati.txt")] + files
    rc = 0
    if a.check_against_mock:
        expect_x = [float(v) for v in a.expect_aoa.split(",")] if a.expect_aoa else None
        ok, md, reasons = verify(rows, bad, a.x, os.path.abspath(a.check_against_mock), a.rtol, a.expect_n, expect_x)
        verdict = "VERIFICA OK" if ok else "VERIFICA FALLITA: " + "; ".join(reasons)
        head = [f"# Verifica dello studio `{os.path.basename(study)}`", "", f"Cartella: `{study}`", ""]
        tail = ["", f"dCL/d{a.x} (0–8°): " + (f"{slope:.4f} /rad" if slope is not None else "non calcolabile"),
                "", f"**{verdict}**", ""]
        p = os.path.join(out, "verifica.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(head + md + tail))
        written.append(p)
        print("\n".join(md))
        print(verdict)
        rc = 0 if ok else 1
    print("Scritti:", ", ".join(written))
    return rc


if __name__ == "__main__":
    sys.exit(main())
