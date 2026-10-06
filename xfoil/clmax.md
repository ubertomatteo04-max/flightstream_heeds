# XFOIL 6.99 – polari e clmax(Re) di vespa_root.dat (Parte 7D, generato da xfoil_polars.py)

Profilo `profiles/vespa_root.dat` (200 punti, corda 1, TE tozzo 0,652 % c), PPAR N = 180, Mach 0, ITER 200, α da −4 a 18° con passo 0,25° in due sequenze da 0°. clmax = massimo cl fra i punti convergenti; **valido** se almeno 2 punti convergenti oltre il massimo, altrimenti **incerto**.

**TE tozzo:** XFOIL tiene il profilo aperto com'è (nessuna chiusura): il gap al TE entra come pannello di bordo d'uscita con la scia che parte dai due spigoli (trattamento standard di XFOIL per TE spessi). XFOIL al caricamento: `Blunt trailing edge.  Gap =  0.00652` (= 0,652 % c).

## Ncrit 9

| Re | punti convergenti | clmax | α_stall [°] | punti oltre il massimo | esito |
|---|---|---|---|---|---|
| 1,00e+05 | 88/89 | 1,2922 | 12,00 | 23 | valido |
| 1,50e+05 | 80/89 | 1,3218 | 13,50 | 9 | valido |
| 2,00e+05 | 88/89 | 1,3343 | 13,25 | 19 | valido |
| 2,50e+05 | 87/89 | 1,3390 | 13,75 | 16 | valido |
| 3,00e+05 | 89/89 | 1,3518 | 14,50 | 14 | valido |
| 4,00e+05 | 88/89 | 1,3691 | 15,25 | 11 | valido |
| 5,00e+05 | 87/89 | 1,3964 | 15,00 | 12 | valido |
| 6,00e+05 | 88/89 | 1,4272 | 15,50 | 10 | valido |
| 8,00e+05 | 87/89 | 1,4863 | 15,75 | 9 | valido |

## Ncrit 5

| Re | punti convergenti | clmax | α_stall [°] | punti oltre il massimo | esito |
|---|---|---|---|---|---|
| 1,00e+05 | 89/89 | 1,2239 | 13,75 | 17 | valido |
| 1,50e+05 | 89/89 | 1,2622 | 14,75 | 13 | valido |
| 2,00e+05 | 88/89 | 1,2945 | 14,50 | 14 | valido |
| 2,50e+05 | 87/89 | 1,3261 | 14,50 | 14 | valido |
| 3,00e+05 | 86/89 | 1,3541 | 14,75 | 13 | valido |
| 4,00e+05 | 87/89 | 1,4069 | 15,00 | 12 | valido |
| 5,00e+05 | 86/89 | 1,4529 | 15,25 | 11 | valido |
| 6,00e+05 | 87/89 | 1,4888 | 15,75 | 9 | valido |
| 8,00e+05 | 89/89 | 1,5451 | 16,25 | 7 | valido |

## Re 4,75e+05 (semiala in FlightStream, V 20 m/s, corda 0,345 m)

| Ncrit | cl_α 2D (−2…6°) [/rad] | α₀ [°] | cl a 4° | clmax | α_stall [°] |
|---|---|---|---|---|---|
| 9 | 6,436 | −2,10 | 0,6874 | 1,3906 | 15,25 |
| 5 | 6,346 | −2,05 | 0,6798 | 1,4430 | 15,25 |

Confronto con la sezione a metà apertura in FlightStream: rimandato (come da richiesta).

Polari complete: `polars/polar_Re<Re>_N<n>.csv` (punti convergenti) e i file grezzi di XFOIL `_pos.txt`/`_neg.txt`.
