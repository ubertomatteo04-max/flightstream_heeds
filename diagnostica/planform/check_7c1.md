# 7C.1 – D_N non quantizzato (generato da check_7c1.py)

`configs/esplorativi/case_planform_taper_S.json` (S_half fisso, trim W = 147,15 N), driver v2.8.1 (schema 7): D0_N dal foglio dei carichi in NEWTONS, Di_N dal log, **D_N = Di_N + D0_N**. Colonne "7C": DOE della 7C (driver v2.7.0: D_N = CD·q·Sref, D0_N = CDo·q·Sref, 4 decimali).

| taper | status | α* [°] | Di_N [N] | D0_N [N] | D_N [N] | Di_N + D0_N − D_N | D0_N 7C | D_N 7C | D0 (N) − CDo·q·S [N] | tempo [s] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0,30 | 0 | 1,355 | 1,06080 | 5,3868 | 6,44760 | -8.9e-16 | 5,4016 | 6,4729 | −0,0148 (±0,0223) | 56,2 |
| 0,35 | 0 | 1,354 | 1,05777 | 5,3984 | 6,45617 | 0.0e+00 | 5,4016 | 6,4729 | −0,0032 (±0,0223) | 53,1 |
| 0,40 | 0 | 1,355 | 1,05777 | 5,4046 | 6,46237 | 0.0e+00 | 5,4016 | 6,4729 | 0,0030 (±0,0223) | 54,1 |
| 0,45 | 0 | 1,358 | 1,05978 | 5,4029 | 6,46268 | 0.0e+00 | 5,4016 | 6,4729 | 0,0013 (±0,0223) | 56,2 |
| 0,50 | 0 | 1,362 | 1,06308 | 5,4093 | 6,47238 | 0.0e+00 | 5,4016 | 6,4729 | 0,0077 (±0,0223) | 52,1 |

## Fit quadratico in taper (5 punti)

| grandezza | residuo massimo [%] | residuo RMS [%] | esito (< 0,1 %) |
|---|---|---|---|
| D_N | 0,0530 | 0,0301 | OK |
| Di_N | 0,0345 | 0,0233 | OK |
| D0_N | 0,0695 | 0,0398 | OK |
| D_N 7C (vecchio, CD·q·S) | 0,0000 | – | OK (confronto) |

Tempo per design (3 run di FlightStream con trim): 52,1–56,2 s, media 54,3 s.
**Esito: D_N liscio** (residuo del fit quadratico < 0,1 %).
