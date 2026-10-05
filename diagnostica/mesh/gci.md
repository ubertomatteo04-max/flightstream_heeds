# Convergenza di mesh – configurazione D, ccs_wing (chord_scale 1), generato da gci.py

CL e CDi dal log (5 cifre significative); CDo, CMy, cl_sec_max, sep_frac_up_le, x_sep_up da results.txt (CDo e CMy a 4 decimali). Celik et al. (2008): r = (N_i/N_j)^(1/2), Fs = 1,25.

| livello | Mesh_U / Mesh_V, growth rate U | pannelli (semiala) | primo pannello al LE [x/c] | tempo per run [s] (4° / 12°) | status |
|---|---|---|---|---|---|
| coarse | 80 / 43, 1,1 | 6806 | 0,00944 | 17,1 / 16,0 | 0 / 0 |
| coarse_g | 80 / 43, 1,15369 | 6810 | 0,00512 | 10,6 / 12,7 | 0 / 0 |
| medium | 120 / 64, 1,1 | 15262 | 0,00321 | 43,8 / 27,4 | 0 / 0 |
| fine_g | 180 / 96, 1,0656 | 34464 | 0,00205 | 60,4 / 63,3 | 0 / 0 |
| fine | 180 / 96, 1,1 | 34454 | 0,00072 | 55,1 / 56,9 | 0 / 0 |

## Famiglia A: growth rate in corda 1,1 fisso (il primo pannello al LE scala di 3–4,5)

### α = 4°

| grandezza | coarse | medium | fine | medium–fine [%] | R | convergenza | p | φ_ext | GCI_fine [%] |
|---|---|---|---|---|---|---|---|---|---|
| CL | 0,57671 | 0,57670 | 0,57643 | 0,05 | 27,000 | divergente | 8,03 | 0,57642 | 0,00 |
| CDi | 0,00775 | 0,00773 | 0,00774 | −0,15 | −0,447 | oscillante | 1,99 | 0,00775 | 0,15 |
| CDo | 0,0112 | 0,0125 | 0,0140 | −10,71 | 1,154 | divergente | 0,33 | 0,0244 | 93,19 |
| CMy | −0,1993 | −0,1993 | −0,1989 | 0,20 | – | non determinabile (una differenza nulla) | – | – | – |
| cl_sec_max | 0,6336 | 0,6359 | 0,6333 | 0,41 | −1,116 | divergente | 0,27 | 0,6108 | 4,44 |
| sep_frac_up_le | 0,0000 | 0,0000 | 0,0000 | – | – | costante | – | 0,0000 | 0,00 |
| x_sep_up | 0,4374 | 0,3979 | 0,4023 | −1,09 | −0,111 | oscillante | 5,44 | 0,4029 | 0,17 |

### α = 12°

| grandezza | coarse | medium | fine | medium–fine [%] | R | convergenza | p | φ_ext | GCI_fine [%] |
|---|---|---|---|---|---|---|---|---|---|
| CL | 1,33800 | 1,34030 | 1,34510 | −0,36 | 2,087 | divergente | 1,78 | 1,34962 | 0,42 |
| CDi | 0,04173 | 0,04156 | 0,04177 | −0,50 | −1,243 | divergente | 0,53 | 0,04264 | 2,60 |
| CDo | 0,0206 | 0,0226 | 0,0238 | −5,04 | 0,600 | monotona | 1,28 | 0,0256 | 9,21 |
| CMy | −0,4013 | −0,4016 | −0,4030 | −0,35 | 4,667 | divergente | 3,74 | −0,4034 | 0,12 |
| cl_sec_max | 1,4713 | 1,4823 | 1,4859 | −0,24 | 0,332 | monotona | 2,74 | 1,4877 | 0,15 |
| sep_frac_up_le | 0,0417 | 0,0517 | 0,0562 | −7,96 | 0,446 | monotona | 2,01 | 0,0597 | 7,83 |
| x_sep_up | 0,0491 | 0,0211 | 0,0060 | 250,51 | 0,538 | monotona | 1,55 | −0,0111 | 355,68 |

r21 = 1,502, r32 = 1,497. **Criterio (|medium − fine| < 2 % su CL, CDi, CDo, CMy, cl_sec_max): NON SUPERATO** — oltre il limite: CDo −10,71 % (α 4°); CDo −5,04 % (α 12°).

## Famiglia B: growth rate in corda scalato 1,1^(120/u_pts) (famiglia geometricamente simile, Celik)

### α = 4°

| grandezza | coarse | medium | fine | medium–fine [%] | R | convergenza | p | φ_ext | GCI_fine [%] |
|---|---|---|---|---|---|---|---|---|---|
| CL | 0,57529 | 0,57670 | 0,58204 | −0,92 | 3,787 | divergente | 3,23 | 0,58400 | 0,42 |
| CDi | 0,00777 | 0,00773 | 0,00782 | −1,18 | −1,919 | divergente | 1,59 | 0,00792 | 1,62 |
| CDo | 0,0119 | 0,0125 | 0,0128 | −2,34 | 0,500 | monotona | 1,73 | 0,0131 | 2,85 |
| CMy | −0,1985 | −0,1993 | −0,2018 | −1,24 | 3,125 | divergente | 2,76 | −0,2030 | 0,75 |
| cl_sec_max | 0,6299 | 0,6359 | 0,6427 | −1,06 | 1,124 | divergente | 0,26 | 0,7030 | 11,73 |
| sep_frac_up_le | 0,0000 | 0,0000 | 0,0000 | – | – | costante | – | 0,0000 | 0,00 |
| x_sep_up | 1,0000 | 0,3979 | 0,3980 | −0,02 | −0,000 | oscillante | 21,67 | 0,3980 | 0,00 |

### α = 12°

| grandezza | coarse | medium | fine | medium–fine [%] | R | convergenza | p | φ_ext | GCI_fine [%] |
|---|---|---|---|---|---|---|---|---|---|
| CL | 1,34000 | 1,34030 | 1,34880 | −0,63 | 28,333 | divergente | 8,13 | 1,34912 | 0,03 |
| CDi | 0,04190 | 0,04156 | 0,04185 | −0,69 | −0,840 | oscillante | 0,43 | 0,04335 | 4,48 |
| CDo | 0,0214 | 0,0226 | 0,0235 | −3,83 | 0,750 | monotona | 0,73 | 0,0261 | 13,76 |
| CMy | −0,4007 | −0,4016 | −0,4054 | −0,94 | 4,222 | divergente | 3,49 | −0,4066 | 0,37 |
| cl_sec_max | 1,4749 | 1,4823 | 1,4943 | −0,81 | 1,637 | divergente | 1,18 | 1,5138 | 1,63 |
| sep_frac_up_le | 0,0426 | 0,0517 | 0,0578 | −10,57 | 0,672 | monotona | 1,01 | 0,0699 | 26,12 |
| x_sep_up | 0,0263 | 0,0211 | 0,0148 | 42,28 | 1,199 | divergente | 0,42 | −0,0187 | 283,30 |

r21 = 1,503, r32 = 1,497. **Criterio (|medium − fine| < 2 % su CL, CDi, CDo, CMy, cl_sec_max): NON SUPERATO** — oltre il limite: CDo −2,34 % (α 4°); CDo −3,83 % (α 12°).
