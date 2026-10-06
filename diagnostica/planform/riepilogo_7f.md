# 7F – clmax di XFOIL attivo (generato da riepilogo_7f.py)

`case_semiala_planform.json`: `mission.clmax_file = xfoil/clmax_vs_Re.csv` (XFOIL 6.99, Ncrit 9; Re = V_min·c/ν, V_min 12 m/s), mesh U120 × V64, trim W = 147,15 N a 20 m/s, configurazione D. Margine = CLmax_wing / CL_req − 1; CL_req = W / (½ ρ V_min² Sref).

## Baseline e 8 vertici della 7B (b_half 2,64 m)

| design | c_root [m] | taper | twist [°] | Sref [m²] | status | α* [°] | CLmax_wing | CL_req | margine | η_stall | D_N [N] | ammissibile (margine ≥ 0) | η_stall ≤ 0,6 | tempo [s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0,3451 | 1,00 | 0 | 1,8221 | 0 | 1,440 | 1,2193 | 0,9156 | 33,2 % | 0,059 | 6,5589 | sì | sì | – |
| Design_001 | 0,2761 | 0,40 | −5 | 1,0204 | 0 | 5,639 | 1,2208 | 1,6351 | −25,3 % | 0,098 | 4,7542 | **no** | sì | 59,4 |
| Design_002 | 0,2761 | 0,40 | 1 | 1,0204 | 0 | 3,104 | 1,2403 | 1,6351 | −24,1 % | 0,747 | 4,6126 | **no** | no | 59,3 |
| Design_003 | 0,2761 | 1,00 | −5 | 1,4577 | 0 | 4,476 | 1,0637 | 1,1445 | −7,1 % | 0,020 | 5,5908 | **no** | sì | 58,1 |
| Design_004 | 0,2761 | 1,00 | 1 | 1,4577 | 0 | 1,677 | 1,2492 | 1,1445 | 9,1 % | 0,328 | 5,5146 | sì | sì | 59,3 |
| Design_005 | 0,5521 | 0,40 | −5 | 2,0407 | 0 | 3,175 | 1,2809 | 0,8175 | 56,7 % | 0,290 | 7,4150 | sì | sì | 76,2 |
| Design_006 | 0,5521 | 0,40 | 1 | 2,0407 | 0 | 0,637 | 1,2574 | 0,8175 | 53,8 % | 0,721 | 7,0329 | sì | no | 66,9 |
| Design_007 | 0,5521 | 1,00 | −5 | 2,9153 | 0 | 2,613 | 1,0975 | 0,5723 | 91,8 % | 0,020 | 9,7141 | sì | sì | 69,1 |
| Design_008 | 0,5521 | 1,00 | 1 | 2,9153 | 0 | −0,100 | 1,2337 | 0,5723 | 115,6 % | 0,020 | 9,4806 | sì | sì | 60,3 |

## Corda minima della rettangolare non svergolata (taper 1, twist 0, b_half 2,64 m)

| design | c_root [m] | taper | twist [°] | Sref [m²] | status | α* [°] | CLmax_wing | CL_req | margine | η_stall | D_N [N] | ammissibile (margine ≥ 0) | η_stall ≤ 0,6 | tempo [s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Design_001 | 0,2400 | 1,00 | 0 | 1,2672 | 0 | 2,671 | 1,2350 | 1,3166 | −6,2 % | 0,059 | 5,0657 | **no** | sì | 64,4 |
| Design_002 | 0,2600 | 1,00 | 0 | 1,3728 | 0 | 2,361 | 1,2307 | 1,2153 | 1,3 % | 0,059 | 5,2424 | sì | sì | 65,5 |
| Design_003 | 0,2800 | 1,00 | 0 | 1,4784 | 0 | 2,094 | 1,2258 | 1,1285 | 8,6 % | 0,020 | 5,5138 | sì | sì | 63,4 |
| Design_004 | 0,3000 | 1,00 | 0 | 1,5840 | 0 | 1,863 | 1,2217 | 1,0533 | 16,0 % | 0,059 | 5,9278 | sì | sì | 57,2 |

**Corda minima ammissibile ≈ 0,2566 m** (margine = 0 per interpolazione lineare fra i run): Sref minima ≈ **1,355 m²** (ala intera; AR 20,6), cioè −25,6 % rispetto alla baseline (1,822 m²).
