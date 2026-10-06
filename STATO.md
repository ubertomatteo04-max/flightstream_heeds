# STATO del progetto fs_heeds_pipeline — aggiornato al 2026-10-06 (v2.8.1: Parte 8 in corso – 7C.1 fatta, schema 7)

**Lavoro sull'ala chiuso (v2.6.0).** Conclusioni per il team: `REPORT_ALA.md`. Configurazione di riferimento D
(disaccoppiata, separazione `none`); C e CS esplorative (`configs/esplorativi/`); modello di separazione abbandonato
per quest'ala; H/cf qualitativi; XFOIL non usato in questa fase (`reference/xfoil/` resta com'è).

Pipeline Python (solo libreria standard) che fa girare FlightStream 26.1 in batch per HEEDS:
`params.txt` → script FlightStream → run `-hidden` → `results.txt`. La documentazione d'uso completa
è in `README.md` e `HEEDS_SETUP.md`; questo file dice **dove siamo** e **perché** certe cose sono come
sono. Dalla v2.6.0 sta nella radice del repo (prima era in `Desktop\fs_heeds_pipeline\`, fuori dal versionamento).

## 1. Stato attuale

| Parte | Stato |
|---|---|
| `fs_driver.py` v2.6.0 + `geometry.py` + `postprocess.py` + `run_fs.bat` | funzionanti con FlightStream 26.1 (build 5012026); repo git `github.com/ubertomatteo04-max/flightstream_heeds`, commit v2.2.0 → v2.6.0 |
| Modalità `fixed` (template `..\semiala_run01.fsm`) | **validata**: riproduce esattamente il run di riferimento; DOE aoa 0–12° tutto status 0; baseline reale (§3.7) |
| Modalità `ccs_wing` (CCS `..\semiala_ccs_U120_V64_blended.csv`, `chord_scale`) | **validata**: con `chord_scale = 1` coincide con `fixed` anche nel Re; DOE `chord_scale` 0,9/1,0/1,1 coerente; baseline reale (§3.7) |
| `results.txt` | schema fisso di **49 righe** (`RESULTS_SCHEMA`, `schema_version = 4` in riga 1, v2.6.0): righe 1–39 identiche allo schema 2 (tagging HEEDS valido, righe 2, 5, 6, 10, 12 bloccate da un test), 40–45 accoppiamento/separazione, 46–49 carico lungo l'apertura (`cl_sec_*`); chiavi nuove solo in fondo |
| Mesh (ccs_wing) | blocco JSON `mesh` (Mesh_U/Mesh_V del CCS); default = mesh attuale, **confermata** (v2.6.0, §3.14): carichi inviscidi entro 1,2 % medium–fine, CDo dichiarata con il GCI (2,9 % a 4°, 13,8 % a 12°) |
| Bordo d'uscita (ccs_wing) | default `te_type: "blended"` (raccordo del CCS); opzione `"blunt"` (TE tozzo fedele con base region): CL −4 %, CMy −6 % → incertezza geometrica dichiarata (§3.14) |
| Carico lungo l'apertura | 40 sezioni, carichi di sezione di FlightStream; ∫cl·c = CL entro 0,65 % (§3.14) |
| `REPORT_ALA.md` | report di chiusura per il team (v2.6.0) |
| Accoppiamento viscoso e separazione | attivabili da JSON (`solver.viscous_coupling`, blocco `separation`), default = comportamento validato (regressione byte per byte righe 2–39); **ESPLORATIVO, NON VALIDATO** (§3.12). Diagnosi (§3.13): il criterio di Stratford segna la separazione al TE già a 0–4° in tutte le varianti; i campi di strato limite del VTK non vengono dalla fase accoppiata. **Modello di separazione abbandonato per quest'ala (v2.6.0)**; JSON in `configs/esplorativi/` |
| Riferimento XFOIL 6.99 | `reference\xfoil\`: profilo `vespa.dat` dal CCS, polari Ncrit 7/9/11, dump, `summary.md`, grafici; α₀ inviscido −2,00° contro −1,98° di FlightStream → profilo verificato (§3.13) |
| Contratto con HEEDS | codice di uscita 0 se lo status è in `heeds.success_statuses` (default `[0]`); `run_info.txt` termina con `FS_DRIVER_RESULT status=<n> success=<0\|1>` |
| Esecuzione come HEEDS | `run_fs.bat` (interprete fissato, `%~dp0`, `exit /b %ERRORLEVEL%`); percorsi del JSON risolti rispetto al JSON, output nella cartella corrente; percorsi con spazi verificati con run reali |
| Processi / licenza | controllo prima del lancio (FlightStream già attivo → status 6), chiusura dell'albero al timeout, nuovi tentativi sulla licenza; tutto provato con run reali (§3.6) |
| Metriche di separazione | `sep_frac_up_le` (vincolo consigliato), `x_sep_up`, `H_max_attached_up`, `x_H_max_attached_up`, `sep_frac_lo_te` (diagnostica) implementate con il blocco `wing_frame` del JSON |
| Test automatici | 52 test senza FlightStream: `python -m unittest discover -s tests -v` (≈ 40 s) |
| `heeds_mock.py` | lancia `run_fs.bat` con cwd = cartella del design; `--root` con struttura `Design_<N>\Analysis_1` |
| Collegamento a HEEDS | **Evaluation Only (Study_1) e sweep su aoa (Study_2, 7 design) riusciti e verificati** (HEEDS 2604.0, §3.8 e §3.10); controllo del codice di uscita attivo e provato |
| `heeds_report.py` / `.bat` | CSV + grafici CL–α e L/D–α di uno studio dai `results.txt` dei design; con `--check-against-mock` verifica lo studio contro il DOE del driver (`verifica.md`, VERIFICA OK/FALLITA, codice 0/1); provato sul DOE mock (OK), su Study_1 (OK) e su una copia alterata (FALLITA) |
| `preflight.py` / `.bat` | controlli prima di uno studio, senza FlightStream: 17 voci, oggi `PREFLIGHT OK` |
| `DEMO.md` | presentazione di una pagina per il team, completa con i numeri dello Study_2; grafici e verifica in `demo/` |
| Compatibilità CCS 26.1 (Parte 5) | **verificata (v2.6.0, §3.14):** `Parameter;`, `WingRefArea`, `MAC` non esistono nel manuale 26.1 (intestazione: `ReferenceArea`, `ReferenceLength`, `Units`, `CG`, p. 77) e la pipeline non li scrive: Sref e Lref vengono da `SOLVER_SET_REF_AREA/LENGTH`. Nessuna modifica; ccs_wing con chord_scale 1,0 = fixed (CL, CMy, Sref, Re) |

File principali (in `Desktop\fs_heeds_pipeline\`):

- `fs_heeds_pipeline\` — codice, JSON dei casi (`case_semiala_fixed.json`, `case_semiala_ccs.json`), README, HEEDS_SETUP.
- `semiala_run01.fsm` — template della semiala (identico, md5 `998c2e80…`, a quello usato per il riferimento in
  `Desktop\ZEFIRO\Flighstream\pipeline_flightstream\reference\`).
- `semiala_ccs_U120_V64_blended.csv` — CCS di partenza per `ccs_wing`.
- `riferimento_run_fsm2\` — copia dello script, dei carichi e del log del **run di riferimento**
  (l'originale stava in una cartella temporanea di una sessione precedente e può sparire).
- Cartelle di prova in `fs_heeds_pipeline\`: `test_fixed_a04_fluido_fsm` (fixed vecchio), `test_A_reinit`,
  `test_B_reinit`, `test_C_ccs` (fluido ISA), `test_C2_ccs_fluido` (§3.1), `mock_runs\` (DOE fixed, §3.3),
  `mock_runs_ccs\` (DOE ccs, §3.4). **Attenzione:** `heeds_mock.py` cancella le `Design_NNN` della cartella
  `--out` (default `mock_runs`): per un nuovo DOE usare un `--out` diverso se servono i VTK del DOE fixed.
- `fs_heeds_pipeline\diagnostica\diag_bl.py`, `diag_bl2.py` — script di analisi dei VTK del DOE fixed (§3.5),
  solo diagnostica, non usati dal driver.
- `fs_heeds_pipeline\baseline\fixed`, `baseline\ccs` — `params_baseline.txt`, `results_baseline.txt`,
  `run_info_baseline.txt` dei run reali per il tagging in HEEDS (§3.7). Le cartelle dei run (con VTK)
  sono in `Desktop\fs_heeds_pipeline\baseline_runs\<fixed|ccs>\Design_1\Analysis_1` (fuori dal repo).

Valori di riferimento (aoa = 4°, V = 20 m/s, Sref = 1,8221 m² nel run di riferimento, 1,82208 nei JSON dalla v2.3.1, Lref = 0,345091 m, simmetria Mirror, carichi
riportati all'ala intera): **CL 0,5767 · CDi 0,0077 · CDo 0,0125 · CMy −0,1993 · Re 474985 · 91 iterazioni.**
Geometria: semiapertura 2,64 m (b = 5,28 m), corda ≈ 0,345 m, allungamento AR = b²/Sref = 15,30.

## 2. Decisioni prese (e perché)

**Sintassi dello script (manuale 26.1 installato è la fonte di verità):**
`C:\Program Files\Altair\2026.1\flightstream\Altair FlightStream User Manual.pdf`.

- **Righe vuote**: il driver scrive una riga vuota dopo **ogni** comando (funzione `render`). Il manuale:
  una riga vuota chiude i parametri di un comando su più righe, un commento no; senza riga vuota il
  comando successivo viene letto come parametro → `Error in script … at line N`. In `geometry.py` ogni
  comando è una lista di righe. Lo script di riferimento non le mette dopo i comandi su una riga e
  funziona lo stesso, ma la regola del manuale è più sicura.
- **OPEN**: file + solo `LOAD_SOLVER_INITIALIZATION ENABLE|DISABLE` (provato con `--probes`: file da solo
  → errore; con `RESET_PARALLEL_CORES` → errore, il comando non esiste più nel 26.1).
- **Inizializzazione in `fixed`**: `geometry.reinitialize = true` è il **default**. OPEN con
  `LOAD_SOLVER_INITIALIZATION DISABLE`, poi tutto esplicito dal blocco `solver` del JSON:
  `SET_SOLVER_STEADY`, `SET_BOUNDARY_LAYER_TYPE`, `SET_SURFACE_ROUGHNESS` (anche 0),
  `SET_SOLVER_VISCOUS_COUPLING`, `SOLVER_SET_*`, `INITIALIZE_SOLVER` (`SOLVER_MODEL`, `SURFACES 1` +
  `1,ENABLE` = quad mesher, `WAKE_TERMINATION_X DEFAULT`, `SYMMETRY MIRROR`, `WALL_COLLISION_AVOIDANCE
  DISABLE`), `CLEAR_SOLUTION`, `START_SOLVER`, poi `SET_VORTICITY_DRAG_BOUNDARIES 1` / `1`.
  Ordine copiato dallo script del riferimento (condizioni prima di `INITIALIZE_SOLVER`, vorticity
  drag boundaries dopo `START_SOLVER`). **Perché:** con l'inizializzazione salvata nel .fsm (vecchio
  comportamento) CL era +2,8 %, CDi +6,5 %, CMy −2,5 % a pari Re e iterazioni; il risultato dipendeva
  dallo stato in cui il .fsm era stato salvato. Con la reinizializzazione il riferimento è riprodotto
  esattamente. `reinitialize = false` resta possibile. La vecchia chiave `geometry.open_options` è stata
  tolta e ora dà errore (era in conflitto con `reinitialize`).
- **Stesso blocco di inizializzazione in `ccs_wing`**: `INITIALIZE_SOLVER` e vorticity drag boundaries
  vengono dalla stessa funzione (`geometry.initialize_solver_lines`, `fs_driver.vorticity_lines`), con
  gli stessi valori nei due JSON. `ccs_wing` rifiuta una `symmetry` diversa da `MIRROR`.
- **Fluido (cambiato il 2026-10-04, v2.2.0)**: il blocco `fluid` dei due JSON contiene i valori della
  sezione `Air` di `semiala_run01.fsm`: ρ = 1,225, μ = 1,78·10⁻⁵, p = 101324,02 Pa, T = 288,166 K, γ = 1,4.
  - `fixed`: il fluido non viene riscritto (vale quello del .fsm, che coincide); `fluid.density` serve
    per q, L, D (il 26.1 non scrive la densità nella tabella dei carichi).
  - `ccs_wing`: lo script scrive `FLUID_PROPERTIES` con i valori del blocco `fluid` (`VISCOSITY 1.78e-05`;
    run reale: Re 474985 come `fixed`). Prima usava l'ISA (μ = 1,789·10⁻⁵, Re −0,5 %).
  - ISA alla quota `altitude` **solo** con `fluid.override_fluid = true`, in entrambe le modalità;
    altrimenti `altitude` in `params.txt` o nel blocco `case` è un errore (status 1). Tolta `altitude`
    dal blocco `case` di `case_semiala_ccs.json`.
- **Licenza (v2.2.0)**: il driver legge `fs_stdout.txt` mentre FlightStream gira. Se compare "Checking
  out Altair units...Not available" e dopo 15 s (`LICENSE_GRACE_S`) nessun fallback EDU/feature è
  riuscito ("Success" o "Running script file"), chiude FlightStream, aspetta `run.license_wait_s`
  (default 60 s) e riprova fino a `run.license_retries` (default 2) volte oltre al primo tentativo.
  Se fallisce anche l'ultimo: **status 6** = "licenza FlightStream non disponibile" (prima sarebbe
  finito in timeout dopo 1800 s, status 2). Il periodo di grazia di 15 s è un'aggiunta rispetto alla
  richiesta: evita di uccidere un run in cui le Altair units mancano ma la licenza EDU o a feature
  viene presa subito dopo. Ordine di priorità degli status: 1, 2, 6, 3, 5, 4.
- **Nota HEEDS** (README e HEEDS_SETUP): con geometria variabile (`chord_scale`) Sref cambia e i
  coefficienti non sono confrontabili tra design; obiettivi = `L_over_D` oppure `L_N` e `D_N`.
- **Processi di FlightStream (verificato 2026-10-04, v2.2.3)**: un run `-hidden` del 26.1 è **un solo
  processo `FlightStream.exe`**, figlio diretto di python, **senza processi figli** (campionamento ogni
  0,1 s di tutti i discendenti del driver; il checkout della licenza avviene nel processo stesso, con
  `liblmx-altair.dll`). Al timeout l'unico altro processo che compare è il `taskkill.exe` del driver.
  Default `run.flightstream_process_names = ["FlightStream.exe"]`. Prima del lancio: nessun
  `FlightStream.exe` attivo (attesa 10 s, poi status 6; `kill_stale_flightstream` default false).
  Licenza di questo PC: Altair One "hosted HWU" (token in `%LOCALAPPDATA%\.altair_licensing\PcUberto\
  altair_hostedhwu.cfg`); nessuna variabile Altair nell'ambiente.
  **Procedura di TEST (solo per provare lo status 6):** impostare `ALTAIR_LICENSE_PATH=<server
  inesistente>` **e** `ALM_HHWU=F` **solo nell'ambiente del processo di prova** (es. variabili passate a
  `subprocess` da uno script di test); con la sola `ALTAIR_LICENSE_PATH` il run va a buon fine.
  `ALM_HHWU=F` **non va mai** nei JSON, in `run_fs.bat` né nelle variabili d'ambiente dell'utente o di
  sistema: disattiverebbe la licenza Altair One per tutti i run.
- **Momenti**: nuovo frame 2 con origine (0,0,0) m, assi paralleli al frame 1. Per la semiala dà gli
  stessi valori del frame 1 usato nel riferimento.
- Altre regole verificate: `CLEAR_SOLUTION` (non `SOLVER_CLEAR`), `FLUID_PROPERTIES` con
  `SPECIFIC_HEAT_RATIO` (non `SONIC_VELOCITY`), `SET_VTK_EXPORT_VARIABLES -1 DISABLE`.

- **Schema di results.txt (v2.2.1)**: `RESULTS_SCHEMA` in `fs_driver.py` è l'unico punto che decide chiavi e
  ordine: sezioni stato (con `schema_version` in riga 1) → carichi → riferimenti → strato limite →
  eco degli ingressi; 39 righe uguali per tutte le modalità, `-999` se non pertinenti. Regola confermata:
  **chiavi nuove solo in fondo al file** (niente slot riservati); ogni modifica incrementa
  `SCHEMA_VERSION`. Un controllo all'avvio blocca il driver se una variabile geometrica nuova non è nello
  schema.
- **Contratto di successo (v2.2.1)**: la Success condition di HEEDS legge solo codice di uscita o contenuto
  di file. Codice 0 se lo status è in `heeds.success_statuses` (default `[0]`; `[0, 4]` per DOE in cui H/cf
  non servono). Condizione consigliata: codice di uscita = 0 AND "File contains" `schema_version = 2`.
- **params.txt (v2.3.0)**: accetta ogni formato di stampa numerico di HEEDS (`4`, `4.0`, `4.000000E+00`,
  `-1.5E-01`, CRLF, BOM, spazi, ultima riga senza a capo); rifiuta con status 1 valori non numerici o non
  finiti, `1_000`, `0x10`, esponente `D`, chiavi ripetute o non valide, righe senza un solo `=`.
- **Timeout (v2.3.0)**: `run.timeout_s = 240` nei due JSON della semiala (circa 10 volte il tempo nominale;
  ogni JSON ha il proprio). Caso peggiore di un design: 3 × 240 + 2 × 60 = 840 s → timeout HEEDS ≥ 15 min.
- **Licenza Altair One** legata all'utente Windows: HEEDS deve eseguire in locale con lo stesso utente;
  login da verificare prima di uno studio lungo (durata del token: DA VERIFICARE).

## 3. Test fatti (2026-10-04)

### 3.1 Validazione e ripetibilità (aoa = 4, V = 20)

| Grandezza | Riferimento | fixed vecchio (init .fsm) | A: fixed reinit | B: ripetizione di A | C: ccs_wing, chord_scale 1 (fluido ISA) |
|---|---|---|---|---|---|
| CL | 0,5767 | 0,5931 (+2,84 %) | 0,5767 (0,00 %) | 0,5767 (0,00 %) | 0,5767 (0,00 %) |
| CDi | 0,0077 | 0,0082 (+6,49 %) | 0,0077 (0,00 %) | 0,0077 (0,00 %) | 0,0077 (0,00 %) |
| CDo | 0,0125 | 0,0126 (+0,80 %) | 0,0125 (0,00 %) | 0,0125 (0,00 %) | 0,0125 (0,00 %) |
| CMy | −0,1993 | −0,2043 (+2,51 % in modulo) | −0,1993 (0,00 %) | −0,1993 (0,00 %) | −0,1993 (0,00 %) |
| Re | 474985 | 474985 | 474985 | 474985 | 472495 (−0,52 %, fluido ISA, ora cambiato) |
| Iterazioni | 91 | 91 | 91 | 91 | 91 |
| CL / CDi dal log (5 cifre, it. 91) | 0,57669 / 0,0077251 | 0,59305 / 0,0082073 | 0,57669 / 0,0077251 | identico ad A | 0,57670 / 0,0077252 |

- **A**: `python fs_driver.py --config case_semiala_fixed.json --workdir test_A_reinit --validate` →
  SUPERATA, anche i residui dell'ultima iterazione coincidono con il riferimento.
- **B**: stesso comando in `test_B_reinit` → `results.txt`, `loads.txt` (a parte la data) e `surface.vtk`
  **identici byte per byte** ad A: scarto 0.
- **C**: `python fs_driver.py --config case_semiala_ccs.json --workdir test_C_ccs --validate` → status 0,
  SUPERATA (fatto prima del cambio del fluido: Re 472495).
- **C2** (stesso comando in `test_C2_ccs_fluido`, nuovo fluido): **coincide con A anche nel Re** (474985):
  CL, CD, CDi, CDo, CMy, L/D, iterazioni (91), `area_frac_cf_neg` (0,0175283, con l'ISA era 0,0179257) e
  `H_max` uguali. Differenze residue: 1 unità sulla 5ª cifra nel log (CL 0,57670 contro 0,57669) e L_N
  −0,001 % (Sref calcolata 1,82208 contro 1,8221 del JSON di `fixed`). Durata ≈ 23–28 s.

### 3.2 Licenza (finto FlightStream, `.bat` nello scratchpad)

- `.bat` che stampa i tre "Not available" e resta appeso, con `license_retries = 1`, `license_wait_s = 3`:
  2 tentativi, status 6, codice di uscita 1, durata 36 s, nessun processo rimasto aperto; `run_info.txt`
  elenca i tentativi.
- `.bat` con "Not available" seguito da "Attempting EDU feature checkout...Success!": **non** interrotto
  (status 1 solo perché il finto eseguibile non produce risultati).
- Caso reale visto in mattinata: un checkout fallito ha lasciato FlightStream appeso 10 minuti (prima
  di questa modifica); rientrato da solo dopo pochi minuti.

### 3.3 DOE `fixed`, aoa 0–12° (`python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8,10,12`)

| aoa | status | iter | CL | CD | CDi | CDo | CMy | L/D | H_max | area_frac_cf_neg | t run [s] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 91 | 0,1905 | 0,0129 | 0,0009 | 0,0120 | −0,0980 | 14,77 | 3,381 | 0 | 16,4 |
| 2 | 0 | 91 | 0,3838 | 0,0155 | 0,0034 | 0,0121 | −0,1484 | 24,76 | 3,356 | 0 | 17,4 |
| 4 | 0 | 91 | 0,5767 | 0,0202 | 0,0077 | 0,0125 | −0,1993 | 28,55 | 3,9155 | 0,0175 | 16,3 |
| 6 | 0 | 92 | 0,7690 | 0,0279 | 0,0137 | 0,0142 | −0,2502 | 27,56 | 3,9155 | 0,0303 | 18,3 |
| 8 | 0 | 92 | 0,9605 | 0,0383 | 0,0213 | 0,0170 | −0,3009 | 25,08 | 3,9155 | 0,0394 | 16,3 |
| 10 | 0 | 93 | 1,1510 | 0,0502 | 0,0306 | 0,0196 | −0,3515 | 22,93 | 3,9155 | 0,0707 | 19,4 |
| 12 | 0 | 96 | 1,3403 | 0,0642 | 0,0416 | 0,0226 | −0,4016 | 20,88 | 3,9155 | 0,0749 | 16,4 |

- Tutti status 0, convergenza in 91–96 iterazioni; `sep_max` = 0 ovunque. Tempo per design 16–19 s
  (≈ 16 s di FlightStream), 7 design in ≈ 2 minuti.
- aoa = 4 **coincide** con il riferimento (e con A).
- dCL/dα (regressione 0–8°) = **5,515 /rad** (0,0963 /deg), R² = 0,999997, α(CL=0) ≈ −1,99°. Teoria
  dell'ala finita con a₀ = 2π, AR = 15,3: linea portante ellittica 5,557 /rad (−0,8 %), Helmbold 5,515 /rad
  (coincide). Pendenze locali da 5,54 (0–2°) a 5,42 (10–12°): leggera diminuzione, nessuno stallo.
- **Vicino allo stallo**: CL resta lineare fino a 12° e L/D massimo è a 4° (28,5). Con
  `viscous_coupling = false` lo strato limite non retroagisce sulla portanza: il metodo **non predice
  lo stallo**, e status 0 non vuol dire che il punto sia fisicamente credibile ad alto aoa. Segnali di
  separazione incipiente: `area_frac_cf_neg` sale da 0 a 7,5 %.
- **`H_max` è saturato**: 3,9155 è un valore massimo imposto da FlightStream (a 4° ci sono 358 facce su
  15262 esattamente a quel valore, a 12° ce ne sono 2522, anche vicino al bordo d'attacco). Come
  indicatore di stallo `H_max` non serve; meglio la frazione d'area con H al limite.

### 3.4 DOE `ccs_wing`, aoa 4 (`python heeds_mock.py --config case_semiala_ccs.json --var chord_scale=0.9,1.0,1.1 --out mock_runs_ccs`)

| chord_scale | Sref [m²] | Lref [m] | Re_ref | CL | CD | CDi | CDo | L_N [N] | D_N [N] | L/D | xtr_up | t [s] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0,9 | 1,63987 | 0,31058 | 427487 | 0,5870 | 0,0200 | 0,0073 | 0,0127 | 235,84 | 8,035 | 29,35 | 0,387 | 28,4 |
| 1,0 | 1,82208 | 0,34509 | 474985 | 0,5767 | 0,0202 | 0,0077 | 0,0125 | 257,45 | 9,017 | 28,55 | 0,378 | 26,6 |
| 1,1 | 2,00429 | 0,37960 | 522484 | 0,5678 | 0,0203 | 0,0082 | 0,0121 | 278,82 | 9,968 | 27,97 | 0,375 | 27,7 |

Tutti status 0 (91–92 iterazioni). Coerenza fisica verificata:
- Sref, Lref e Re esattamente proporzionali a `chord_scale` (apertura fissa).
- L_N cresce (+8,4 % per +10 % di corda), meno che in proporzione perché l'allungamento cala (AR 17,0 → 15,3
  → 13,9) e con lui CL: −1,5 % / +1,8 % contro ∓1,2 % della linea portante (2π/(1+2/AR)), stessa direzione.
- CDi segue CL²/(π·e·AR) con e ≈ 0,90 costante (0,0072 / 0,0077 / 0,0082 previsti); CDo cala con il Re
  (0,0127 → 0,0121); D_N e L/D si comportano di conseguenza (L/D cala perché AR cala).
- La transizione sul dorso anticipa con il Re (xtr_up 0,387 → 0,375), come atteso.

### 3.5 Diagnosi degli indicatori di strato limite (VTK del DOE fixed, aoa 0/4/8/12; `diagnostica\`)

Metà ala (y ≥ 0, 7631 celle). x/c rispetto alla corda locale; "dorso"/"ventre" dal segno della normale
esterna (vicino al bordo d'attacco il "ventre" geometrico comprende la zona tra il ristagno e il bordo
d'attacco); η = y/(b/2).

**cf < 0** (% dell'area dell'insieme per lato, fascia di corda, fascia di apertura):

| aoa | celle | % area | dorso | ventre | x/c 0–5 | 5–20 | 20–80 | 80–100 | η 0–0,2 | 0,2–0,4 | 0,4–0,6 | 0,6–0,8 | 0,8–0,95 | 0,95–1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | – | – | – | – | – | – | – | – | – | – | – | – |
| 4 | 186 | 1,75 | 14 | 86 | 0 | 0 | 14 | 86 | 24 | 19 | 19 | 24 | 13 | 0 |
| 8 | 624 | 3,94 | 0 | 100 | 0 | 0 | 0 | 100 | 22 | 22 | 20 | 21 | 13 | 2 |
| 12 | 1306 | 7,49 | 35 | 65 | 21 | 14 | 0 | 65 | 20 | 21 | 20 | 21 | 16 | 3 |

**H al tetto (3,9155)**: praticamente le stesse celle (179 di 186, 624 di 624, 1261 di 1306 sono anche cf < 0):
% area 0 / 1,51 / 3,94 / 7,16; a 4° e 8° tutte sul ventre a x/c > 0,8; a 12° 33 % sul dorso a x/c < 0,2 e
67 % sul ventre a x/c > 0,8. Distribuzione in apertura uniforme fino a η ≈ 0,95, quasi nulla all'estremità.

Conclusioni:
- **cf < 0 e H al tetto sono lo stesso fenomeno**: quando il solutore integrale arriva alla separazione
  porta cf sotto zero e blocca H a 3,9155 (fuori dalle celle al tetto H massimo = 3,38 / 3,73 / 3,39 / 3,91 a 0 / 4 / 8 / 12°).
- **(b) Il segno di cf non è riferito alla corrente libera.** Le 525 celle tra il ristagno e il bordo
  d'attacco (a 12°: ventre, x/c ≤ 0,028, Vx < 0) hanno tutte cf > 0 (minimo +0,0006); nessuna cella con cf < 0
  ha Vx < 0 (0 su 1306). Le 257 celle con cf < 0 a x/c < 5 % (solo a 12°) stanno tutte sul **dorso**, a
  x/c 0,021–0,049, **a valle** del picco di aspirazione (x/c ≈ 0,005), con Vx ≈ +34 m/s: è una bolla di
  separazione laminare di bordo d'attacco, non un artefatto del ristagno. cf è riferito alla direzione
  della linea di corrente superficiale che parte dalla linea di attacco.
- **Ventre al bordo d'uscita (x/c 0,90–1,0)**: tra x/c ≈ 0,88 e il bordo d'uscita Cp sale (es. da +0,15 a
  +0,40 a 8°: bordo d'uscita arrotondato, `blended`). Lo strato limite del ventre è ancora transizionale
  (Transition_marker 0,7–0,95) e separa; a 4° e 8° si riattacca turbolento (H scende a 1,4, tr = 1), a 12°
  resta separato fino al bordo d'uscita. La zona cresce con aoa perché il ventre resta laminare più a lungo
  (tr a x/c 0,88: 0,94 / 0,81 / 0,71 a 4 / 8 / 12°). Parte di questo effetto può dipendere dal bordo
  d'uscita arrotondato nel metodo a potenziale (da verificare).
- **Dorso a 4°**: 7 celle con cf < 0 a x/c ≈ 0,40 subito prima della transizione (bolla laminare corta).
- **(c) Transition_marker** è quasi sempre intermedio (=0 in ~100 celle, =1 in ~2800–3500, il resto tra 0 e
  1). Nelle celle al tetto: nessuna con tr < 0,01, 6–21 con tr > 0,99, tutte le altre "transizionali"
  (mediana 0,95 / 0,89 / 0,82 a 4 / 8 / 12°; con soglia 0,5: 1 sola cella "laminare"). Sono quindi
  separazioni laminari/transizionali (bolle), non separazioni turbolente.
- **(d) Separation_marker = 0 in tutte le celle a tutti gli angoli**; `sep_max` = 0. Per il manuale indica
  le separazioni turbolente e, senza un modello di separazione assegnato (nel .fsm non c'è), non scatta.
- **`area_frac_cf_neg` oggi misura soprattutto le bolle laminari del ventre al bordo d'uscita**, non lo
  stallo del dorso; `H_max` vale 3,9155 appena compare una separazione, quindi non dice quanto è estesa.

**(e) Manuale 26.1** (testo estratto dal PDF installato; pagine del PDF):
- p. 244–245, "Boundary Layer Parameters": *Transition Marker* "Value of zero indicates fully laminar flow
  and unity value indicate fully turbulent flows. Values in between zero and unity are locations of
  transitional flow." *Shape Factor* "Shape factor of the boundary layer in non-dimensional value"
  (**nessun limite dichiarato**). *Skin Friction Coefficient* "computed from the boundary layer
  characterstics at each solver face" (**né segno né direzione dichiarati**). *Separation marker* "Value of
  zero indicates fully attached flows and unity value indicate fully separated turbulent flows. Values in
  between zero and unity are locations of attached lows on the verge of separation." *Streamline Length*
  "measured from the attachment locations" (coerente con cf riferito alla linea di corrente).
- p. 248 e 251 (export di sonde e sezioni): "CF Skin friction coefficient based on global reference
  velocity" (normalizzazione, non il segno). p. 248 chiama "Transition" una colonna descritta come
  "locations of flow separation" e p. 348 (comando `SET_SCENE_CONTOUR`) descrive `transition` come
  "Boundary layer laminar separation marker": il manuale è incoerente su questa variabile.
- p. 205: in modalità *Decoupled* (default, `viscous_coupling = false`) "This mode will only generate
  linear aerodynamic loads". p. 205/208: senza un *Flow separation model* "the aerodynamic loads and
  moments will not stall, despite the enabling of viscous coupling".
- p. 207: modello *Airfoil* (criterio di Stratford, opzionale Valarezo), applicabile "with either solver
  viscous modes independently". Comando `CREATE_AIRFOIL_SEPARATION <NAME> <NUM_BOUNDARIES>
  <VALAREZO_CRITERION>` (p. 340–341). p. 221/344: `LAMINAR_SEPARATION ENABLE` "Enable Laminar boundary
  layer separation model for low-Re flows".

### 3.6 Processi, timeout, licenza e spazi (Parte 4, v2.2.3; cartelle `test_P4_*` e `C:\fs test\` cancellate dopo la copia di questi dati)

| Test | Esito | Tempo |
|---|---|---|
| Run reale fixed 4° con campionamento dei processi ogni 0,1 s | status 0, CL 0,5767; un solo `FlightStream.exe` (figlio di python), nessun figlio, nulla rimasto | 17,7 s |
| Timeout reale 5 s (kill durante il checkout della licenza) | status 2; nessun FlightStream rimasto (solo `taskkill.exe` tra i figli) | 5,6 s |
| → run normale subito dopo | status 0, CL 0,5767, 91 iterazioni | 16,7 s |
| Timeout reale 10 s (kill all'iterazione 9, licenza già presa) | status 2; nessun FlightStream rimasto | 10,7 s |
| → run normale subito dopo (licenza rilasciata) | status 0, CL 0,5767 | 16,7 s |
| Licenza: solo `ALTAIR_LICENSE_PATH=6200@server-inesistente.invalid` | status 0 (la licenza hosted HWU ignora la variabile) | 12,7 s |
| Licenza: `ALTAIR_LICENSE_PATH` inesistente + `ALM_HHWU=F` | status 6 dopo 3 tentativi (≈ 16 s ciascuno) + 2 × 60 s di attesa; nessun processo rimasto | 169,9 s |
| Spazi, fixed: `heeds_mock --root "C:\fs test\DOE aoa"` | status 0, CL 0,5767, Re 474985 | 20,7 s |
| Spazi, ccs_wing: `--root "C:\fs test\DOE ccs"` (`FILE C:\fs test\...\case_ccs.csv`) | status 0, CL 0,5767, Re 474985, sep_frac_lo_te 0,0306 | 14,7 s |
| Test automatici (16, di cui 3 in `tests/test_processes.py`) | tutti OK | 36 s |

Testo di FlightStream senza licenza (`fs_stdout.txt`, nessun `FlightStreamLog.txt`):
`Checking out Altair units...Not available. Attempting EDU feature checkout...Not available.
Attempting feature license checkout...Not available.`

### 3.7 Baseline per HEEDS (v2.3.0, run reali con `run_fs.bat` in `baseline_runs\<modalità>\Design_1\Analysis_1`)

| Grandezza | Riferimento | baseline fixed (aoa 4) | baseline ccs (chord_scale 1,0, aoa 4) |
|---|---|---|---|
| status / codice di uscita | – | 0 / 0 | 0 / 0 |
| iterazioni | 91 | 91 | 91 |
| CL | 0,5767 | 0,5767 | 0,5767 |
| CDi | 0,0077 | 0,0077 | 0,0077 |
| CDo | 0,0125 | 0,0125 | 0,0125 |
| CMy | −0,1993 | −0,1993 | −0,1993 |
| Re | 474985 | 474985 | 474985 |
| L/D, L_N | – | 28,5495, 257,444 N (Sref 1,82208, v2.3.1) | 28,5495, 257,445 N (Sref calcolata 1,82208203) |
| sep_frac_up_le, x_sep_up, sep_frac_lo_te | – | 0; 0,398; 0,0306 | 0; 0,398; 0,0306 |
| tempo (FlightStream) | – | 27,9 s (26,7 s; v2.3.1) — prima 37,8 s | 45,4 s (43,8 s) |

**v2.3.1:** `reference.sref_m2` del JSON fixed = 1,82208 (Sref geometrica calcolata in `ccs_wing`, per
coerenza tra le due modalità; prima 1,8221 come nel run di riferimento). Baseline fixed rilanciata:
coefficienti identici, cambiano solo `Sref_m2` (1,82208), `L_N` (257,444) e `D_N` (9,01747); la differenza
residua con ccs alla 6ª cifra viene dalle cifre di Sref oltre la quinta (1,82208203).
`heeds_inputs\<fixed|ccs>\params.txt` e `results.txt` sono le copie delle baseline con i nomi che HEEDS
usa (legge l'output con lo stesso nome del file taggato).

**Tempi e thread.** I tempi della sera sono più alti di quelli del pomeriggio (solver 0,275 / 0,17 min
contro 0,079–0,094 min, inizializzazione 4,7–11,9 s contro 2,1 s) **a pari numero di thread**: tutti gli
script, pomeriggio e sera, contengono `SET_MAX_PARALLEL_THREADS 6` (`solver.threads = 0` → metà dei 12
core logici). Il driver quindi fissa già i core (comando 26.1: `SET_MAX_PARALLEL_THREADS <NUM_CORES>`,
manuale p. 339; in alternativa la variabile `OMP_NUM_THREADS`, p. 20, e `KMP_AFFINITY=norespect` per più
socket, p. 21). FlightStream non scrive nel log quanti thread usa davvero. La differenza è da attribuire
al carico o allo stato del PC (alimentazione, temperatura, altri processi): DA VERIFICARE.
`run_info_baseline.txt` di ccs riporta "fs_driver v2.2.3" (lanciata prima del passaggio del numero di
versione; stesso codice).

### 3.8 Primo Evaluation Only in HEEDS (2026-10-04, HEEDS MDO 2604.0)

Progetto `C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala.heeds`, studio
`semiala_Study_1` ("Evaluate baseline design", lanciato dall'utente): 1 design, 0 errori, 53 s;
status 0, CL 0,5767, CD 0,0202, CMy −0,1993, L/D 28,5495, aoa 4 — uguale al riferimento.
Configurazione: portale General (no portals), Compute resource Local, **variante A** (Execution command
`<REPO>\run_fs.bat`, Command options `--config "<REPO>\case_semiala_fixed.json"`), 1 design alla volta,
Run in = Analysis folder, input `heeds_inputs\fixed\params.txt`, output `heeds_inputs\fixed\results.txt`,
tagging delimitato (aoa riga 4; status/CL/CD/CMy/L_over_D righe 2/5/6/10/12, colonna 2), Max execution
time 1200 s, Default decimal delimiter = Period, If an error occurs = "Stop process for current design,
discard design data" (default), Capture analysis output spuntato. Study_1 di default = SHERPA (35
valutazioni): senza obiettivo "The study contains setup errors"; risolto con Maximize `L_over_D`.

Controllo sui file del design (Parte A, sola lettura), cartella
`semiala_Study_1\HEEDS_0\Design1\Analysis_1`:
- `params.txt` scritto da HEEDS: `aoa = 4.00000` (punto decimale, 5 decimali; commenti e altre righe intatti).
- `results.txt`: 39 righe, stesse chiavi, stesso ordine e **stessi valori** di `heeds_inputs\fixed\results.txt`.
- Tempi (`POST_0\Design1\Analysis_1\Analysis.log` e output catturato): studio 52,7 s (22:23:55,45 →
  22:24:48,13); comando `run_fs.bat` 50,6 s; FlightStream 48,9 s (inizializzazione 14,1 s, solver
  0,294 min = 17,6 s); **driver ≈ 1,7 s; HEEDS ≈ 2,1 s** (pulizia di `HEEDS_0`/`POST_0` e dei risultati
  prima, estrazione delle 5 risposte dopo, ≈ 0,05 s). FlightStream resta lento la sera (16 s nel
  pomeriggio), sempre con `SET_MAX_PARALLEL_THREADS 6`.
- Codice di uscita del comando registrato da HEEDS: 0 (`.aux\Process_execution_actions.log`).
- Nessun `FlightStream.exe` rimasto.
- File di HEEDS nella cartella dello studio: elenco e uso in HEEDS_SETUP, "Dove guardare quando un design
  fallisce". Da `HEEDS0.rpt`: `successCondition: NONE`, `saveDesigns: LatestBest`, `saveErrorDesigns:
  saveOnly`, `dontStopOnDesignErrors: no`, `aoa` continua 0–12 con Resolution 101. HEEDS copia
  `params.txt` nella cartella del progetto e usa quella copia. Rilanciando uno studio, HEEDS cancella le
  sue cartelle `HEEDS_0` e `POST_0`.

DA VERIFICARE risolti: variante A (`.bat` diretto, `cmd /c` non serve); nomi dei file; tagging per
posizione; separatore decimale (Period; opzioni "From portal", "Period", "Comma"); Max execution time;
testo di default di "If an error occurs".

DA VERIFICARE ancora aperti: Success condition non ancora configurata (procedura dal manuale in
HEEDS_SETUP passo 6: "Compare analysis successful return value" = 0 nelle Advanced Options + condizione
"File contains" assegnata come Success); se le due si sommano in AND (implicito nel manuale); come
scegliere il file e gli spazi nel testo di "File contains"; Stop durante un run e FlightStream orfani;
comportamento di un design in errore (Rename in `Design<X>-ERROR`); elenco completo delle opzioni di
"If an error occurs" (il manuale dice solo "stop the process or continue to the next analysis"); se il
Max execution time chiude il comando; durata del token Altair One.

Dal manuale HEEDS (`MDO\docs\en\HEEDSMDO.pdf`, testo estratto con pypdf in un venv temporaneo):
il Full factorial esiste solo a 2 e 3 livelli; per aoa = 0, 2, …, 12 si usa lo **Sweep** (Define Variable
Sweep: Min, Max, # values) in uno studio **Evaluation Only - User prescribed** (consigliato) o DOE con
**Custom sampling (RSM only)**. "Do not stop HEEDS for a design-based error" (Study tab) è l'opzione che
fa proseguire i DOE con errori. Dettagli e pagine in HEEDS_SETUP passi 5, 6, 8, 9.

### 3.9 Verifica dello sweep, preflight, demo (v2.4.0, 2026-10-05)

- `heeds_report.py --check-against-mock <summary.csv> --expect-n 7 --expect-aoa 0,2,…,12`: per ogni design a
  status 0 confronta CL, CD, CMy, L_over_D con il punto del DOE mock allo stesso aoa (tolleranza relativa
  1e-4, `--rtol`), conta i design, controlla i valori di aoa, i design `-ERROR` e che non ci sia un
  FlightStream attivo; scrive `report\verifica.md`; ultima riga VERIFICA OK / VERIFICA FALLITA, codice 0/1.
  Prove: DOE mock contro sé stesso → OK (7 PASS, diff 0); Study_1 (1 design a 4°, `--expect-n 1
  --expect-aoa 4`) → OK; copia del mock con CL a 6° 0,769 → 0,7691 → FALLITA (`aoa = 6: CL diff 1.30e-04`).
  Calcola anche dCL/dα tra 0 e 8°.
- `preflight.bat` → `PREFLIGHT OK` (17 voci; il `.bat` esegue la riga `set "PY=..."` di `run_fs.bat`, quindi
  usa lo stesso interprete). Con un `FlightStream.exe` attivo: `ERRORE` e codice 1 (test).
- **Sicurezza dei test sui processi (corretto in v2.4.0):** prima il `tearDown` di `test_processes.py` chiudeva
  tutti i `FlightStream.exe` e il test di `kill_stale_flightstream` faceva chiudere al driver ogni
  `FlightStream.exe`: lanciando i test durante uno studio HEEDS si sarebbe potuto chiudere un FlightStream
  vero. Ora i finti si chiamano `FlightStreamProva.exe`, il driver dei test cerca solo quel nome e ogni
  test chiude solo i processi che ha avviato (il test di preflight usa una copia `FlightStream.exe` e la
  chiude da sé; viene saltato se c'è un FlightStream vero attivo).
- HEEDS_SETUP: procedura del test di errore con `--dry-run` (esito atteso; la sola condizione "File
  contains" non basta perché anche il `results.txt` del dry-run contiene `schema_version = 2`), preflight e
  verifica, comando batch `HEEDSMDO.exe -b <progetto>.heeds -cmd=RunStudy -study=Study_2` (manuale §9, PDF
  p. 1084–1085; non provato, DA VERIFICARE con la GUI aperta).

### 3.10 Sweep HEEDS su aoa: Study_2 (v2.4.1, eseguito dall'utente il 2026-10-04 sera)

Studio `C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala_Study_2`, "Evaluation Only - User
prescribed", Sweep di aoa 0–12 con 7 valori (`method: DesignSweep`, `saveDesigns: All`,
`saveErrorDesigns: saveAndRename`, `dontStopOnDesignErrors: yes`, `successReturnValue: 0`).
Verifica (`heeds_report.bat --check-against-mock mock_runs\summary.csv --expect-n 7 --expect-aoa
0,2,4,6,8,10,12`, report in `Desktop\fs_heeds_pipeline\reports\semiala_Study_2`, copia in
`fs_heeds_pipeline\demo\`): **VERIFICA OK**.

| aoa | CL | CD | CMy | L/D | diff. rel. max contro il mock | tempo design / FlightStream [s] |
|---|---|---|---|---|---|---|
| 0 | 0,1905 | 0,0129 | −0,0980 | 14,77 | 0 | 33,3 / 32,1 |
| 2 | 0,3838 | 0,0155 | −0,1484 | 24,76 | 0 | 27,7 / 26,7 |
| 4 | 0,5767 | 0,0202 | −0,1993 | 28,55 | 0 | 40,1 / 38,4 |
| 6 | 0,7690 | 0,0279 | −0,2502 | 27,56 | 0 | 32,1 / 31,0 |
| 8 | 0,9605 | 0,0383 | −0,3009 | 25,08 | 0 | 26,7 / 25,6 |
| 10 | 1,1510 | 0,0502 | −0,3515 | 22,93 | 0 | 27,6 / 26,7 |
| 12 | 1,3403 | 0,0642 | −0,4016 | 20,88 | 0 | 31,0 / 29,9 |

- dCL/dα (0–8°): **5,5153 /rad** (0,09626 /deg), uguale al DOE del driver e a Helmbold (5,515); linea
  portante 5,557 (−0,8 %). L/D massimo 28,55 a 4° (passo 2°).
- Tempi: media 31,2 s a design (FlightStream 30,1 s, driver + HEEDS ≈ 1,1 s); studio intero 220 s.
- `params.txt` scritto da HEEDS: 6 cifre significative (`aoa = 0.00000`, `aoa = 10.0000`).
- Grafici controllati a vista: assi e unità corretti, punti HEEDS sovrapposti al mock. Corretto in
  `heeds_report.py`: la retta di Helmbold era coperta dalla linea dei punti e non aveva il nome in
  legenda (ora nera, sopra, "Helmbold (AR 15,3)"; opzione `--slope-label`).

DA VERIFICARE risolti (dall'utente in HEEDS):
- **Controllo del codice di uscita:** Analysis_1 → Execution → riquadro Analysis Execution Options → campo
  **Conditions** → Condition Event **Success** → casella **"Compare analysis successful return value"** = 0
  (non nelle Advanced Options, come avevo dedotto dal manuale). Provato: un design con codice di uscita 1
  diventa errore, messaggio *"The return value (1) for the analysis command did not match the specified
  value (0). This design analysis will be marked as an error."* (nella prova `--dry-run` era finito per errore
  dentro le virgolette del JSON: il driver non ha trovato il file, codice 1, design in errore lo stesso).
- **Procedura dello Study_2:** Create Study → Evaluation Only - User prescribed → Methods → **+ Design Set**
  (senza set i pulsanti Design/Sweep/Fill sono grigi) → **Sweep...** (Min 0, Max 12, # values 7) →
  **Replace** → `sweep_1`…`sweep_7`; colonne **Map** e **Show Resp.** NON spuntate; Saved Designs e Run
  Options nella pagina dello studio, non in More options.
- **Rilancio di uno studio con risultati:** HEEDS chiede **Unlock**, poi le opzioni di run (Erase existing
  study results).

Ancora aperti: condizione "File contains" `schema_version = 2` (non configurata, `successCondition: NONE`;
facoltativa); se casella e condizione si combinano in AND; Stop durante un run e FlightStream orfani; Max
execution time (chiude il comando? come tratta il codice di uscita?); elenco delle opzioni di "If an error
occurs"; durata del token Altair One; comando batch `HEEDSMDO.exe -b … -cmd=RunStudy` (non provato).

Script registrato (`...\heeds\semiala_fixed\record_study2.py`, punto 7 del piano, API HEEDS): contiene
`HEEDS.currentProject()`, `project.findChild('Study_1', HEEDS.Study)`, `project.createStudy(name='Study_2',
studyType='EVAL', fromStudy=Study1, copyPost=0, copyResponses=0, copyVariables=1)`,
`Study2.createUserDesignSet('Set_1')`, `Set1.sweep(aoa=(0, 12, 7), replace=True)`,
`Study2.set('saveErrorDesigns', 'saveAndRename')`, `Study2.set('RunOpt_SkipFirstEvalCheck', True)`,
`project.save(...)`, `Study2.run(results=None, wait=True)`. **Nessun tagging** (variabili e risposte erano
già definite nel processo prima della registrazione) e nessuna impostazione di Saved designs = All (default
dello studio EVAL o non registrata: DA VERIFICARE). Fattibile creare e lanciare studi da script; il tagging
va ancora cercato nell'API.

### 3.11 Punto 4 del piano: accoppiamento viscoso e separazione — Parte A, lettura del manuale (2026-10-05)

**ESPLORATIVO, NON VALIDATO:** nessuna conclusione quantitativa sullo stallo finché non ci sono il confronto con
XFOIL e la convergenza di mesh. Fonte: manuale installato `C:\Program Files\Altair\2026.1\flightstream\Altair
FlightStream User Manual.pdf` (riestratto il 2026-10-05: testo identico a quello usato finora, 409 pagine).
- `SET_SOLVER_VISCOUS_COUPLING <ENABLE/DISABLE>` (p. 340). Coupled = run inviscido fino a convergenza, poi
  **secondo run** con lo strato limite accoppiato (p. 205); senza modello di separazione niente stallo.
- `SET_BOUNDARY_LAYER_TYPE LAMINAR|TRANSITIONAL|TURBULENT` (p. 340): TRANSITIONAL valido per Re di corda
  500 000–1 500 000, TURBULENT oltre 1 500 000 (p. 203). `SET_SURFACE_ROUGHNESS <nm>` (p. 340, tabella p. 204).
  Transizione forzata: in scripting solo `DELETE_TRANSITION_TRIP` (p. 326); creazione da GUI, file di vertici
  (p. 193) o parametro CCS `BL_Transition;u1;u2;v1;v2` (p. 85).
- `CREATE_AIRFOIL_SEPARATION <NAME> <NUM_BOUNDARIES> <VALAREZO_CRITERION>` + riga con gli indici (o `-1` = tutte),
  `DELETE_SEPARATION <INDEX|-1>` (p. 340–341); criterio di **Stratford** (+ Valarezo opzionale, per ali con
  freccia > 10° o ipersostentatori); pressione semi-empirica sulle facce separate a fine run; **indipendente**
  dalla modalità viscosa (p. 207–208). `LAMINAR_SEPARATION <ENABLE/DISABLE>` esiste nella 26.1 (p. 344,
  "Laminar boundary layer separation model for low-Re flows", p. 221).
- Carichi: solo CDi (vorticità o pressione) e CDo (attrito); **nessuna CDp** (p. 223–224). Il manuale non descrive
  il log della fase accoppiata: da vedere su un run reale (Parte B).

### 3.12 Punto 4: accoppiamento viscoso e separazione — Parti B e C (v2.5.0, 2026-10-05)

**ESPLORATIVO, NON VALIDATO.** Nessuna conclusione quantitativa sullo stallo finché non ci sono il confronto
con XFOIL e la convergenza di mesh. Re = 4,7·10⁵, sotto il campo del modello transizionale (5·10⁵–1,5·10⁶).

Implementazione:
- JSON: `solver.viscous_coupling` (esistente), blocco `separation` = {`model` "none"|"airfoil", `surfaces` [1]
  o -1, `valarezo`, `laminar_separation`}; tipo di strato limite e rugosità restano `solver.bl_type` e
  `solver.roughness_nm`. Lo script scrive sempre `DELETE_SEPARATION -1` e `LAMINAR_SEPARATION`, e con
  "airfoil" `CREATE_AIRFOIL_SEPARATION AIRFOIL_SEP 1 DISABLE` + `1`, tutti prima di `INITIALIZE_SOLVER`
  (nessun errore di FlightStream).
- Log in modalità accoppiata: **due tabelle di iterazioni**, la numerazione continua nella seconda (es. 91
  inviscide, poi 92…126). `iterations_inviscid`, `iterations_viscous`, `converged_viscous` (residui finali di
  entrambe le fasi sotto la soglia); se la fase viscosa non converge o manca: **status 3**.
- Schema 3: righe 40–45 `viscous_coupling separation_model iterations_inviscid iterations_viscous
  converged_viscous sep_marker_frac_up` (frazione del dorso con `Separation_marker` ≥ 0,5). Nessuna CDp:
  FlightStream non la fornisce.
- **Regressione:** run reale fixed 4° con i default → righe 2–39 identiche byte per byte alla baseline; nuove
  baseline fixed e ccs (schema 3) con righe 2–39 identiche alle precedenti.
- JSON di esempio (dalla v2.6.0 in `configs/esplorativi/`): `case_semiala_fixed_coupled.json` (C), `case_semiala_fixed_coupled_sep.json` (CS),
  `run.timeout_s = 450` (≈ 10 × il tempo nominale dei run accoppiati, 33–57 s).

**Parte B, run a un punto (fixed):**

| conf, α | CL | CD | CDi | CDo | CMy | L/D | iter. inviscide + viscose | tempo FS [s] | sep_frac_up_le | x_sep_up | Separation_marker |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D 4° | 0,5767 | 0,0202 | 0,0077 | 0,0125 | −0,1993 | 28,55 | 91 + 0 | 21,5 | 0 | 0,398 | 0 ovunque |
| C 4° | 0,5515 | 0,0196 | 0,0071 | 0,0125 | −0,1877 | 28,14 | 91 + 35 | 26,7 | 0 | 0,398 | 0 ovunque |
| CS 4° | 0,5536 | 0,0196 | 0,0071 | 0,0125 | −0,1897 | 28,24 | 91 + 35 | 33,9 | 0 | 0,398 | max 1; ≥ 0,5 sul 48 % del dorso, x/c 0,44–1,00, η 0,01–1,00 |
| D 12° | 1,3403 | 0,0642 | 0,0416 | 0,0226 | −0,4016 | 20,88 | 96 + 0 | 35,2 | 0,052 | 0,021 | 0 ovunque |
| C 12° | 1,1529 | 0,0537 | 0,0325 | 0,0212 | −0,3133 | 21,47 | 96 + 70 | 45,6 | 0,052 | 0,021 | 0 ovunque |
| CS 12° | 1,2352 | 0,0537 | 0,0325 | 0,0212 | −0,3600 | 23,00 | 96 + 70 | 26,6 | 0,052 | 0,021 | max 1; ≥ 0,5 sull'89 % del dorso, x/c 0,08–1,00, η 0,01–1,00 |

**Parte C, DOE fixed α = 0, 2, …, 10, 11, …, 18 (14 punti), `heeds_mock.py`** (cartelle `mock_runs_visc_D|C|CS`,
grafici e riepilogo in `fs_heeds_pipeline\diagnostica\doe_viscoso\`):

| conf | design ok | dCL/dα 0–8° [/rad] | CL esce dalla linearità | CL_max (α) | non riusciti | tempo medio (min–max) [s] |
|---|---|---|---|---|---|---|
| D | 14/14 | 5,515 | mai (−1,3 % a 18°) | 1,899 (18°, limite del DOE) | – | 38,5 (29,7–52,6) |
| C | 13/14 | 5,145 | 10° (−4 %), poi −9,5 % a 14° e di nuovo verso la retta (−3,9 % a 18°) | 1,731 (18°, limite del DOE) | 2°: status 2 (timeout, FlightStream fermo dopo l'iterazione 118 con residui già sotto soglia; ripetuto: OK in 33 s, CL 0,3666) | 51,8 (41,8–57,4) |
| CS | 14/14 | 5,033 | 10° | **1,266 a 13°**, poi CL ≈ 1,14–1,10 da 14° a 18° | – | 36,9 (32,7–41,1) |

Osservazioni (esplorative):
- **C (accoppiato, senza separazione):** decambering viscoso (CL −4 % a 4°), nessuno stallo come dice il
  manuale; la curva non è monotona nella sua deviazione dalla retta (massima a 14°, poi CL torna a salire più
  ripido): comportamento da capire.
- **CS:** il modello Airfoil produce un massimo di CL a 13° e un plateau dopo, senza oscillazioni (CL scende
  in modo monotono, 0 cambi di segno di dCL dopo il massimo). **Ma:**
  - la separazione agisce solo come **correzione della pressione dopo il run**: il CL del log è uguale a quello
    di C, cambia solo la tabella dei carichi (CL, CMy);
  - **CD e CDi sono identici fra C e CS a ogni α**: la separazione non produce resistenza (CDi da vorticità,
    CDo da attrito); il calo di L/D dopo lo stallo viene solo dal calo di CL;
  - prima del massimo CS ha CL **più alto** di C (11–13°): la separazione aumenta la portanza, poco credibile;
  - `Separation_marker` ≥ 0,5 copre già il 18 % del dorso a 0° e il 48 % a 4° (da x/c ≈ 0,44, cioè dalla
    transizione): il criterio di Stratford sembra scattare dove lo strato limite è appena transizionale, a un Re
    sotto il campo del modello. `sep_marker_frac_up` non distingue quindi una separazione reale.
- Il blocco di FlightStream in C a 2° (nessun output per oltre 9 minuti con residui già sotto soglia, non
  ripetibile) è gestito dal driver come status 2: questi design vanno rilanciati.
- Da fare prima di usare questi risultati: convergenza di mesh, confronto con XFOIL a Re 4,7·10⁵ (anche con
  `laminar_separation`), prova di `SET_VORTICITY_DRAG_BOUNDARIES` disattivato (CDi da pressione) per vedere se
  la separazione entra nella resistenza (fatto in §3.13).

### 3.13 Punto 4 bis: diagnosi del modello di separazione + riferimento XFOIL (v2.5.1, 2026-10-05)

**SOLO DIAGNOSTICA.** Nessun JSON di produzione toccato; unica modifica al driver: `solver.vorticity_drag_boundaries = []`
→ `DELETE_VORTICITY_DRAG_BOUNDARIES` (CDi dall'integrazione della pressione, manuale p. 202 e 349), con test.
**Regressione D** (fixed 4°, default, run reale): `results.txt` identico byte per byte alla baseline (45 righe).
File: `fs_heeds_pipeline\diagnostica\separazione\` (`run_varianti.py`, `config\case_<variante>.json`, `analisi_varianti.py`,
`analisi.md`, `tabella_varianti.csv`, grafici; cartelle dei run in `runs\`, fuori dal repo) e `fs_heeds_pipeline\reference\xfoil\`.
CS, C, D: run del DOE di v2.5.0 (`mock_runs_visc_*`), non rifatti. 20 run nuovi, tutti status 0, 33–43 s ciascuno.

**Parte 1 – varianti di CS** (striscia di celle a η = 0,492; x_tr = primo Transition_marker ≥ 0,99; la tabella completa
con CDi, CMy, iterazioni e cl di sezione è in `analisi.md`):

| conf | α | CL log | CL carichi | CD | x_tr | Separation_marker ≥ 0,5 da | = 1 da | frazione dorso ≥ 0,5 |
|---|---|---|---|---|---|---|---|---|
| CS | 0 / 4 / 12 / 16 | 0,182 / 0,551 / 1,153 / 1,517 | 0,183 / 0,554 / 1,235 / 1,111 | 0,0128 / 0,0196 / 0,0537 / 0,0820 | 0,665 / 0,398 / 0,080 / 0,049 | 0,805 / 0,493 / 0,080 / 0,058 | 0,916 / 0,845 / 0,398 / 0,058 | 0,18 / 0,48 / 0,89 / 0,92 |
| CS_Re22 (V 22, Re 522 484) | idem | 0,182 / 0,552 / 1,158 / 1,518 | 0,182 / 0,554 / 1,238 / 1,112 | 0,0128 / 0,0192 / 0,0535 / 0,0814 | 0,628 / 0,398 / 0,068 / 0,049 | 0,805 / 0,493 / 0,080 / 0,049 | 0,916 / 0,845 / 0,398 / 0,049 | 0,18 / 0,47 / 0,89 / 0,92 |
| CS_turb (TURBULENT) | idem | 0,176 / 0,540 / 1,133 / 1,560 | 0,177 / 0,544 / 1,224 / 1,079 | 0,0194 / 0,0260 / 0,0565 / 0,0881 | 0 (LE) | 0,805 / 0,493 / 0,021 / 0,012 | 0,916 / 0,845 / 0,357 / 0,027 | 0,18 / 0,48 / 0,96 / 0,97 |
| CS_lam (LAMINAR_SEPARATION) | idem | = CS | 0,183 / 0,553 / **0,873** / 0,971 | = CS | = CS | 0,493 / 0,320 / 0,012 / 0,008 | 0,916 / 0,845 / **0,016** / 0,008 | 0,22 / 0,55 / 0,97 / 0,97 |
| DS (disaccoppiato + Airfoil) | idem | 0,191 / 0,577 / 1,341 / 1,715 (= D) | 0,191 / 0,577 / 1,313 / 1,155 | 0,0129 / 0,0202 / 0,0641 / 0,0972 | = CS | = CS | = CS | = CS |
| CS_pdrag (CDi da pressione) | idem | = CS | = CS | 0,0128 / 0,0198 / **0,0589** / **0,1251** | = CS | = CS | = CS | = CS |

**Risposta alla domanda:** in **nessuna** variante l'inizio della separazione a 4° si sposta oltre x/c 0,9 o sparisce.
Separation_marker ≥ 0,5 parte da 0,493 e = 1 da 0,845 in CS, CS_Re22, CS_turb, DS e CS_pdrag; CS_lam lo anticipa (0,320).
Quindi la causa **non** è il Reynolds (Re22 ≈ CS), **né** lo strato limite transizionale (con TURBULENT, a valle di
x/c 0,40 il marker è uguale a CS), **né** l'accoppiamento (DS = CS). È **il modello stesso**: il criterio di Stratford
applicato a questa distribuzione di pressione. Dettagli:
- Il Separation_marker **non è binario**: a valle della transizione cresce con continuità (0,39 a x/c 0,40, 0,55 a 0,49,
  1 a 0,845 a 4°). La soglia 0,5 non indica una separazione; lo stato "fully separated" (manuale p. 245) è il valore 1.
  Con TURBULENT il marker è > 0 anche a monte (0,19 a x/c 0,26): il criterio vale solo sullo strato limite turbolento e
  dipende quasi solo dal Cp.
- Anche con marker = 1, FlightStream separa al TE già a 0° (x/c 0,916) e a 4° (0,845). XFOIL non ha separazione
  turbolenta al TE fino a 11° (0,983 a 11,5°, 0,946 a 12°); a 12° FlightStream la mette a 0,398.
- **Problema del VTK:** fra D e C sono identici cella per cella cf, H, Transition_marker e BL_Thickness (differenza 0),
  mentre Cp e velocità cambiano (ΔCp max 0,058 a 4°, 1,18 a 12°). Lo strato limite esportato **non è quello della fase
  accoppiata**: è calcolato sulla pressione della fase inviscida. Anche il Separation_marker è uguale fra CS e DS a ogni α.
  Quindi metriche di strato limite e di separazione lette dal VTK di un run accoppiato non descrivono la soluzione accoppiata.
- La correzione di separazione è solo in **`Cp_reference`** (in CS differisce da `Cp_freestream` fino a 0,12 a 4° e 0,97
  a 12°; in C e D le due coincidono) e in cf (≈ −0,0002 nelle celle separate). Il CL del log è sempre quello senza
  separazione (CS = C, DS = D): la separazione corregge **solo i carichi**, dopo il run.
- **Forma della correzione** (`cp_eta05_C_vs_CS.png`): dove il marker vale 1 il Cp del dorso resta più basso di C (meno
  recupero di pressione, quasi un plateau), mentre il picco al LE resta uguale. Più suzione sul dorso = **più portanza**:
  ecco perché CS ha CL più alto di C prima del massimo (12°: 1,235 contro 1,153). Solo quando la zona separata arriva al LE
  (16°: marker = 1 da x/c 0,058) il CL crolla (1,111 contro 1,517).
- **CDi da pressione** (CS_pdrag): CL e CMy uguali a CS; CDi 0,0073 / 0,0377 / 0,0974 a 4 / 12 / 16° contro
  0,0071 / 0,0325 / 0,0543. Con la CDi da pressione **la separazione entra nella resistenza** (CD a 16°: 0,125 contro 0,082).
  Manca C con CDi da pressione per separare l'effetto del metodo da quello della separazione.
- **LAMINAR_SEPARATION**: a 12° tratta la bolla al LE come separazione completa (marker = 1 da x/c 0,016, CL 0,873,
  −29 % rispetto a CS); in XFOIL la bolla (0,009–0,034) riattacca.
- Transizione a η ≈ 0,5: FlightStream 0,665 / 0,398 / 0,080 a 0 / 4 / 12°; XFOIL allo stesso α 0,755 / 0,478 / 0,030,
  a pari cl di sezione 0,788 / 0,544 / 0,035. A 0–4° FlightStream anticipa la transizione di 0,12–0,15 c e non vede la
  bolla laminare (XFOIL: 0,419–0,462 a 4°).
- Log: FlightStream ristampa l'intestazione della tabella ogni 100 iterazioni. `parse_log` la conta come una fase in più:
  con più di 100 iterazioni inviscide `iterations_inviscid` = 100 invece del valore vero (D 16°: 100 invece di 101; CS 16°:
  `iterations_viscous` 74 invece di 73, e `converged_viscous` legge i residui dell'iterazione 100). Righe 2–39 non toccate.
  **Da correggere** (non fatto qui per non cambiare il comportamento di default).

**Parte 2 – XFOIL 6.99** (`reference\xfoil\summary.md`; eseguibile MIT scaricato in `Desktop\fs_heeds_pipeline\tools\XFOIL6.99\`,
fuori dal repo):
- Profilo dal CCS (`estrai_profilo.py`, `profilo.md`): 200 punti, corda 0,345093 m (Lref 0,345091), corda inclinata di
  +0,037° rispetto a x (non ruotata: α XFOIL = α geometrico FS); TE tozzo **0,652 % c** (2,25 mm); spessore massimo
  **12,18 % c a x/c 0,304**, curvatura massima **1,89 % c a x/c 0,410**. Controllo con il VTK fixed a η = 0,500:
  distanza normale < 8·10⁻⁵ c fino a x/c 0,8 e < 2·10⁻⁴ c fino a 0,91, poi il raccordo del TE della mesh
  (`Blend_trailing_edges`, TE chiuso): 3,3·10⁻³ c al TE.
- **α₀ inviscido −2,000°** contro −1,98° (−CL₀/CLα dello Study_2): scarto 0,02° < 0,2° → profilo verificato.
  Pendenza inviscida 6,954 /rad.
- Re 474985, M 0,059, N 160, ITER 200, Ncrit 9: tutti i 45 punti convergono (Ncrit 7: manca −2,5°; Ncrit 11: tutti).
  α₀ viscoso −2,11°, a₀ 6,435 /rad (−2…6°), **cl_max 1,381 a 15,5°** (Ncrit 7: 1,404 a 14,5°; Ncrit 11: 1,378 a 16°),
  cd_min 0,00657 a 0°, (l/d)_max 85,8 a 5,5°.
- Dorso: bolla laminare a metà corda fino a 4° (0,664–0,742 a 0°, 0,419–0,462 a 4°), transizione naturale 4,5–7,5°,
  bolla al LE da 8° (0,040–0,084, poi sempre più corta), separazione turbolenta al TE da 11,5° (0,983) che risale fino a
  0,631 a cl_max e 0,422 a 18°.

**Confronto dell'innesco** (solo innesco; il confronto completo dopo la convergenza di mesh):

| α | XFOIL x_tr | XFOIL bolla | XFOIL sep. TE | FS (CS = DS = CS_pdrag; CS_Re22 quasi uguale): x_tr / marker ≥ 0,5 / = 1 |
|---|---|---|---|---|
| 0 | 0,755 | 0,664–0,742 | – | 0,665 / 0,805 / 0,916 |
| 4 | 0,478 | 0,419–0,462 | – | 0,398 / 0,493 / 0,845 |
| 12 | 0,030 | 0,009–0,034 | 0,946 | 0,080 / 0,080 / 0,398 |

### 3.14 v2.6.0 – chiusura del lavoro sull'ala (2026-10-05)

Decisioni (dell'utente): configurazione di riferimento **D** (disaccoppiata, separazione `none`); C e CS
esplorative; modello di separazione Airfoil **abbandonato** per quest'ala (resta nel codice, default `none`, da non
usare in HEEDS); metriche H/cf del VTK **qualitative** (strato limite sul Cp inviscido anche nei run accoppiati);
XFOIL non usato in questa fase (`reference\xfoil\` resta com'è).

**Parte 1 – correzioni**
- `parse_log`: una fase nuova solo se l'intestazione è preceduta da due righe di trattini (fine della tabella
  precedente + apertura della nuova); la ristampa ogni 100 iterazioni ne ha una sola. Verificato su tutti i log dei DOE
  D/C/CS (D 16°: [101]; C/CS 16°: [101, 174]). Test con due log veri a 16° (`tests\fixtures\log_a16_101it.txt`,
  `log_coupled_a16_101it.txt`). Nessun effetto sui run con meno di 100 iterazioni.
- Baseline fixed e ccs rigenerate con run reali (`baseline\regen_baseline.py`): 45 righe, **0 righe diverse**;
  `heeds_inputs` aggiornati. ccs (chord_scale 1,0) = fixed: CL 0,5767, CMy −0,1993, Sref 1,82208, Re 474985.
- `STATO.md` spostato nella radice del repo.
- CCS 26.1: vedi la riga "Compatibilità CCS 26.1" in §1 (nessuna modifica necessaria).

**Parte 2 – carico lungo l'apertura (schema 4)**
- FlightStream calcola i carichi di sezione anche da script (manuale p. 363): 40 sezioni XZ addensate verso
  l'estremità (η = sin(π/2·t)), dopo l'export di carichi e VTK (non cambiano la soluzione: righe 2–45 delle baseline
  identiche). cl = CFz cos α − CFx sin α. Blocco JSON `spanload` (`enabled`, `n_sections`, `semispan_m`; in fixed
  2,64 m, in ccs_wing dal CCS). Tempo per run invariato (≈ 23–33 s).
- Righe 46–49: `cl_sec_max`, `eta_cl_sec_max`, `cl_sec_root` (sezione a η ≈ 0,02), `cl_sec_eta05`. Righe taggate in
  HEEDS (2, 5, 6, 10, 12) ferme: test `TestTaggedRows`. Baseline e heeds_inputs rigenerati (diff: riga 1 e 46–49).
- Controllo (2/Sref)∫cl·c dy contro CL: fixed −0,43 / −0,53 / −0,56 / −0,63 % a 0 / 4 / 8 / 12°; ccs_wing (chord_scale 1)
  −0,53 % a 4°. Entro l'1 %.
- cl(η) in D (`diagnostica\apertura\cl_eta.png`, `spanload_riepilogo.md`): ala rettangolare non svergolata, carico
  quasi piatto fino a η ≈ 0,5 e più pieno dell'ellittico verso l'estremità; cl_sec_max/CL ≈ 1,10 (4°). **Attenzione:**
  il massimo è su un plateau (cl a η 0,02 e 0,06 differiscono alla 4ª cifra), quindi `eta_cl_sec_max` salta tra 0,06 e
  0,25 (0°): non usarlo come risposta di ottimizzazione; `cl_sec_max` sì.

**Parte 3 – convergenza di mesh (D, ccs_wing, chord_scale 1) – FERMA ALLO STOP**
- Blocco JSON `mesh` (ccs_wing): `u_pts`, `u_growth_type`, `u_growth_rate`, `u_periodicity`, `v_*` → righe
  `Mesh_U`/`Mesh_V` del CCS (manuale p. 82: growth_type 3 = successiva su due lati, con periodicity 2 addensa a LE e TE).
  Default = mesh attuale: CCS e script generati **identici byte per byte** alla baseline; run medium = baseline ccs.
  `geometry.mesh_u/mesh_v` ora danno errore. Test `tests\test_mesh.py`.
- Run a 4° e 12°, `diagnostica\mesh\` (`run_mesh.py`, `gci.py` → `gci.md`, `gci.csv`). Due famiglie:
  A = growth rate 1,1 fisso (come chiesto: solo i punti × 1,5), B = growth rate scalato 1,1^(120/u_pts), perché con 1,1
  fisso il primo pannello al LE scala di 3–4,5 invece che di 1,5 (famiglia non simile, Celik la richiede simile).

| livello | Mesh_U / Mesh_V, growth U | pannelli | 1° pannello al LE [x/c] | tempo [s] 4° / 12° |
|---|---|---|---|---|
| coarse (A) | 80 / 43, 1,1 | 6806 | 0,00944 | 17 / 16 |
| coarse (B) | 80 / 43, 1,15369 | 6810 | 0,00512 | 11 / 13 |
| medium | 120 / 64, 1,1 | 15262 | 0,00321 | 44 / 27 |
| fine (B) | 180 / 96, 1,0656 | 34464 | 0,00205 | 60 / 63 |
| fine (A) | 180 / 96, 1,1 | 34454 | 0,00072 | 55 / 57 |

  Differenza medium–fine (famiglia B; famiglia A fra parentesi): CL −0,92 / −0,63 % (0,05 / −0,36) a 4 / 12°; CDi
  −1,18 / −0,69 % (−0,15 / −0,50); CMy −1,24 / −0,94 % (0,20 / −0,35); cl_sec_max −1,06 / −0,81 %; **CDo −2,34 / −3,83 %
  (−10,7 / −5,0 %)**. Carichi inviscidi entro il 2 % in entrambe le famiglie; **CDo no** (attrito dello strato limite
  integrale, molto sensibile al pannello al LE: in A cresce del 12 % a ogni raffinamento). Convergenza spesso
  "divergente" (R > 1): le differenze sono all'ultima cifra stampata (CMy, CDo a 4 decimali) o non asintotiche;
  p e GCI in `gci.md`. sep_frac_up_le e x_sep_up a 12° cambiano del 10–250 %: indicatori qualitativi, come deciso.
- **Bordo d'uscita** (`te_compare.py` → `te.md`, `te_cp.png`): il raccordo viene dal parametro CCS
  `Blend_trailing_edges` (manuale p. 84); il `.fsm` di fixed lo eredita (è costruito dallo stesso CCS). Varianti:
  `sharp` (sezioni chiuse) NON fedele: il vertice del TE del ventre viene portato su quello del dorso, il ventre si
  piega in su nell'ultimo 1 % di corda, CL −33 % a 4°; `blunt` (`Open_Cross_Sections` + `Blunt_trailing_edges`,
  `AUTO_DETECT_BASE_REGIONS`, `SET_BASE_REGION_TRAILING_EDGES -1`, p. 316; `proto_te_blunt.py`) fedele (TE a z 0,01483 e
  0,01708 m come nel CCS, 129 bordi d'uscita marcati), Cp regolare vicino al TE (la blended ha due gobbe a x/c 0,88–0,92,
  dove comincia il raccordo). **Effetto: CL −4,1 / −3,9 %, CMy −5,9 / −6,5 % a 4 / 12°** (oltre l'1 %); bolla sul ventre
  0,876–0,926 (blended 0,904–0,926) a 4°, sep_frac_lo_te 0,040 contro 0,031.
- **STOP** (due condizioni): medium non supera il 2 % sulla CDo; la variante TE fedele cambia CL e CMy di più dell'1 %.
- **Decisione dell'utente (2026-10-06):** mesh medium come default, CDo dichiarata con il suo GCI (famiglia B: 2,9 % a
  4°, 13,8 % a 12°); TE `blended` come default, `blunt` come opzione `te_type`, incertezza geometrica dichiarata
  (≈ 4 % su CL, ≈ 6 % su CMy). Implementato: `te_type: "blunt"` aggiunge `AUTO_DETECT_BASE_REGIONS` e
  `SET_BASE_REGION_TRAILING_EDGES -1` dopo l'import del CCS e richiede `solver.init_surfaces = -1`; run reale = prototipo
  (CL 0,5531, CMy −0,1875 a 4°; ∫cl·c −0,50 %). Esempio: `configs/esplorativi/case_semiala_ccs_te_blunt.json`.

**Parte 4 – collaudo e pulizia**
- JSON di C, CS, varianti della separazione e livelli di mesh in `configs/esplorativi/` (README: non validati, non
  usare in HEEDS); in radice solo `case_semiala_fixed.json` e `case_semiala_ccs.json`. `run_varianti.py` e
  `run_mesh.py` scrivono lì; i JSON rigenerati coincidono con quelli spostati.
- `.gitignore`: cartelle `runs/` e log della diagnostica, `spanload.txt`, VTK, cartelle dei design fuori dal repo;
  CSV di riepilogo della diagnostica e di XFOIL dentro. File più grande nel repo: 168 kB (PNG). In `diagnostica/`
  restano md, csv, png e gli script che li rigenerano.
- Collaudo end-to-end con `run_fs.bat` (`diagnostica/collaudo/collaudo.py` → `collaudo.md`): fixed α 0–12° passo 2°
  contro i `results.txt` dello Study_2 e ccs_wing chord_scale 0,9/1,0/1,1 a 4° contro `mock_runs_ccs` (confronto per
  chiave: quel DOE ha lo schema pre-v2.2.1, senza le 5 metriche `wing_frame`). **10/10 status 0, righe 2–39 identiche,
  differenza massima 0**; riga 1 = 4 (era 2). L_N ccs 235,838 / 257,445 / 278,819 N.
- Controlli finali: `PREFLIGHT OK`; 52 test OK; `heeds_report.bat --check-against-mock mock_runs\summary.csv` sullo
  Study_2: **VERIFICA OK** (anche contro il DOE di collaudo). Report in `Desktop\fs_heeds_pipeline\reports\semiala_Study_2_v260`.

**Parte 5** – `REPORT_ALA.md` (report per il team), DEMO.md, README (quick start) e questo file aggiornati.

### 3.15 Parte 7 – ala parametrica per SHERPA (v2.7.0, 2026-10-06; si procede una sotto-parte alla volta)

**7.0 – verifica dei dati (solo lettura)**
- CCS di ccs_wing e `.fsm` (mesh esportata nel VTK del run fixed): b/2 = 2,64 m; corda alla radice = all'estremità =
  0,345091 m (ala rettangolare, non svergolata, 200 punti per sezione); S semiala 0,911041 m², ala intera 1,822082 m².
  Unità: **nessuna dichiarata** (manca `Units;` nel CCS; nessuna voce nel `.fsm`); metri dimostrati indirettamente
  (Re 474985 di FlightStream = ρ V Lref / μ con Lref in m) e dal default della simulazione (manuale p. 18).
- C_L richiesto (ρ 1,225, S 1,82208 m²; α stimati dalla retta di D, non run):

| W | C_L a 20 m/s | C_L a 12 m/s |
|---|---|---|
| 29,43 N (3 kg, primo dato) | 0,0659 (α ≈ −1,3°) | 0,1831 (α ≈ −0,1°) |
| **147,15 N (15 kg, velivolo completo, dato del team)** | **0,3296** (α ≈ 1,4°) | **0,9157** (α ≈ 7,5°) |

- Correzione dell'utente: W = 147,15 N sostituisce 215,8 N; V_min = 12 m/s (ipotesi da confermare). Valgono per la 7B.

**7A – modalità `ccs_planform`**
- Profilo: `profiles/vespa_root.dat` (Selig, 200 punti, corda 1 = estensione in x, LE in 0, TE tozzo 0,652 % c) da
  `profiles/estrai_vespa_root.py` (sezione y = 0 del CCS; LE della radice (0,002108707; 0; 0,01586614) m).
- `geometry.py`: modalità `ccs_planform` (variabili `c_root` o `S_half` secondo `geometry.size_by`, `taper`,
  `twist_tip_deg`, `b_half`; `geometry.n_sections` default 7 sezioni equidistanti; linea dei quarti di corda dritta;
  svergolamento lineare in η attorno a c/4, positivo a cabrare). Stesso numero di punti per sezione, pannelli fissi
  dal blocco `mesh` (15 262 in tutti i casi provati). Intestazione del CCS 26.1 (p. 77): `ReferenceArea`,
  `ReferenceLength`, `Units;Meter`, riga vuota; come FlightStream interpreti ReferenceArea (ala o semiala) è
  **DA VERIFICARE**, ma Sref/Lref effettivi vengono da `SOLVER_SET_REF_AREA/LENGTH` (Sref = 2 S_half calcolata,
  Lref = MAC). Import del CCS e tappo di radice in una funzione comune con ccs_wing (script di ccs_wing identico byte per
  byte a prima). Manuale: quello installato (`/mnt/project` non esiste su questa macchina).
- Schema 5: righe 50–54 `c_root taper twist_tip_deg b_half S_half` (valori effettivi; -999 nelle altre modalità).
  `case_semiala_planform.json` in radice; baseline `baseline/planform`, `heeds_inputs/planform`; preflight e
  `regen_baseline.py` estesi. Test `tests/test_planform.py` (geometria, segno dello svergolamento, S_half, errori).
- **Test di equivalenza** (taper 1, twist 0, c_root e b_half della baseline, run reale): sezioni del CCS = CCS di
  partenza entro 2·10⁻¹¹ m; righe 2–49 di results.txt **identiche** a ccs_wing (CL 0,5767, CDi 0,0077, CDo 0,0125,
  CMy −0,1993, 91 iterazioni, anche residui e CL/CDi a 5 cifre nel log), salvo l'eco di chord_scale (−999).
- **8 vertici** (c_root 0,8/1,6 × c0, taper 0,4/1,0, twist −5/+1, b_half = b0, α 4°): tutti status 0, 89–93
  iterazioni, 16,8–19,0 s; ∫cl·c = CL entro 0,55 %. Tabella in `diagnostica/planform/vertici.md`.

**7B – trim, carichi sezionali, sezione critica (schema 6)**
- 7B.1: lo script attiva già `SET_VORTICITY_DRAG_BOUNDARIES 1` / `1` sull'ala (dopo `START_SOLVER`, opzione JSON esistente
  `solver.vorticity_drag_boundaries`, `[1]` nei JSON; `[]` = `DELETE_VORTICITY_DRAG_BOUNDARIES`). Baseline trimmata:
  CDi 0,0025 con e senza (pressione); a 0° 0,0009 (vorticità) / 0,0010 (pressione), a 2° 0,0034 / 0,0033. `Di_N` ed
  `e_span` usano il CDi del log (colonna "CDi (vorticity)", 5 cifre), calcolato durante il solve: non dipendono
  dall'opzione. JSON della prova: `configs/esplorativi/case_planform_cdi_pressione.json`.
- Blocchi JSON `trim` (default disattivato; attivo in `case_semiala_planform.json`) e `mission` (W_N 147,15 = 15 kg, dato del
  team; V_cruise 20; V_min 12, ipotesi da confermare; rho 1,225; b_half_max 3,04; clmax `profiles/clmax_vs_Re.csv`
  **SEGNAPOSTO 1,2**). Trim: α1 (aoa del caso, default 0) e α1 + 2° in `trim_1`, `trim_2` (VTK cancellati), α* lineare
  su L_N = W, terzo run ad α* nella cartella del design: tutte le chiavi di carico vengono da lì; `aoa` = α1, `alpha_trim`
  = α*; status 3 se |α* − α1| > 6° o |L − W|/W > 0,5 %; i tre α e le tre L_N in `run_info.txt`.
- Carichi sezionali anche in NEWTONS (`spanload_N.txt`): L'(y) = CFz cos α − CFx sin α, ∫L'dy contro L_N/2 in `run_info.txt`,
  `M_root_Nm` = ∫L' y dy; colonna `Lp_N_m` in `spanload.csv`. Sezione critica: C_L*(η) dai run ad α1 e α2, clmax a
  Re = V_min c/ν; `CLmax_wing` = minimo, `eta_stall` = posizione. Righe 55–64: `alpha_trim Di_N D0_N M_root_Nm CLmax_wing
  CL_req eta_stall Re_tip AR e_span` (D_N, Sref_m2, b_half: chiavi esistenti). Baseline fixed/ccs: righe 1–54 invariate salvo
  la riga 1; righe nuove calcolate anche senza trim (Di_N, D0_N, M_root_Nm, AR, e_span).
- Pulizia delle cartelle robusta (`empty_tree` in heeds_mock e regen_baseline: Windows nega a volte rmdir).
- **Risultati** (`diagnostica/planform/riepilogo_7b.md`): baseline trimmata **CL 0,3297, α* 1,440°**, |L−W|/W 0,021 %, D_N
  6,52 N (Di 1,14, D0 5,40), e_span 0,888, M_root 89,6 N m, 49–54 s per design (3 run). 8 vertici e 2 estremi di apertura
  (b_half 2,112 e 3,04): tutti status 0, 52–57 s, α* da −0,10° a 5,64°, |L−W|/W ≤ 0,072 %, ∫L'dy = L_N/2 entro 0,54 %.
  Con il clmax segnaposto CL_req > CLmax_wing nei 4 design con c_root 0,8 c0 (non volerebbero a 12 m/s).

**7C – benchmark sulla rastremazione** (`diagnostica/planform/benchmark_taper.md`, `.py`, 3 grafici; JSON
`configs/esplorativi/case_planform_taper_S.json`: size_by S_half, S_half 0,911041, b_half 2,64, twist 0, trim W 147,15 N)
- 16 design (taper 0,25–1,00), tutti status 0, 49–53 s (il primo 80 s), α* 1,354–1,440°.
- **Minimo di Di_N a taper 0,35–0,40** (discreto 0,35 = 1,0578 N, 0,40 uguale a 4 decimali; parabola 0,382): dentro
  l'atteso 0,3–0,45. e_span da 0,888 (taper 1) a **0,954** (massimo a 0,40); Di_N rettangolare/ottimo = 1,075. e massimo
  più basso dell'atteso ≈ 0,98 della linea portante: lo scarto relativo fra rettangolare e ottimo (7,5 %) è invece vicino.
- η_stall (clmax segnaposto) va verso l'estremità al diminuire del taper (0,06 → 0,75), a gradini per le 40 sezioni
  discrete e il plateau di cl.
- **Rumore di Di_N:** differenze seconde ≤ 0,33 % (quasi tutta curvatura vera); tolta la curvatura del polinomio di 4°
  grado ≤ 0,04 %; residui RMS 0,016 %: sotto lo 0,5 %, **Di_N è adatto a SHERPA**.
- **Attenzione per SHERPA – D_N e D0_N quantizzati:** CDo e CD hanno 4 decimali nella tabella dei carichi, quindi D0_N
  vale solo 5,357 o 5,402 N e D_N salta a gradini di 0,045 N (0,7 % di D_N, oltre lo 0,5 %). Con D_N come obiettivo
  SHERPA vedrebbe un gradino. Proposta (non fatta): esportare i carichi anche in NEWTONS (più cifre su D0) o
  ricostruire CDo da cf del VTK.

**7D – polari XFOIL e clmax(Re) di vespa_root.dat** (v2.8.0, 2026-10-06; fatta mentre girava lo studio HEEDS della
7C.1: nessun FlightStream, nessuna modifica a driver, geometria, post-processing, heeds_inputs né al JSON)
- `xfoil/xfoil_polars.py` (XFOIL 6.99 MIT in `..\tools\XFOIL6.99\`, file di comandi + subprocess con timeout): PPAR N 180,
  Mach 0, ITER 200, α −4…18° passo 0,25° in due sequenze da 0°, Re 1–8·10⁵ (9 valori) più 4,75·10⁵, Ncrit 9 e 5.
  TE tozzo lasciato aperto: XFOIL lo riconosce ("Blunt trailing edge. Gap = 0.00652") e lo tratta come base con la scia
  dai due spigoli.
- clmax(Re) Ncrit 9: 1,292 (1·10⁵) → 1,396 (5·10⁵) → 1,486 (8·10⁵), α_stall 12–15,75°; Ncrit 5: 1,224 → 1,453 → 1,545.
  Tutti **validi** (≥ 7 punti convergenti oltre il massimo); 80–89 punti convergenti su 89 per polare.
- Re 4,75·10⁵ Ncrit 9: cl_α 2D 6,436 /rad, α₀ −2,10°, cl(4°) 0,6874, clmax 1,391 a 15,25° (v2.5.1, M 0,059: 1,381 a 15,5°).
- `xfoil/clmax_vs_Re.csv` (Ncrit 9, colonna `source`, letto correttamente da `postprocess.read_clmax_table`);
  `xfoil/clmax.md`; polari in `xfoil/polars/`. **Non attivo:** `mission.clmax_file` punta ancora al segnaposto
  `profiles/clmax_vs_Re.csv` (invariato); copia del segnaposto in `profiles/clmax_vs_Re.csv.bak`. Confronto con la sezione
  a metà apertura di FlightStream rimandato.

### 3.16 Parte 8 (v2.8.1, 2026-10-06)

**7C.1 – D0 non quantizzato (schema 7)**
- Script: dopo l'export dei carichi in coefficienti, `SET_LOADS_AND_MOMENTS_UNITS NEWTONS` (manuale 26.1 p. 349) ed
  `EXPORT_SOLVER_ANALYSIS_SPREADSHEET` su `loads_N.txt`. Formato reale: stessa tabella con etichette
  `Fx, Fy, Fz, L, Di, Do, Mx, My, Mz`, "Force Units: Newtons", 4 decimali in N; letto per posizione
  (`postprocess.parse_loads_newtons`, test sul file vero `tests/fixtures/loads_N_planform_trim.txt`).
- `D0_N` (riga 57) = colonna Do del foglio in N; `Di_N` resta dal log; **`D_N` (riga 14) = Di_N + D0_N esattamente**.
  Schema 7: nessuna riga nuova, cambiano valore e definizione di D_N e D0_N. `L_over_D` resta dai coefficienti.
- Controllo D0_N(N) − CDo·q·Sref (in `run_info.txt`): baseline planform +0,020 N, fixed/ccs −0,019 N, taper 0,30–0,50 da
  −0,015 a +0,008 N: sempre entro la quantizzazione di CDo (±0,022 N).
- Baseline rigenerate: cambiano solo le righe 1, 14, 57 (fixed D_N 9,01747 → 9,0101; planform 6,51759 → 6,55887).
  `heeds_inputs/planform_S/results.txt` = run reale schema 7 a taper 1,0 (righe 2–64 = planform).
- Taper 0,30/0,35/0,40/0,45/0,50 (`diagnostica/planform/check_7c1.md`): tutti status 0, 52–56 s per design;
  **D_N liscio: residuo massimo del fit quadratico 0,053 %** (Di_N 0,035 %, D0_N 0,070 %). Il D_N vecchio era costante
  (6,4729 N) su tutto l'intervallo. Il minimo di D_N non coincide con quello di Di_N: D0_N cresce con il taper.

## 4. Metriche di separazione: implementate e ancora proposte

Implementate (v2.2.0, con `wing_frame`): `sep_frac_up_le`, `x_sep_up`, `H_max_attached_up`,
`x_H_max_attached_up`, `sep_frac_lo_te`. Restano proposte (non implementate):

Tutte pesate sull'area (indipendenti dal numero di celle), su metà ala, escludendo le facce di estremità.
"Separata" = cf < −1·10⁻⁵ (equivalente a H al tetto, con una piccola tolleranza contro il rumore). Non
serve escludere il bordo d'attacco per falsi positivi (§3.5 b), ma conviene separare le zone fisiche:

1. (implementata) `sep_frac_up_le` — frazione d'area del **dorso** separata a x/c < 0,15.
2. `sep_frac_up_turb` — frazione d'area del dorso separata con tr ≥ 0,99 a x/c ≥ 0,15: separazione
   turbulenta di bordo d'uscita, l'indicatore di stallo vero (oggi ~0 fino a 12°).
3. `sep_frac_up_lam` — come 2 ma con tr < 0,99: bolle laminari/transizionali sul dorso a metà corda.
4. `sep_frac_lo_te` — frazione d'area del ventre separata a x/c > 0,8 (bolla del bordo d'uscita del
   ventre); utile come diagnostica, da non usare come vincolo di stallo.
5. `x_sep_up` / `x_reatt_up` sulla striscia (η 0,45–0,55): x/c della prima cella separata sul dorso e della
   riattaccatura (lunghezza della bolla); `x_sep_up = 1` se non c'è separazione. Più `x_sep_lo`.
6. `eta_sep_up` — frazione dell'apertura (fasce in η) con separazione turbolenta sul dorso: dice dove
   inizia lo stallo (radice o estremità).
7. Sostituire `H_max` con `H_max_attached` (H massimo fuori dalle celle al tetto) e togliere `sep_max`
   o tenerlo solo se si usa un modello di separazione.

Limite da dire chiaramente: con `viscous_coupling = false` e senza modello di separazione queste metriche
**descrivono** lo strato limite ma i carichi restano lineari; per avere lo stallo nei coefficienti servono
`CREATE_AIRFOIL_SEPARATION` (ed eventualmente `viscous_coupling` / `LAMINAR_SEPARATION`), da validare.

## 5. Prossimi passi

1. **Problema SHERPA** da discutere col team (`REPORT_ALA.md` §6): min `D_N` con `L_N` ≥ peso W (**W da chiedere**),
   variabili `aoa` e `chord_scale`; senza vincolo di stallo l'ottimo va sul limite delle variabili (limite su `aoa` o
   vincolo su `cl_sec_max` da decidere). Non eseguito.
2. **Validazione esterna** (galleria o CFD): carichi, CDo, H/cf. Fino ad allora H/cf qualitativi.
3. HEEDS: creare in GUI i set di POST per *Share designs* (rivalutazione dei design con status 2/6, HEEDS_SETUP passo 10);
   test dello **Stop** durante un run; facoltativo "File contains" `schema_version = 4`.
4. API HEEDS (tagging da trovare); fusoliera (riferimento RANS per la resistenza di pressione).
