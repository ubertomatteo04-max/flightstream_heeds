"""Approfondimento: profili in corda a meta' apertura e Transition_marker nelle celle al tetto."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diag_bl import load, HCAP  # noqa: E402

for aoa in (4, 8, 12):
    d = load(aoa)
    cap = [r for r in d["rows"] if abs(r["H"] - HCAP) < 1e-3]
    trs = sorted(r["tr"] for r in cap)
    q = lambda p: trs[int(p * (len(trs) - 1))]
    print(f"\naoa {aoa}: Transition_marker nelle celle al tetto: min {trs[0]:.3f} q25 {q(.25):.3f} "
          f"mediana {q(.5):.3f} q75 {q(.75):.3f} max {trs[-1]:.3f}; tr<0.5: {sum(t < 0.5 for t in trs)}, "
          f"tr>=0.5: {sum(t >= 0.5 for t in trs)}")
    for side in ("dorso", "ventre"):
        c = [r for r in cap if r["side"] == side]
        if c:
            t = sorted(r["tr"] for r in c)
            print(f"   {side}: n {len(c)}, tr mediana {t[len(t) // 2]:.3f}, tr<0.5 {sum(v < 0.5 for v in t)}")
    # profilo a meta' apertura (fascia con eta ~ 0.5)
    strip = [r for r in d["rows"] if 0.49 <= r["eta"] <= 0.51 and r["side"] != "estremita"]
    for side in ("dorso", "ventre"):
        rr = sorted((r for r in strip if r["side"] == side), key=lambda r: r["xc"])
        print(f"   profilo {side} eta~0.5 (x/c, Cp, cf, H, tr, Vx):")
        pick = [r for r in rr if r["xc"] < 0.06] [:6] + [r for r in rr if r["xc"] >= 0.06][::6] + rr[-4:]
        seen = set()
        for r in pick:
            if r["i"] in seen:
                continue
            seen.add(r["i"])
            print(f"     {r['xc']:.3f} {r['Cp']:+.3f} {r['cf']:+.5f} {r['H']:.3f} {r['tr']:.3f} {r['Vx']:+.2f}")
