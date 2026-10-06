# 7E – convergenza di mesh di ccs_planform con trim (generato da gci_7e.py)

`configs/esplorativi/case_planform_mesh7e_<mesh>.json` (= case_planform_taper_S.json con il solo blocco mesh cambiato), S_half 0,911041, b_half 2,64, twist 0, trim W = 147,15 N, configurazione D. CLmax_wing con clmax **segnaposto**. Celik et al. (2008): r = rapporto degli intervalli nella direzione raffinata, Fs = 1,25; E = Fs·|φ − φ_ext|/|φ_ext| = errore stimato di ogni livello.

| mesh | tempo taper 1 / 0,38 [s] | status |
|---|---|---|
| U120 × V43 | 42,6 / 42,7 | 0 / 0 |
| U120 × V64 (attuale) | 53,1 / 54,0 | 0 / 0 |
| U120 × V96 | 81,1 / 78,0 | 0 / 0 |
| U80 × V64 | 38,5 / 38,5 | 0 / 0 |
| U180 × V64 | 105,7 / 109,0 | 0 / 0 |

## Serie apertura (U 120), taper 1,00 (r21 = 1,508, r32 = 1,500)

| grandezza | coarse | medium | fine | convergenza | p | φ_ext | GCI_fine [%] | E coarse / medium / fine [%] |
|---|---|---|---|---|---|---|---|---|
| Di_N | 1,13277 | 1,13727 | 1,14178 | divergente | 0,03 | 1,55788 | 45,554 | 34,110 / 33,748 / 33,387 |
| D0_N | 5,4214 | 5,4216 | 5,4121 | divergente | 9,28 | 5,4119 | 0,005 | 0,220 / 0,224 / 0,005 |
| D_N | 6,55417 | 6,55887 | 6,55388 | divergente | 0,14 | 6,47246 | 1,553 | 1,578 / 1,669 / 1,572 |
| e_span | 0,89111 | 0,88752 | 0,88412 | monotona | 0,17 | 0,83569 | 6,847 | 8,288 / 7,752 / 7,244 |
| alpha_trim | 1,4106 | 1,4395 | 1,4435 | monotona | 4,88 | 1,4442 | 0,054 | 2,909 / 0,402 / 0,054 |
| CLmax_wing | 1,0900 | 1,0858 | 1,0844 | monotona | 2,68 | 1,0837 | 0,082 | 0,728 / 0,245 / 0,082 |
| M_root_Nm | 89,8322 | 89,6064 | 89,6518 | oscillante | 3,95 | 89,6630 | 0,016 | 0,236 / 0,079 / 0,016 |

## Serie apertura (U 120), taper 0,38 (r21 = 1,508, r32 = 1,500)

| grandezza | coarse | medium | fine | convergenza | p | φ_ext | GCI_fine [%] | E coarse / medium / fine [%] |
|---|---|---|---|---|---|---|---|---|
| Di_N | 1,05072 | 1,05755 | 1,06192 | monotona | 1,13 | 1,06935 | 0,874 | 2,177 / 1,379 / 0,868 |
| D0_N | 5,4271 | 5,3999 | 5,3675 | divergente | 0,39 | 5,1820 | 4,321 | 5,913 / 5,257 / 4,476 |
| D_N | 6,47782 | 6,45745 | 6,42942 | divergente | 0,74 | 6,35059 | 1,533 | 2,504 / 2,103 / 1,552 |
| e_span | 0,96063 | 0,95443 | 0,95038 | monotona | 1,08 | 0,94312 | 0,955 | 2,321 / 1,499 / 0,963 |
| alpha_trim | 1,3250 | 1,3544 | 1,3932 | divergente | 0,63 | 1,5233 | 11,680 | 16,275 / 13,860 / 10,682 |
| CLmax_wing | 1,1402 | 1,1391 | 1,1366 | divergente | 2,05 | 1,1346 | 0,213 | 0,613 / 0,494 / 0,213 |
| M_root_Nm | 81,9514 | 81,7215 | 81,8532 | oscillante | 1,37 | 82,0279 | 0,267 | 0,117 / 0,467 / 0,266 |

## Serie corda (V 64, growth scalato), taper 1,00 (r21 = 1,504, r32 = 1,506)

| grandezza | coarse | medium | fine | convergenza | p | φ_ext | GCI_fine [%] | E coarse / medium / fine [%] |
|---|---|---|---|---|---|---|---|---|
| Di_N | 1,15951 | 1,13727 | 1,12629 | monotona | 1,72 | 1,11548 | 1,200 | 4,934 / 2,442 / 1,211 |
| D0_N | 4,9730 | 5,4216 | 5,6279 | monotona | 1,89 | 5,8052 | 3,937 | 17,919 / 8,259 / 3,817 |
| D_N | 6,13251 | 6,55887 | 6,75419 | monotona | 1,90 | 6,92084 | 3,084 | 14,238 / 6,538 / 3,010 |
| e_span | 0,87034 | 0,88752 | 0,89628 | monotona | 1,64 | 0,90550 | 1,286 | 4,853 / 2,482 / 1,272 |
| alpha_trim | 1,4703 | 1,4395 | 1,3968 | divergente | 0,81 | 1,2881 | 9,725 | 17,679 / 14,691 / 10,546 |
| CLmax_wing | 1,0873 | 1,0858 | 1,0862 | oscillante | 3,20 | 1,0863 | 0,017 | 0,107 / 0,063 / 0,017 |
| M_root_Nm | 89,8246 | 89,6064 | 89,6930 | oscillante | 2,26 | 89,7502 | 0,080 | 0,104 / 0,200 / 0,080 |

## Serie corda (V 64, growth scalato), taper 0,38 (r21 = 1,504, r32 = 1,506)

| grandezza | coarse | medium | fine | convergenza | p | φ_ext | GCI_fine [%] | E coarse / medium / fine [%] |
|---|---|---|---|---|---|---|---|---|
| Di_N | 1,07362 | 1,05755 | 1,04625 | monotona | 0,85 | 1,01911 | 3,243 | 6,686 / 4,715 / 3,329 |
| D0_N | 5,0434 | 5,3999 | 5,4130 | monotona | 8,06 | 5,4135 | 0,012 | 8,546 / 0,314 / 0,012 |
| D_N | 6,11702 | 6,45745 | 6,45925 | monotona | 12,80 | 6,45926 | 0,000 | 6,623 / 0,035 / 0,000 |
| e_span | 0,94014 | 0,95443 | 0,96467 | monotona | 0,80 | 0,99101 | 3,412 | 6,416 / 4,614 / 3,321 |
| alpha_trim | 1,3847 | 1,3544 | 1,3096 | divergente | 0,97 | 1,2176 | 8,782 | 17,152 / 14,045 / 9,445 |
| CLmax_wing | 1,1372 | 1,1391 | 1,1347 | divergente | 1,96 | 1,1312 | 0,393 | 0,661 / 0,878 / 0,394 |
| M_root_Nm | 82,0668 | 81,7215 | 81,7623 | oscillante | 5,22 | 81,7678 | 0,008 | 0,457 / 0,071 / 0,008 |

## (a) Scarto di e_span dalla linea portante

| taper | linea portante | e mesh attuale | e_ext apertura | e_ext corda | e fine (V96) | e fine (U180) |
|---|---|---|---|---|---|---|
| 1,00 | ≈ 0,91 | 0,8875 | 0,8357 | 0,9055 | 0,8841 | 0,8963 |
| 0,38 | ≈ 0,98 | 0,9544 | 0,9431 | 0,9910 | 0,9504 | 0,9647 |

## (b) Differenza di Di_N e D_N fra taper 1 e 0,38

| mesh | Di_N taper 1 [N] | Di_N 0,38 [N] | ΔDi [%] | ΔD [%] |
|---|---|---|---|---|
| U120 × V43 | 1,13277 | 1,05072 | 7,243 | 1,165 |
| U120 × V64 (attuale) | 1,13727 | 1,05755 | 7,010 | 1,546 |
| U120 × V96 | 1,14178 | 1,06192 | 6,994 | 1,899 |
| U80 × V64 | 1,15951 | 1,07362 | 7,407 | 0,253 |
| U180 × V64 | 1,12629 | 1,04625 | 7,107 | 4,367 |

Escursione di ΔDi fra le mesh: **0,413 punti percentuali** (5,7 % del valore); ΔD: 4,114 punti percentuali.

## Errore stimato di D_N per mesh (max sulle due geometrie)

| mesh | E(D_N) [%] | serie |
|---|---|---|
| U120 × V96 | 1,572 | apertura (U 120) |
| U120 × V64 (attuale) | 2,103 | apertura (U 120) |
| U120 × V43 | 2,504 | apertura (U 120) |
| U180 × V64 | 3,010 | corda (V 64, growth scalato) |
| U120 × V64 (attuale) | 6,538 | corda (V 64, growth scalato) |
| U80 × V64 | 14,238 | corda (V 64, growth scalato) |
