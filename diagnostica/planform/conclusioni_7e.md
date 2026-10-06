# 7E – conclusioni sulla convergenza di mesh (ccs_planform, trim W = 147,15 N)

Dati: `gci_7e.md` (generato da `gci_7e.py`). 5 mesh × 2 geometrie (taper 1,0 e 0,38, S_half fisso, twist 0), tutti
status 0. Serie in corda con growth rate scalato (famiglia simile).

## Variazioni medium → fine (le più leggibili: p di Celik spesso fuori dal campo asintotico)

| grandezza | apertura V64 → V96, taper 1 / 0,38 | corda U120 → U180, taper 1 / 0,38 |
|---|---|---|
| Di_N | +0,40 % / +0,41 % | −0,97 % / −1,07 % |
| D0_N | −0,18 % / −0,60 % | **+3,81 %** / +0,24 % |
| D_N | −0,08 % / −0,43 % | **+2,98 %** / +0,03 % |
| e_span | −0,38 % / −0,42 % | +0,99 % / +1,07 % |
| alpha_trim | +0,28 % / +2,86 % | −2,97 % / −3,31 % |
| CLmax_wing\* | −0,13 % / −0,22 % | +0,04 % / −0,39 % |
| M_root_Nm | +0,05 % / +0,16 % | +0,10 % / +0,05 % |

\* clmax segnaposto.

- In apertura Di_N cresce di circa lo 0,4 % a ogni raffinamento con passi quasi uguali (p ≈ 0): non è nel campo
  asintotico. Gli errori "E" della serie in apertura nella tabella finale di `gci_7e.md` (fino al 34 %) vengono da
  questo p ≈ 0 e **non vanno usati**.
- In corda D0_N della rettangolare non converge (+9,0 % da U80 a U120, +3,8 % da U120 a U180; GCI_fine 3,9 %), mentre
  quello di taper 0,38 sì (+0,24 %). È lo stesso comportamento della CDo nella v2.6.0: l'attrito dello strato limite
  integrale dipende dal pannello al bordo d'attacco.
- M_root_Nm e CLmax_wing sono convergenti (≤ 0,5 %).

## (a) Lo scarto di e dalla linea portante dipende dalla mesh?

Sì, quasi tutto dalla mesh **in corda**. Con il raffinamento in corda e_span sale ed estrapola (Richardson) a **0,906**
(taper 1, linea portante ≈ 0,91) e **0,991** (taper 0,38, ≈ 0,98). In apertura e_span scende di circa lo 0,4 % per
livello, poco e senza un limite chiaro. La mesh attuale (U120 × V64) sottostima e di circa il 2 % (rettangolare) e il
4 % (taper 0,38) rispetto al valore estrapolato in corda.

## (b) La differenza di Di_N fra taper 1 e 0,38 è stabile?

**Sì, per Di_N:** ΔDi = 6,99–7,41 % sulle 5 mesh, escursione **0,41 punti percentuali** (< 0,5). **No per D_N:**
ΔD = 0,25–4,37 % (escursione 4,1 punti), perché D0_N della rettangolare cambia con la mesh in corda e quello di taper
0,38 no.

## Proposta per SHERPA

Nessuna mesh provata ha GCI < 1 % su D_N: in corda il GCI_fine è 3,1 % (taper 1), in apertura 1,6 %, quindi il
criterio richiesto non è soddisfacibile con queste mesh, nemmeno con la più fine (107 s per design). Opzioni:

1. **(consigliata) Mesh attuale U120 × V64 (54 s per design)**: tempi accettabili (150 valutazioni ≈ 2,3 h); ΔDi stabile
   entro 0,4 punti; M_root, CLmax_wing (e quindi stall_margin) convergenti. D_N dichiarato con un'incertezza di mesh di
   circa il 3 % concentrata su D0_N: differenze di D_N fra design sotto circa il 3 % non sono significative.
2. U180 × V64 (≈ 107 s, 150 valutazioni ≈ 4,5 h): riduce l'errore su D_N ma non lo porta sotto l'1 %.
3. Obiettivo Di_N invece di D_N (convergenza migliore delle differenze), con D0_N come risposta di controllo.

La più leggera provata (U80 × V64, 38,5 s) ha D0_N lontano del 9–18 % dal valore estrapolato: da scartare.
