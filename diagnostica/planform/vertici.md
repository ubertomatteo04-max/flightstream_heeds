# ccs_planform – test sugli 8 vertici (Parte 7A, 2026-10-06)

`python heeds_mock.py --config case_semiala_planform.json --var c_root=0.2760730344,0.5521460688 --var taper=0.4,1.0
--var twist_tip_deg=-5,1 --out diagnostica/planform/runs/vertici` (run_fs.bat, configurazione D, α = 4°, V = 20 m/s,
b_half = b0 = 2,64 m; c0 = 0,345091 m). Pannelli: **15 262 in tutti i design** (uguale alla baseline).

| design | c_root / c0 | taper | twist tip [°] | status | iter. | tempo [s] | Sref [m²] | AR | Re (MAC) | CL | CDi | CDo | CMy | L_N [N] | D_N [N] | cl_sec_max (η) | ∫cl·c vs CL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0,8 | 0,4 | −5 | 0 | 89 | 18,8 | 1,0204 | 27,3 | 282 277 | 0,4123 | 0,0027 | 0,0132 | −0,1961 | 103,1 | 3,97 | 0,550 (0,06) | −0,39 % |
| 2 | 0,8 | 0,4 | +1 | 0 | 89 | 19,0 | 1,0204 | 27,3 | 282 277 | 0,6844 | 0,0058 | 0,0148 | −0,2929 | 171,1 | 5,15 | 0,735 (0,75) | −0,43 % |
| 3 | 0,8 | 1,0 | −5 | 0 | 90 | 17,9 | 1,4577 | 19,1 | 379 988 | 0,3641 | 0,0025 | 0,0124 | −0,1459 | 130,0 | 5,32 | 0,574 (0,02) | −0,42 % |
| 4 | 0,8 | 1,0 | +1 | 0 | 91 | 17,9 | 1,4577 | 19,1 | 379 988 | 0,6444 | 0,0082 | 0,0134 | −0,2190 | 230,1 | 7,71 | 0,687 (0,47) | −0,50 % |
| 5 | 1,6 | 0,4 | −5 | 0 | 91 | 17,9 | 2,0407 | 13,7 | 564 554 | 0,3746 | 0,0042 | 0,0120 | −0,1791 | 187,3 | 8,10 | 0,472 (0,06) | −0,43 % |
| 6 | 1,6 | 0,4 | +1 | 0 | 92 | 16,8 | 2,0407 | 13,7 | 564 554 | 0,6209 | 0,0094 | 0,0124 | −0,2647 | 310,4 | 10,90 | 0,673 (0,72) | −0,46 % |
| 7 | 1,6 | 1,0 | −5 | 0 | 92 | 16,8 | 2,9153 | 9,6 | 759 976 | 0,3283 | 0,0039 | 0,0115 | −0,1331 | 234,5 | 11,00 | 0,502 (0,02) | −0,49 % |
| 8 | 1,6 | 1,0 | +1 | 0 | 93 | 16,8 | 2,9153 | 9,6 | 759 976 | 0,5666 | 0,0118 | 0,0111 | −0,1923 | 404,7 | 16,36 | 0,624 (0,29) | −0,55 % |

Controlli di plausibilità: lo svergolamento negativo (washout) abbassa CL e sposta il massimo del cl di sezione verso la
radice; con +1° il massimo va verso l'estremità (η 0,3–0,75); a pari corda la rastremazione 0,4 alza CL·AR rispetto a CDi
(efficienza di apertura e ≈ 0,94 nel design 2 contro ≈ 0,84 nel 4, stima da CL²/(π AR CDi) con CDi a 4 decimali).
Re 2,8·10⁵ nei design 1–2: ancora più sotto il campo del modello TRANSITIONAL (5·10⁵–1,5·10⁶).
