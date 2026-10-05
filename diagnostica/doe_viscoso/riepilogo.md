# DOE esplorativo accoppiamento viscoso / separazione

**ESPLORATIVO, NON VALIDATO**: manca il confronto con XFOIL e la convergenza di mesh.

| config | design ok/tot | dCL/dα 0–8° [/rad] | CL esce dalla linearità (> 2 % sotto la retta) | CL_max (α) | non convergenti / errori | cambi di segno di dCL dopo il max | tempo medio (max) [s] |
|---|---|---|---|---|---|---|---|
| D | 14/14 | 5.515 | mai fino a 18° | 1.8988 (18°) | nessuno | 0 su 0 intervalli | 38.5 (52.6) |
| C | 13/14 | 5.145 | a 10° | 1.7314 (18°) | 2°: status 2 | 0 su 0 intervalli | 91.1 (602.0) |
| CS | 14/14 | 5.033 | a 10° | 1.2663 (13°) | nessuno | 0 su 5 intervalli | 36.9 (41.1) |

Scostamento relativo di CL dalla retta 0–8° (per α > 8°):

- D: 10° -0.2 %, 11° -0.3 %, 12° -0.4 %, 13° -0.6 %, 14° -0.7 %, 15° -0.8 %, 16° -1.0 %, 17° -1.1 %, 18° -1.3 %
- C: 10° -4.1 %, 11° -7.8 %, 12° -8.8 %, 13° -9.2 %, 14° -9.5 %, 15° -8.3 %, 16° -6.6 %, 17° -4.2 %, 18° -3.9 %
- CS: 10° -3.9 %, 11° -4.3 %, 12° -0.9 %, 13° -5.1 %, 14° -19.7 %, 15° -25.4 %, 16° -30.4 %, 17° -34.3 %, 18° -37.9 %
