"""DOE esplorativo su aoa in tre configurazioni (D disaccoppiato, C accoppiato, CS accoppiato + separazione):
grafici sovrapposti e riepilogo. ESPLORATIVO, NON VALIDATO (manca il confronto con XFOIL e la convergenza
di mesh).

Uso (serve matplotlib: Python di HEEDS, come heeds_report.bat):
    set PYTHONPATH=C:\\Program Files\\Siemens\\SimcenterHEEDS-2604.0\\MDO\\Python3\\Lib\\siemens
    "C:\\Program Files\\Siemens\\SimcenterHEEDS-2604.0\\MDO\\Python3\\python.exe" diagnostica\\plot_viscous_doe.py
        --doe D=mock_runs_visc_D --doe C=mock_runs_visc_C --doe CS=mock_runs_visc_CS --out <cartella>

Ogni --doe e' una cartella di heeds_mock.py con summary.csv. Scrive CL_alpha.png, polare.png, LD_alpha.png,
CMy_alpha.png, separazione_alpha.png e riepilogo.md.
"""
import argparse
import csv
import math
import os

COLORS = {"D": "tab:blue", "C": "tab:green", "CS": "tab:red"}
LABELS = {"D": "D disaccoppiato", "C": "C accoppiato", "CS": "CS accoppiato + separazione"}


def num(t):
    try:
        v = float(t)
    except (TypeError, ValueError):
        return None
    return None if v == -999 or not math.isfinite(v) else v


def load(folder):
    with open(os.path.join(folder, "summary.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["_aoa"] = num(r.get("aoa"))
    return sorted(rows, key=lambda r: r["_aoa"])


def linear_fit(pts):
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    a = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    return a, my - a * mx


def analyse(name, rows, tol=0.02):
    """Uscita dalla linearita' (CL sotto la retta 0-8 gradi di oltre tol relativo), CL_max, punti non
    convergenti, tempo medio, rumore dopo il massimo (cambi di segno di dCL tra punti successivi)."""
    ok = [r for r in rows if num(r.get("status")) == 0 and num(r.get("CL")) is not None]
    bad = [(r["_aoa"], r.get("status"), r.get("reason", "")) for r in rows if num(r.get("status")) != 0]
    out = {"name": name, "n": len(rows), "ok": len(ok), "bad": bad}
    lin = [(r["_aoa"], num(r["CL"])) for r in ok if r["_aoa"] <= 8]
    if len(lin) >= 2:
        a, b = linear_fit(lin)
        out["slope_rad"] = a * 180 / math.pi
        dev = [(r["_aoa"], num(r["CL"]) / (a * r["_aoa"] + b) - 1) for r in ok if r["_aoa"] > 8]
        first = next((x for x, d in dev if d < -tol), None)
        out["nonlin_aoa"] = first
        out["dev"] = dev
    if ok:
        m = max(ok, key=lambda r: num(r["CL"]))
        out["clmax"], out["aoa_clmax"] = num(m["CL"]), m["_aoa"]
        after = [num(r["CL"]) for r in ok if r["_aoa"] >= m["_aoa"]]
        d = [b - a for a, b in zip(after, after[1:])]
        out["sign_changes_after_max"] = sum(1 for p, q in zip(d, d[1:]) if p * q < 0)
        out["n_after_max"] = len(after) - 1
    times = [num(r.get("wall_s")) for r in rows if num(r.get("wall_s")) is not None]
    out["t_mean"] = sum(times) / len(times) if times else None
    out["t_max"] = max(times) if times else None
    return out


def plots(data, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def series(rows, key):
        return [(r["_aoa"], num(r.get(key))) for r in rows if num(r.get("status")) == 0 and num(r.get(key)) is not None]

    def fig(fname, title, ylabel, key, xkey="aoa"):
        f, ax = plt.subplots(figsize=(7.5, 5))
        for name, rows in data.items():
            if xkey == "aoa":
                pts = series(rows, key)
                ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=4, lw=1.2, color=COLORS.get(name), label=LABELS.get(name, name))
            else:
                pts = [(num(r.get(xkey)), num(r.get(key))) for r in rows if num(r.get("status")) == 0
                       and num(r.get(xkey)) is not None and num(r.get(key)) is not None]
                ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=4, lw=1.2, color=COLORS.get(name), label=LABELS.get(name, name))
        ax.set_xlabel("aoa [deg]" if xkey == "aoa" else xkey)
        ax.set_ylabel(ylabel)
        ax.set_title(title + " — ESPLORATIVO, non validato", fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.legend()
        f.tight_layout()
        f.savefig(os.path.join(out, fname), dpi=150)
        plt.close(f)

    fig("CL_alpha.png", "CL in funzione dell'incidenza", "CL", "CL")
    fig("polare.png", "Polare CL–CD", "CL", "CL", xkey="CD")
    fig("LD_alpha.png", "Efficienza in funzione dell'incidenza", "L/D", "L_over_D")
    fig("CMy_alpha.png", "CMy in funzione dell'incidenza", "CMy", "CMy")

    f, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, key, yl in zip(axs, ("sep_frac_up_le", "x_sep_up", "sep_marker_frac_up"),
                           ("sep_frac_up_le (area dorso, x/c < 0,15)", "x_sep_up (1 = nessuna separazione)",
                            "sep_marker_frac_up (Separation_marker >= 0,5)")):
        for name, rows in data.items():
            pts = series(rows, key)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", ms=4, lw=1.2, color=COLORS.get(name), label=LABELS.get(name, name))
        ax.set_xlabel("aoa [deg]")
        ax.set_ylabel(yl)
        ax.grid(True, alpha=0.3)
    axs[0].legend()
    f.suptitle("Indicatori di separazione — ESPLORATIVO, non validato", fontsize=11)
    f.tight_layout()
    f.savefig(os.path.join(out, "separazione_alpha.png"), dpi=150)
    plt.close(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doe", action="append", required=True, help="NOME=cartella con summary.csv (ripetibile)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data = {}
    for item in a.doe:
        name, folder = item.split("=", 1)
        data[name] = load(folder)
    md = ["# DOE esplorativo accoppiamento viscoso / separazione", "",
          "**ESPLORATIVO, NON VALIDATO**: manca il confronto con XFOIL e la convergenza di mesh.", "",
          "| config | design ok/tot | dCL/dα 0–8° [/rad] | CL esce dalla linearità (> 2 % sotto la retta) | CL_max (α) | non convergenti / errori | cambi di segno di dCL dopo il max | tempo medio (max) [s] |",
          "|---|---|---|---|---|---|---|---|"]
    for name, rows in data.items():
        r = analyse(name, rows)
        bad = "; ".join(f"{x:g}°: status {s}" for x, s, _ in r["bad"]) or "nessuno"
        md.append(f"| {name} | {r['ok']}/{r['n']} | {r.get('slope_rad', float('nan')):.3f} | "
                  f"{'a ' + format(r['nonlin_aoa'], 'g') + '°' if r.get('nonlin_aoa') is not None else 'mai fino a 18°'} | "
                  f"{r.get('clmax', float('nan')):.4f} ({r.get('aoa_clmax', float('nan')):g}°) | {bad} | "
                  f"{r.get('sign_changes_after_max', 0)} su {r.get('n_after_max', 0)} intervalli | "
                  f"{r['t_mean']:.1f} ({r['t_max']:.1f}) |")
    md += ["", "Scostamento relativo di CL dalla retta 0–8° (per α > 8°):", ""]
    for name, rows in data.items():
        r = analyse(name, rows)
        md.append(f"- {name}: " + ", ".join(f"{x:g}° {100 * d:+.1f} %" for x, d in r.get("dev", [])))
    with open(os.path.join(a.out, "riepilogo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    plots(data, a.out)
    print("grafici in", a.out)


if __name__ == "__main__":
    main()
