# fs_pipeline v2: FlightStream in batch, pronto per HEEDS

Script Python (solo libreria standard, Python ≥ 3.8) che, in una cartella di design:
legge `params.txt` → prepara la geometria → scrive lo script FlightStream → lancia FlightStream
senza interfaccia → legge carichi, log e VTK → scrive `results.txt`.

| File | Cosa fa | Chi lo modifica |
|---|---|---|
| `fs_driver.py` | l'unico comando che HEEDS lancia | nessuno |
| `geometry.py` | come si apre o costruisce la geometria | **chi cambia geometria** |
| `postprocess.py` | lettura di carichi, log e VTK | nessuno |
| `heeds_mock.py` | simula HEEDS in locale (più design, riepilogo CSV) | nessuno |
| `case_*.json` | un file per caso: geometria, condizioni, fluido, solver, riferimenti | chi prepara il caso |
| `params.txt` | i valori del singolo design (li scrive HEEDS) | HEEDS |
| `HEEDS_SETUP.md` | come collegare tutto in HEEDS | — |
| `_old/` | versione precedente (`fs_pipeline.py`), solo come riferimento | — |

I percorsi nel JSON sono relativi alla cartella del JSON. Nei JSON di esempio il template `.fsm` e
il CCS stanno nella cartella superiore (`../semiala_run01.fsm`, `../semiala_ccs_U120_V64_blended.csv`).

**Fonte di verità per la sintassi:** il manuale installato con FlightStream 26.1
(`C:\Program Files\Altair\2026.1\flightstream\Altair FlightStream User Manual.pdf` / `.chm`).

## Regole dello script FlightStream (verificate su 26.1)

- **Riga vuota obbligatoria dopo ogni comando.** Dal manuale: una riga vuota chiude i parametri di
  un comando su più righe; un commento no. Senza riga vuota FlightStream prende il comando successivo
  come parametro e si ferma con `Error in script … at line N`. Il driver scrive sempre una riga vuota
  dopo ogni comando (funzione `render`); in `geometry.py` ogni comando è una lista di righe.
- **OPEN**: il file e poi solo `LOAD_SOLVER_INITIALIZATION ENABLE|DISABLE` (il driver scrive `DISABLE`
  con `geometry.reinitialize = true`, il default). `RESET_PARALLEL_CORES` non esiste più nel 26.1
  ("Unexpected argument"); senza `LOAD_SOLVER_INITIALIZATION` il comando è incompleto.
- **CLEAR_SOLUTION** azzera la soluzione prima di `START_SOLVER` (`SOLVER_CLEAR` non esiste).
- **FLUID_PROPERTIES**: `DENSITY`, `PRESSURE`, `TEMPERATURE`, `VISCOSITY`, `SPECIFIC_HEAT_RATIO`
  (`SONIC_VELOCITY` non è più supportato).
- **INITIALIZE_SOLVER** (`ccs_wing` e `fixed` con `reinitialize`): `SOLVER_MODEL`, `SURFACES n` seguito
  da una riga `indice,ENABLE|DISABLE` per superficie (flag del quad mesher; `SURFACES -1` = tutte,
  senza righe), `WAKE_TERMINATION_X`, `SYMMETRY`, `WALL_COLLISION_AVOIDANCE`. Il modello del solver
  sta qui (`SET_SOLVER_MODEL` non esiste). Va dopo i `SOLVER_SET_*` e prima di `START_SOLVER`.
- **SET_VORTICITY_DRAG_BOUNDARIES n** + riga `1,2,…` (oppure `-1` = tutte): comando di analisi,
  scritto dopo `START_SOLVER` come nello script del riferimento.
- **SET_VTK_EXPORT_VARIABLES -1 DISABLE** su una riga: tutte le variabili, senza scie.
- **File CCS**: i parametri del componente sono parole chiave senza prefisso
  (`Mark_trailing_edges`, `Open_Cross_Sections`, `Blend_trailing_edges`, `Mesh_U;…`).

## Reinizializzazione in modalità `fixed` (`geometry.reinitialize`, default `true`)

Con `reinitialize = true` il driver apre il .fsm con `LOAD_SOLVER_INITIALIZATION DISABLE` e poi
scrive **tutto** in modo esplicito dal blocco `solver` del JSON: `SET_SOLVER_STEADY`,
`SET_BOUNDARY_LAYER_TYPE`, `SET_SURFACE_ROUGHNESS` (anche 0), `SET_SOLVER_VISCOUS_COUPLING`,
`INITIALIZE_SOLVER` (superfici con flag quad mesher, scia, simmetria, wall collision avoidance,
modello del solver) e, dopo il run, `SET_VORTICITY_DRAG_BOUNDARIES`. Dal .fsm si prendono solo la
mesh e il fluido.

**Perché è il default:** così i risultati non dipendono dallo stato in cui è stato salvato il .fsm
(inizializzazione, scia, liste di superfici, impostazioni rimaste dall'ultima sessione nella GUI).
Con l'inizializzazione salvata (`reinitialize = false`) la semiala dava CL 0,5931 contro 0,5767 del
riferimento (+2,8 %), CDi +6,5 %, CMy +2,5 %, con lo stesso Re e lo stesso numero di iterazioni.
Con `reinitialize = true` il riferimento è riprodotto esattamente (CL, CDi, CDo, CMy, Re,
iterazioni e anche i residui dell'ultima iterazione), due run identici danno file identici byte per
byte e `ccs_wing` con `chord_scale = 1` coincide (prove del 2026-10-04, vedi `../STATO.md`).

`reinitialize = false` resta disponibile per un .fsm che non si sa reinizializzare dallo script
(es. impostazioni del solver non esposte nel JSON): in quel caso vale ciò che è salvato nel file.

## Il fluido (uguale in `fixed` e `ccs_wing`)

- Il blocco `fluid` del JSON contiene i valori del fluido del `.fsm` di riferimento (sezione `Air`
  di `semiala_run01.fsm`): ρ = 1,225 kg/m³, μ = 1,78·10⁻⁵ Pa·s, p = 101324,02 Pa, T = 288,166 K, γ = 1,4.
  Gli stessi valori stanno in entrambi i JSON.
- `fixed`: il fluido **non** viene riscritto, vale quello salvato nel `.fsm` (che coincide con il
  blocco `fluid`). `ccs_wing`: la simulazione nasce da zero e lo script scrive `FLUID_PROPERTIES` con
  i valori del blocco `fluid` (tutti e cinque obbligatori). Così le due modalità hanno lo stesso
  Reynolds a pari geometria.
- `q_Pa`, `L_N` e `D_N` usano `fluid.density` (il 26.1 non scrive la densità nella tabella dei
  carichi). `Re_ref` è quello scritto da FlightStream nella tabella dei carichi.
- `altitude` **non** è una variabile ammessa: se compare in `params.txt` o nel blocco `case` il run
  si ferma con `status = 1` e un messaggio chiaro.
- Solo con `"override_fluid": true` (in entrambe le modalità) il driver scrive il fluido dall'ISA
  alla quota `altitude`, che diventa una variabile ammessa.

## Primo utilizzo (una volta sola)

1. **Prove di sintassi** (già fatte su questo PC con FlightStream 26.1):
   ```
   python fs_driver.py --config case_semiala_fixed.json --probes
   probes\run_probes.bat
   ```
   Esito delle prove: solo file → errore; file + `RESET_PARALLEL_CORES` + `LOAD_SOLVER_INITIALIZATION`
   → errore; file + `LOAD_SOLVER_INITIALIZATION` → ok; sistema dei momenti → ok. Su un altro PC o con
   un'altra versione di FlightStream conviene ripeterle: se un file `probe_N_…_log.txt` esiste e non
   contiene `ERROR`, quella sintassi funziona (in modalità `-hidden` gli errori finiscono anche in
   `FlightStreamLog.txt`, nella cartella da cui si lancia).
2. **Validazione** rispetto al run di riferimento (tolleranza `validation.rel_tol`): crea una cartella `val`,
   copiaci `params.txt` (aoa = 4, velocity = 20) e lancia
   ```
   python fs_driver.py --config case_semiala_fixed.json --workdir val --validate
   ```
   **Stato attuale: superata** con `reinitialize = true` (scarti 0,00 % su CL, CDi, CDo, CMy, Re e
   iterazioni; tolleranza 0,5 %).

## Run a mano

Nella cartella del design deve esserci `params.txt`:
```
cd C:\run\prova01
python C:\percorso\fs_driver.py --config C:\percorso\case_semiala_fixed.json
```
Opzioni utili:
- `--dry-run`: scrive solo `fs_script.txt`, senza lanciare FlightStream (status = 1);
- `--extract-only --loads loads.txt --log fs_log.txt --vtk surface.vtk`: rilegge file già esistenti
  (anche esportati dalla GUI) senza lanciare nulla;
- `--exe`: percorso di FlightStream. In alternativa la variabile d'ambiente `FLIGHTSTREAM_EXE`, la
  voce `flightstream_exe` del JSON, il PATH o la ricerca in `Program Files\Altair`.

File prodotti nella cartella: `results.txt` (per HEEDS), `run_info.txt` (motivo dello status e
densità usata), `fs_script.txt`, `fs_stdout.txt`, `FlightStreamLog.txt` (solo se FlightStream si
ferma per un errore), `loads.txt`, `fs_log.txt`, `surface.vtk`, `bl_profiles.csv` (solo `ccs_wing`)
e `case_ccs.csv` (solo `ccs_wing`). All'avvio i risultati vecchi vengono cancellati.
Un run della semiala in `fixed` dura circa 15 s, in `ccs_wing` circa 27 s.

**Licenza.** Durante il run il driver legge `fs_stdout.txt`. Se compare "Checking out Altair
units...Not available" e dopo 15 s nessun fallback (EDU, licenza a feature) è riuscito, chiude
FlightStream (che in `-hidden` altrimenti resterebbe aperto fino al timeout), aspetta
`run.license_wait_s` secondi e riprova, fino a `run.license_retries` volte oltre al primo
tentativo. Se fallisce anche l'ultimo: `status = 6`. Con i valori di default (2 nuovi tentativi,
60 s) un design senza licenza si chiude in circa 3 × 15 s + 2 × 60 s ≈ 3 minuti.

## heeds_mock.py: simulare HEEDS

```
python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8
python heeds_mock.py --config case_semiala_ccs.json --var aoa=2,6 --var chord_scale=0.9,1.1
python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,4 --dry-run
```
Crea `mock_runs\Design_001`, `Design_002`, … (più `--var` = tutte le combinazioni), in ognuno scrive
`params.txt` e lancia `fs_driver.py` in quella cartella, come farà HEEDS. Il riepilogo va in
`mock_runs\summary.csv` e a schermo. Con `--dry-run` genera solo gli script. **All'avvio cancella le
cartelle `Design_NNN` già presenti in `--out`.**

## Contratto con HEEDS (`results.txt`)

- È scritto **sempre**, anche in caso di errore, con le stesse chiavi nello stesso ordine
  (`chiave = valore`). Valore mancante = `-999`.
- Codice di uscita: 0 se `status = 0`, altrimenti 1.

| status | Significato | Coefficienti scritti? |
|---|---|---|
| 0 | ok | sì |
| 1 | errore generico o di setup (file mancante, chiave non ammessa in params.txt, `fluid.density` mancante, coefficienti incompleti, dry-run) | no |
| 2 | timeout (`run.timeout_s`) | no |
| 6 | licenza FlightStream non disponibile, anche dopo `run.license_retries` nuovi tentativi: **non** è un errore del design, si può rilanciare | no |
| 3 | solver non convergente (o convergenza non verificabile dal log) | sì, solo per diagnosi |
| 5 | risultati non fisici (CD ≤ 0, CDo < 0, valori non finiti) | sì, solo per diagnosi |
| 4 | H/cf non estraibili (CL/CD validi) | sì |

Se valgono più condizioni insieme, conta la prima di questa tabella dall'alto (1, 2, 6, 3, 5, 4).
Gli status 2 e 6 dipendono dalla macchina, non dal design: vale la pena rilanciare quei design.

### Nota per HEEDS: geometria variabile e coefficienti

Quando varia la geometria (`chord_scale` in `ccs_wing`), `Sref` e `Lref` sono ricalcolati per ogni
design (`Sref_m2`, `Lref_m` in `results.txt`). I coefficienti (CL, CD, CMy, …) sono quindi riferiti
ad aree diverse e **non sono confrontabili tra design**: un'ala più grande può avere CL più basso e
portanza più alta. Come obiettivi e vincoli usare `L_over_D` (adimensionale e indipendente da
Sref) oppure le forze dimensionali `L_N` e `D_N`. Con `fixed` (Sref costante) i coefficienti
restano confrontabili.

Chiavi: `status converged iterations CL CD CDi CDo CMx CMy CMz L_over_D L_N D_N q_Pa xtr_up xtr_lo
H_te_up H_te_lo H_max_up H_max_lo cf_min_up cf_min_lo area_frac_cf_neg H_max sep_max aoa velocity
altitude sideslip chord_scale Sref_m2 Lref_m Re_ref sep_frac_up_le x_sep_up H_max_attached_up
x_H_max_attached_up sep_frac_lo_te`. Il significato è in `HEEDS_SETUP.md`. **HEEDS legge le risposte per
posizione: le chiavi nuove si aggiungono solo in coda, mai riordinate né tolte** (le ultime cinque
sono della v2.2.0).

## Il JSON del caso

Le chiavi che iniziano con `_` sono commenti. Esempi: `case_semiala_fixed.json`, `case_semiala_ccs.json`.

| Chiave | Significato |
|---|---|
| `flightstream_exe` | percorso dell'eseguibile (vuoto = ricerca automatica) |
| `geometry.mode` | `fixed` (template .fsm) oppure `ccs_wing` (semiala da CCS); le altre chiavi di `geometry` dipendono dalla modalità e le legge solo `geometry.py` |
| `geometry.template_fsm` | (`fixed`) il .fsm già pronto: la mesh e il fluido vengono da lì |
| `geometry.reinitialize` | (`fixed`) `true` (default) = OPEN con `LOAD_SOLVER_INITIALIZATION DISABLE`, modello fisico e `INITIALIZE_SOLVER` dal blocco `solver`; `false` = inizializzazione e modello fisico salvati nel .fsm. La vecchia chiave `open_options` non è più ammessa (errore) |
| `geometry.base_ccs`, `mesh_u`, `mesh_v`, `te_type`, `root_cap_tol_m` | (`ccs_wing`) CCS di partenza, pannelli, tipo di bordo d'uscita (`blended`/`sharp`/`blunt`), tolleranza in y per togliere il tappo di radice |
| `case` | valori di default di `aoa` [deg], `velocity` [m/s], `sideslip` [deg], `altitude` [m] (solo con `override_fluid`) e delle variabili geometriche; `params.txt` li sovrascrive |
| `fluid.override_fluid` | `false` (default) = fluido del blocco `fluid` / del .fsm; `true` = fluido ISA alla quota `altitude`. Vale per tutte le modalità |
| `fluid.density`, `viscosity`, `pressure`, `temperature`, `specific_heat_ratio` | fluido del .fsm di riferimento [kg/m³, Pa·s, Pa, K, –]. `density` è sempre obbligatoria (q, L, D); in `ccs_wing` lo sono tutte (`FLUID_PROPERTIES`) |
| `solver.iterations`, `convergence`, `threads` | iterazioni massime, soglia di convergenza, thread (0 = metà dei core) |
| `solver.model`, `bl_type`, `roughness_nm`, `viscous_coupling`, `wall_collision_avoidance` | modello fisico: usato quando lo script inizializza la simulazione (`ccs_wing`, `fixed` con `reinitialize`); con `reinitialize = false` vale quello del .fsm |
| `solver.init_surfaces` | superfici di `INITIALIZE_SOLVER`: `[[indice, quad_mesher], …]` (es. `[[1, true]]`) oppure `-1` = tutte. Obbligatoria quando lo script inizializza |
| `solver.wake_termination_x`, `symmetry` | `"DEFAULT"` o un numero [m]; `"MIRROR"`, `"NONE"` (`ccs_wing` vuole `"MIRROR"`). `symmetry` obbligatoria quando lo script inizializza |
| `solver.vorticity_drag_boundaries` | superfici per il CDi di vorticità: lista di indici (es. `[1]`) oppure `-1` = tutte |
| `reference.sref_m2`, `lref_m` | area e lunghezza di riferimento. Obbligatorie in `fixed`; in `ccs_wing` `null` = calcolate dalla geometria (Sref = 2·S_semiala con symmetry_loads, Lref = MAC) |
| `reference.symmetry_loads` | carichi riportati al corpo intero (simmetria Mirror) |
| `reference.moment_point_m` | punto [x, y, z] in metri attorno a cui si calcolano i momenti; `null` = origine del frame 1, senza creare un nuovo sistema |
| `reference.moment_frame_index` | indice del nuovo sistema di riferimento (default 2). **Se il .fsm ha già sistemi utente, va aumentato** (es. 3) |
| `postproc.vtk_surfaces` | indici delle superfici da esportare nel VTK e usare per H/cf; `[]` = tutte |
| `postproc.strip`, `bin_width`, `xtr_threshold`, `te_window`, `exclude_le` | (`ccs_wing`) striscia in apertura, larghezza delle fasce in corda, soglia di transizione, finestra del bordo d'uscita, zona di ristagno esclusa |
| `wing_frame` | assi dell'ala per le metriche di separazione: `{"chord_axis": "+x", "span_axis": "+y", "up_axis": "+z"}` (corda dal bordo d'attacco al bordo d'uscita, apertura dalla radice all'estremità, verso il dorso), opzionali `span_root_m` (default 0: si usano le facce con coordinata in apertura ≥ radice, cioè una semiala; le facce specchiate sono escluse) e `n_strips` (strisce in apertura, default 60). Assente o `null` = le cinque metriche di separazione valgono -999 (es. fusoliera); un valore non valido = status 1 |
| `postproc.sep_cf`, `le_xc`, `lo_te_xc`, `x_sep_eta`, `h_attached_xc_max` | (con `wing_frame`) soglia di separazione (cella separata se cf < −sep_cf, default 1e-5), x/c del bordo d'attacco per `sep_frac_up_le` (0,15), x/c del bordo d'uscita per `sep_frac_lo_te` (0,8), strisce usate per `x_sep_up` (η 0,05–0,95), x/c massimo per `H_max_attached_up` (0,95) |
| `run.timeout_s`, `run.save_fsm` | tempo massimo per FlightStream (per tentativo); salvare `case.fsm` nella cartella del design |
| `run.license_retries`, `run.license_wait_s` | nuovi tentativi se la licenza non è disponibile (default 2, oltre al primo) e attesa prima di ognuno (default 60 s); poi `status = 6` |
| `validation` | valori del run di riferimento per `--validate` (CL, CDi, CDo, CMy, `Re_ref`, `iterations`, tolleranza relativa `rel_tol`) |

Il .fsm deve essere in metri (da verificare se un template usa altre unità).

## Cambiare geometria (solo `geometry.py` e il JSON)

- **Geometria fissa** (fusoliera, velivolo completo, nessuna variabile geometrica): prepara e
  inizializza il caso nella GUI, salvalo come .fsm e crea un JSON con `"mode": "fixed"`,
  `template_fsm`, `fluid.density`, `sref_m2`, `lref_m`, `moment_point_m` adatti al nuovo corpo, il
  blocco `solver` di inizializzazione (`init_surfaces` con gli indici delle superfici del nuovo .fsm,
  `symmetry`, `wake_termination_x`, `vorticity_drag_boundaries`: copiarli da ciò che si usa nella GUI)
  e, se servono, `symmetry_loads` e `vtk_surfaces`. Prima di fidarsi dei risultati, un run con
  `--validate` contro un run fatto a mano. Non si tocca nessun file Python.
- **Geometria parametrica nuova**: aggiungi una modalità in `geometry.py`. Le istruzioni sono nel
  commento in testa al file (variabili in `GEOMETRY_VARIABLES`, post-processing in `POSTPROC`,
  `NEW_SIMULATION`, una funzione che restituisce i comandi). Le nuove variabili diventano
  automaticamente chiavi ammesse in `params.txt` e colonne di `results.txt`.

Limiti da ricordare per corpi diversi dall'ala: con `fixed` gli scalari della striscia (`xtr_*`,
`H_te_*`, `H_max_*`, `cf_min_*`) valgono -999; senza `wing_frame` valgono -999 anche le metriche di
separazione (`sep_frac_*`, `x_sep_up`, `*H_max_attached_up`) e restano solo `area_frac_cf_neg`,
`H_max` e `sep_max`.

### Metriche di separazione (con `wing_frame`, v2.2.0)

Dalla diagnosi del 2026-10-04 (`../STATO.md`): una cella separata ha cf < 0 e H bloccato a 3,9155; il
segno di cf è riferito alla linea di corrente superficiale (non alla corrente libera), quindi la zona
tra il ristagno e il bordo d'attacco **non** dà falsi positivi. `H_max` vale 3,9155 appena compare una
separazione e `sep_max` è sempre 0 senza modello di separazione: restano solo per compatibilità.
Le metriche si calcolano sulla semiala (facce d'estremità escluse), pesate sull'area:
- `sep_frac_up_le`: area separata del dorso a x/c < 0,15 / area del dorso (bolla di bordo d'attacco).
- `x_sep_up`: per ogni striscia in apertura (η 0,05–0,95) il primo x/c separato sul dorso dal bordo
  d'attacco; si scrive il minimo sulle strisce. **Convenzione: 1.0 = nessuna separazione sul dorso.**
  Comprende anche le bolle laminari corte prima della transizione (a 4° vale 0,40), quindi non è da
  solo un indicatore di stallo.
- `H_max_attached_up`, `x_H_max_attached_up`: H massimo sul dorso dove cf > 1e-5 e x/c ≤ 0,95, e il suo
  x/c (quanto lo strato limite attaccato è vicino alla separazione).
- `sep_frac_lo_te`: area separata del ventre a x/c > 0,8 / area del ventre. Solo diagnostica (bolla del
  ventre al bordo d'uscita arrotondato), da non usare come vincolo di stallo.
Il metodo a pannelli con strato limite integrale non prevede la resistenza di pressione dovuta
alla separazione su corpi tozzi. `Sref` e `Lref` vanno scelti per il nuovo corpo.

## Da verificare

- Criterio di convergenza: `converged = 1` se i residui finali sono sotto `solver.convergence`,
  oppure se il solver si ferma prima di `solver.iterations` con residui finiti.
- Unità di `ORIGIN_*` in `EDIT_COORDINATE_SYSTEM` non documentate: l'origine viene comunque
  reimpostata con `SET_COORDINATE_SYSTEM_ORIGIN … METER`.
- Percorsi con spazi: lo script FlightStream non usa virgolette; meglio cartelle senza spazi.
- Fisica: a 20 m/s il Reynolds sulla corda (≈ 4,7·10⁵) è sotto il campo del modello transizionale
  (5·10⁵–1,5·10⁶); H e cf sono indicatori comparativi.
