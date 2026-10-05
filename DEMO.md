# FlightStream + HEEDS: catena automatica per l'ottimizzazione di una semiala

> Numeri dello Study_2 (sweep HEEDS su aoa, 2026-10-04) verificati con
> `heeds_report.bat --check-against-mock …`: dettaglio in [`demo/verifica_Study_2.md`](demo/verifica_Study_2.md).

## Obiettivo e cosa è stato fatto

Far valutare a **HEEDS MDO** design aerodinamici calcolati con **FlightStream 26.1** senza interventi
manuali, come base per DOE e ottimizzazione. Fatto: driver Python che genera lo script FlightStream,
lo esegue in batch e restituisce i risultati in un formato fisso; validazione contro un run manuale;
gestione degli errori (status, licenza, timeout, processi); due modalità geometriche (`fixed` da `.fsm`,
`ccs_wing` con la corda variabile); collegamento a HEEDS provato con un Evaluation Only e uno sweep su aoa.

## Architettura

```mermaid
flowchart LR
    H[HEEDS MDO<br/>studio] -->|params.txt<br/>aoa, velocity, ...| B[run_fs.bat]
    B --> D[fs_driver.py<br/>script FlightStream]
    D -->|-hidden -script| F[FlightStream 26.1<br/>pannelli + strato limite]
    F -->|carichi, log, VTK| D
    D -->|results.txt<br/>49 righe fisse + codice di uscita| H
```

La comunicazione avviene **solo tramite file** nella cartella di ogni design: HEEDS scrive
`params.txt`, lancia `run_fs.bat`, legge `results.txt` (stesse 49 righe nello stesso ordine,
`schema_version = 4`; le righe taggate nello Study_2 non si sono spostate) e il codice di uscita (0 = design valido). È automatica per ogni design; il motivo
di un errore è sempre in `run_info.txt`.

## Validazione della catena

| aoa = 4°, V = 20 m/s | CL | CD | CMy | L/D | Re |
|---|---|---|---|---|---|
| Riferimento (run manuale di FlightStream, `riferimento_run_fsm2`) | 0,5767 | 0,0202 | −0,1993 | 28,55 | 474985 |
| Driver da riga di comando (`heeds_mock.py`) | 0,5767 | 0,0202 | −0,1993 | 28,5495 | 474985 |
| HEEDS, Evaluation Only (Study_1) | 0,5767 | 0,0202 | −0,1993 | 28,5495 | 474985 |

Sweep HEEDS su aoa = 0, 2, …, 12° (Study_2, 7 design) confrontato design per design con il DOE del
driver: **VERIFICA OK**, **7/7** design, differenza relativa massima **0** su CL, CD, CMy e L/D (tolleranza
1e-4), 0 design in errore. Tempo per design **31 s** in media (27–40 s): ≈ 30 s di FlightStream, ≈ 1 s di
driver e HEEDS; studio intero 3 min 40 s.

Gestione degli errori provata in HEEDS: un design con codice di uscita ≠ 0 viene **scartato** ("The return
value (1) for the analysis command did not match the specified value (0). This design analysis will be
marked as an error.").

## Risultati

| CL in funzione di α | L/D in funzione di α |
|---|---|
| ![CL-alpha](demo/CL_alpha.png) | ![L/D-alpha](demo/LD_alpha.png) |

- dCL/dα (0–8°, minimi quadrati): **5,515 /rad** (0,0963 /deg) dallo sweep HEEDS, identico al DOE del
  driver; teoria dell'ala finita (AR = 15,3): Helmbold 5,515 /rad (scarto < 0,01 %), linea portante
  ellittica 5,557 /rad (−0,8 %).
- L/D massimo **28,55 a 4°** tra i punti calcolati (passo 2°).
- **Convergenza di mesh** (v2.6.0): carichi inviscidi entro 1,2 % fra la mesh attuale e una 1,5 volte più fitta per
  direzione; CDo con GCI 2,9 % (4°) e 13,8 % (12°). Mesh attuale confermata.
- **Carico lungo l'apertura** (v2.6.0): cl(η) dai carichi di sezione di FlightStream, integrale = CL entro lo 0,6 %
  (figura in `diagnostica/apertura/cl_eta.png`); nuove risposte `cl_sec_*` in coda a `results.txt`.
- **Collaudo finale** (v2.6.0): 10 design con `run_fs.bat`, righe 2–39 identiche ai DOE precedenti e allo Study_2.

## Limiti

Conclusioni complete in [`REPORT_ALA.md`](REPORT_ALA.md).

- Metodo a pannelli con strato limite integrale: **nessuno stallo** (CL lineare fino a 12° e oltre).
- Modello di separazione di FlightStream (Airfoil, Stratford) **non usabile** per quest'ala: separazione segnalata
  già a 0°, la correzione aumenta CL e non dà resistenza.
- H e cf del VTK: indicatori **qualitativi** (strato limite sul Cp inviscido, transizione anticipata, non validati).
- Incertezza geometrica sul bordo d'uscita: ≈ 4 % su CL, ≈ 6 % su CMy (raccordo di default contro TE tozzo).
- Reynolds ≈ 4,7·10⁵, **sotto il campo** del modello transizionale (5·10⁵–1,5·10⁶). Una sola variabile
  geometrica (`chord_scale`).

## Prossimi passi

1. **Problema SHERPA** da discutere (proposta in `REPORT_ALA.md` §6): min `D_N` con `L_N` ≥ peso (da definire),
   variabili `aoa` e `chord_scale`; senza vincolo di stallo l'ottimo va sul limite delle variabili.
2. **Validazione esterna** (galleria o CFD) di carichi, CDo e indicatori di strato limite.
3. **API HEEDS:** creare e lanciare gli studi da script Python invece che dalla GUI.
4. **Fusoliera:** pressioni, momenti e interferenza ala–fusoliera nel flusso attaccato; per la resistenza di
   pressione serve un riferimento RANS.
