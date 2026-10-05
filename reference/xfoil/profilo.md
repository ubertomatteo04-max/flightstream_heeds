# Profilo della semiala per XFOIL (vespa.dat)

Fonte: `..\semiala_ccs_U120_V64_blended.csv`, prima CrossSection (y = 0 m; quella a y = 2,64 m e' uguale).
Punti: 200 (TE dorso -> LE -> TE ventre), 100 sul dorso prima del LE.

| grandezza | valore |
|---|---|
| LE (x, z) [m] | 0.002107, 0.015733 |
| TE medio (x, z) [m] | 0.347200, 0.015957 |
| corda c [m] | 0.345093 (Lref dei JSON 0,345091) |
| inclinazione corda rispetto a x | +0.0373 deg (non ruotata: alfa XFOIL = alfa geometrico FS) |
| spessore al TE (tozzo) | 0.652 % c (2.249 mm) |
| spessore massimo | 12.176 % c a x/c = 0.304 |
| curvatura massima | 1.887 % c a x/c = 0.410 |

## Controllo con il VTK fixed (`mock_runs_visc_D\Design_003\surface.vtk`)

Stazione di punti a y = 1.3200 m (eta = 0.500), 118 punti.
- scarto massimo (distanza normale / c) su tutta la sezione: -0.00326 a x/c = 1.0000 (ventre)
- scarto massimo (distanza normale / c) per x/c < 0,95: -0.001609 a x/c = 0.9486 (ventre)
- scarto massimo (distanza normale / c) per x/c < 0,8: -0.000076 a x/c = 0.0014 (ventre); lo scarto supera 2e-4 da x/c = 0.910 (raccordo del TE)
- TE della mesh FlightStream: x/c = 1.0000, z/c = 0.00065 (TE medio CCS z/c = 0.00065): la mesh chiude il TE (`Blend_trailing_edges` nel CCS), XFOIL usa invece il TE tozzo.
