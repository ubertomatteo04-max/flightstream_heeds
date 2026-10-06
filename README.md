# fs_pipeline v2.6.0: FlightStream in batch, pronto per HEEDS

**Stato (v2.6.0):** lavoro sull'ala chiuso. Configurazione di riferimento = disaccoppiata, senza modello di
separazione (default dei due JSON in radice). Conclusioni per il team in `REPORT_ALA.md`; storia e decisioni in
`STATO.md`. I JSON in `configs/esplorativi/` (accoppiamento, separazione, mesh, TE tozzo) **non sono validati e
non vanno usati in HEEDS**.

Script Python (solo libreria standard, Python ≥ 3.8) che, in una cartella di design:
legge `params.txt` → prepara la geometria → scrive lo script FlightStream → lancia FlightStream
senza interfaccia → legge carichi, log e VTK → scrive `results.txt`.

## Quick start

**Requisiti:** Windows, FlightStream 26.1 (`C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe`,
trovato da solo), Python 3 indicato in testa a `run_fs.bat`, login Altair One valido, **GUI di
FlightStream chiusa** (un solo FlightStream alla volta, altrimenti `status = 6`).

**1. Prova senza FlightStream (pochi secondi):**
```
cd C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline
preflight.bat
python -m unittest discover -s tests -v
```
`preflight.bat` (prima di ogni studio) deve finire con `PREFLIGHT OK`: nessun FlightStream attivo,
interpreti Python, JSON e percorsi, `heeds_inputs` coerenti con lo schema, `--dry-run` con `run_fs.bat`.

**2. Un design come lo lancerà HEEDS** (cartella del design = cartella corrente, `params.txt` dentro):
```
mkdir "C:\HEEDS prove\Design_1\Analysis_1"
copy baseline\fixed\params_baseline.txt "C:\HEEDS prove\Design_1\Analysis_1\params.txt"
cd /d "C:\HEEDS prove\Design_1\Analysis_1"
"C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\run_fs.bat" --config "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\case_semiala_fixed.json"
echo %ERRORLEVEL%
```
Atteso in 15–45 s: codice di uscita 0, `results.txt` uguale a `baseline\fixed\results_baseline.txt`
(`schema_version = 5`, `status = 0`, CL 0,5767, CDi 0,0077, CDo 0,0125, CMy −0,1993, Re 474985).
Il motivo di uno status diverso da 0 è in `run_info.txt`, che termina con
`FS_DRIVER_RESULT status=<n> success=<0|1>`.

**3. Più design (simula HEEDS):**
```
python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8 --root "C:\HEEDS prove\doe aoa"
python heeds_mock.py --config case_semiala_ccs.json --var chord_scale=0.9,1.0,1.1 --root "C:\HEEDS prove\doe corda"
```
Riepilogo in `summary.csv` nella cartella `--root` (≈ 15–45 s a design).

**4. Riepilogo e grafici di uno studio HEEDS** (CSV, design scartati, CL–α e L/D–α in PNG), letti dai
`results.txt` delle cartelle dei design:
```
heeds_report.bat --study "C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala_Study_2"
```
Risultati in `<studio>\report\`. `heeds_report.bat` usa il Python di HEEDS (ha matplotlib); con
`python heeds_report.py ...` senza matplotlib si ottengono solo CSV ed elenco degli scartati.
Verifica di uno sweep contro il DOE del driver (scrive `report\verifica.md`, codice di uscita 0/1):
```
heeds_report.bat --study "...\semiala_Study_2" --check-against-mock mock_runs\summary.csv --expect-n 7 --expect-aoa 0,2,4,6,8,10,12
```

**5. HEEDS:** seguire `HEEDS_SETUP.md` (procedura passo-passo del primo Evaluation Only, con la tabella
delle 64 righe di `results.txt` da taggare e i file `heeds_inputs\<modalità>\params.txt` / `results.txt`
da aggiungere in HEEDS).

**Da sapere in breve**
- Due modalità: `fixed` (template `.fsm`, variabili `aoa`, `velocity`, `sideslip`) e `ccs_wing` (semiala da
  CCS, in più `chord_scale`; `sideslip` = 0). Con `chord_scale` Sref cambia: obiettivi `L_over_D` o
  `L_N`/`D_N`, non CL.
- `results.txt` ha sempre 64 righe nello stesso ordine (`-999` = non disponibile, schema 7); chiavi nuove solo in
  fondo. Righe 46–49: carico lungo l'apertura (`cl_sec_*`, `spanload.csv` nella cartella del design).
- Incertezze (v2.6.0, `REPORT_ALA.md`): mesh ≈ 1 % sui carichi inviscidi, CDo GCI 2,9 % a 4° e 13,8 % a 12°;
  bordo d'uscita raccordato (default) contro tozzo (`te_type: "blunt"`, opzione): ≈ 4 % su CL, ≈ 6 % su CMy.
  H e cf del VTK: indicatori qualitativi.
- Codice di uscita 0 solo se lo status è in `heeds.success_statuses` del JSON (default `[0]`).
- Status: 0 ok, 1 setup/errore, 2 timeout (`run.timeout_s` = 240 s nei JSON della semiala), 3 non
  convergente, 4 manca solo H/cf, 5 non fisico, 6 FlightStream non disponibile (licenza o già attivo).
- Vincolo di separazione consigliato: `sep_frac_up_le`; `x_sep_up`, `H_max_attached_up`,
  `sep_frac_lo_te` sono solo diagnostica.

## File

| File | Cosa fa | Chi lo modifica |
|---|---|---|
| `run_fs.bat` | il comando che HEEDS lancia: fissa l'interprete Python (riga `set "PY=..."`) e chiama `fs_driver.py` | chi installa su un altro PC |
| `fs_driver.py` | il driver: params.txt → FlightStream → results.txt | nessuno |
| `geometry.py` | come si apre o costruisce la geometria | **chi cambia geometria** |
| `postprocess.py` | lettura di carichi, log e VTK | nessuno |
| `heeds_mock.py` | simula HEEDS in locale (più design, riepilogo CSV) | nessuno |
| `heeds_report.py`, `heeds_report.bat` | riepilogo di uno studio HEEDS o di un DOE mock dai `results.txt` dei design: CSV, scartati, grafici CL–α e L/D–α (il `.bat` usa il Python di HEEDS, che ha matplotlib) | nessuno |
| `case_*.json` | un file per caso: geometria, condizioni, fluido, solver, riferimenti | chi prepara il caso |
| `params.txt` | i valori del singolo design (li scrive HEEDS) | HEEDS |
| `baseline/fixed`, `baseline/ccs` | `params_baseline.txt` e `results_baseline.txt` di run reali a 4° | si rigenerano se cambia lo schema |
| `heeds_inputs/fixed`, `heeds_inputs/ccs` | le stesse baseline rinominate `params.txt` e `results.txt`: i file da aggiungere e taggare in HEEDS (HEEDS legge l'output con lo stesso nome del file taggato) | si ricopiano dalle baseline |
| `preflight.py`, `preflight.bat` | controlli prima di uno studio (non lancia FlightStream); il `.bat` usa l'interprete di `run_fs.bat` | nessuno |
| `HEEDS_SETUP.md` | procedura passo-passo per HEEDS | — |
| `DEMO.md` | presentazione di una pagina per il team (numeri dello Study_2 da inserire; grafici in `demo/`) | — |
| `tests/` | test automatici senza FlightStream (`python -m unittest discover -s tests -v`) | chi cambia il driver |
| `diagnostica/` | script di analisi dei VTK (strato limite), non usati dal driver | — |
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
byte e `ccs_wing` con `chord_scale = 1` coincide (prove del 2026-10-04, vedi `STATO.md`).

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
Un run della semiala in `fixed` dura circa 15–40 s, in `ccs_wing` circa 25–45 s (il solver è più lento con il PC carico: baseline del 2026-10-04 sera 36 s e 44 s, pomeriggio 16 s e 27 s).

**Licenza.** Durante il run il driver legge `fs_stdout.txt`. Se compare "Checking out Altair
units...Not available" e dopo 15 s nessun fallback (EDU, licenza a feature) è riuscito, chiude
FlightStream (che in `-hidden` altrimenti resterebbe aperto fino al timeout), aspetta
`run.license_wait_s` secondi e riprova, fino a `run.license_retries` volte oltre al primo
tentativo. Se fallisce anche l'ultimo: `status = 6`. Con i valori di default (2 nuovi tentativi,
60 s) un design senza licenza si chiude in circa 3 × 15 s + 2 × 60 s ≈ 3 minuti.

**Processi.** Prima di ogni tentativo il driver controlla che non ci sia già un FlightStream attivo
(aspetta fino a 10 s; poi status 6, oppure lo chiude se `run.kill_stale_flightstream = true`). Durante
il run registra l'albero dei processi (in `run_info.txt`: "processi del run"); al timeout o con la
licenza mancante chiude l'albero con `taskkill /T /F` e verifica che non resti nessun processo del
run. Percorsi con spazi nelle cartelle di lavoro: verificati con run reali di `fixed` e `ccs_wing`.
Per simulare una licenza mancante solo in un processo di prova servono **due** variabili:
`ALTAIR_LICENSE_PATH=<server inesistente>` e `ALM_HHWU=F` (la licenza di questo PC è Altair One
"hosted HWU", con il token in `%LOCALAPPDATA%\.altair_licensing`, e ignora la sola
`ALTAIR_LICENSE_PATH`).

## heeds_mock.py: simulare HEEDS

```
python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,2,4,6,8
python heeds_mock.py --config case_semiala_ccs.json --var aoa=2,6 --var chord_scale=0.9,1.1
python heeds_mock.py --config case_semiala_fixed.json --var aoa=0,4 --dry-run
python heeds_mock.py --config case_semiala_fixed.json --var aoa=4 --root "C:\HEEDS prove\studio 1"
```
Crea `mock_runs\Design_001`, `Design_002`, … (più `--var` = tutte le combinazioni), in ognuno scrive
`params.txt` e lancia **`run_fs.bat --config <JSON assoluto>` con la cartella del design come cartella
corrente**, come farà HEEDS. Con `--root` usa la struttura di HEEDS, `<root>\Design_<N>\Analysis_1`
(nome dell'analisi con `--analysis`; nomi esatti di HEEDS DA VERIFICARE), anche fuori dal repo e con
spazi nel percorso. Il riepilogo va in `summary.csv` (in `--out` o `--root`) e a schermo, con il codice
di uscita di ogni design. Con `--dry-run` genera solo gli script. Gli argomenti dopo `--` vanno al
driver tali e quali (solo per prove, es. `-- --extract-only --loads ...`). **All'avvio cancella le
cartelle dei design già presenti (`Design_NNN` in `--out`, `Design_<N>` in `--root`).**

Test automatici (senza FlightStream): `python -m unittest discover -s tests -v` — schema di
`results.txt`, contratto di successo, `run_fs.bat` (processo diretto, `cmd /c`, `call`, PowerShell) e
`heeds_mock.py --root` in una cartella con spazi.

## Contratto con HEEDS (`results.txt`)

- È scritto **sempre**, anche in caso di errore, con le stesse chiavi nello stesso ordine
  (`chiave = valore`). Valore mancante = `-999`.
- Codice di uscita: 0 se lo status è in `heeds.success_statuses` del JSON (default `[0]`), altrimenti 1.
  `[0]` per l'ottimizzazione; `[0, 4]` per i DOE in cui H/cf non sono obiettivi (status 4 = CL/CD validi,
  manca solo lo strato limite). Gli status 1, 2, 3, 5, 6 non vanno mai messi nella lista.
- `run_info.txt` termina **sempre** con la riga fissa `FS_DRIVER_RESULT status=<n> success=<0|1>`, che è
  anche l'ultima riga stampata dal driver; `success = 1` se lo status è in `heeds.success_statuses` (cioè
  se il codice di uscita è 0). È l'alternativa al codice di uscita per la condizione "File contains"
  di HEEDS (cercare `success=1`).
- `results.txt` comincia con `schema_version = 5`. Success condition in HEEDS: codice di uscita = 0
  (verificato) e, facoltativa, "File contains" `schema_version = 5` in `results.txt` (vedi `HEEDS_SETUP.md`).

| status | Significato | Coefficienti scritti? |
|---|---|---|
| 0 | ok | sì |
| 1 | errore generico o di setup (file mancante, chiave non ammessa in params.txt, `fluid.density` mancante, coefficienti incompleti, dry-run) | no |
| 2 | timeout (`run.timeout_s`) | no |
| 6 | FlightStream non disponibile: licenza (anche dopo `run.license_retries` nuovi tentativi) oppure un `FlightStream.exe` già attivo prima del lancio (GUI aperta, processo orfano; PID in `run_info.txt`). **Non** è un errore del design, si può rilanciare | no |
| 3 | solver non convergente (o convergenza non verificabile dal log); con `viscous_coupling` anche fase viscosa non convergente o assente nel log | sì, solo per diagnosi |
| 5 | risultati non fisici (CD ≤ 0, CDo < 0, valori non finiti) | sì, solo per diagnosi |
| 4 | H/cf o carico in apertura non estraibili (CL/CD validi) | sì |

Se valgono più condizioni insieme, conta la prima di questa tabella dall'alto (1, 2, 6, 3, 5, 4).
Gli status 2 e 6 dipendono dalla macchina, non dal design: vale la pena rilanciare quei design.

### Nota per HEEDS: geometria variabile e coefficienti

Quando varia la geometria (`chord_scale` in `ccs_wing`), `Sref` e `Lref` sono ricalcolati per ogni
design (`Sref_m2`, `Lref_m` in `results.txt`). I coefficienti (CL, CD, CMy, …) sono quindi riferiti
ad aree diverse e **non sono confrontabili tra design**: un'ala più grande può avere CL più basso e
portanza più alta. Come obiettivi e vincoli usare `L_over_D` (adimensionale e indipendente da
Sref) oppure le forze dimensionali `L_N` e `D_N`. Con `fixed` (Sref costante) i coefficienti
restano confrontabili.

**Schema fisso** (`RESULTS_SCHEMA` in `fs_driver.py`, unico punto in cui si decide): le stesse chiavi
nello stesso ordine per **tutte** le modalità; quelle non pertinenti valgono -999. Sezioni, in ordine:

| Sezione | Chiavi |
|---|---|
| stato | `schema_version status converged iterations` |
| carichi | `CL CD CDi CDo CMx CMy CMz L_over_D L_N D_N` |
| riferimenti | `Sref_m2 Lref_m Re_ref q_Pa` |
| strato limite | `xtr_up xtr_lo H_te_up H_te_lo H_max_up H_max_lo cf_min_up cf_min_lo area_frac_cf_neg H_max sep_max sep_frac_up_le x_sep_up H_max_attached_up x_H_max_attached_up sep_frac_lo_te` |
| ingressi (eco) | `aoa velocity altitude sideslip chord_scale` |
| viscoso (schema 3, v2.5.0) | `viscous_coupling separation_model iterations_inviscid iterations_viscous converged_viscous sep_marker_frac_up` |
| apertura (schema 4, v2.6.0) | `cl_sec_max eta_cl_sec_max cl_sec_root cl_sec_eta05` |
| planform (schema 5, v2.7.0) | `c_root taper twist_tip_deg b_half S_half` (pianta effettiva di `ccs_planform`) |
| missione (schema 6, v2.7.0) | `alpha_trim Di_N D0_N M_root_Nm CLmax_wing CL_req eta_stall Re_tip AR e_span` |

Il significato è in `HEEDS_SETUP.md`. **HEEDS legge le risposte per posizione.** Regole:
- una chiave nuova si aggiunge **solo in fondo al file** (in coda all'ultima sezione, oggi "missione"):
  aggiungerla in coda a una sezione intermedia sposterebbe tutte le righe successive;
- mai riordinare né togliere chiavi;
- una variabile geometrica nuova (modalità nuova) va aggiunta in fondo a `RESULTS_SCHEMA`: se manca, il
  driver si ferma all'avvio invece di spostare le posizioni in silenzio;
- **ogni modifica dello schema incrementa `SCHEMA_VERSION`** (scritto come `schema_version` nella prima
  riga di `results.txt`): così HEEDS, se controlla `schema_version = 5`, rifiuta un results.txt con
  un ordine diverso da quello taggato invece di leggere righe sbagliate;
- `tests/test_schema.py` controlla che `fixed` e `ccs_wing` scrivano lo stesso elenco, che le
  posizioni dello schema 7 non cambino (e le righe taggate 2, 5, 6, 10, 12) e che la prima riga sia `schema_version = 7`
  (`python -m unittest discover -s tests -v`).

Lo schema 7 (v2.8.1) non aggiunge righe ma cambia `D_N` (= Di_N + D0_N) e `D0_N` (dal foglio dei carichi in NEWTONS,
`loads_N.txt`, esportato dopo `SET_LOADS_AND_MOMENTS_UNITS NEWTONS`, manuale p. 349). Lo schema 6 (v2.7.0) aggiunge in coda le 10 righe "missione" (55–64); lo schema 5 le 5 righe "planform" (50–54); lo schema 4 (v2.6.0) le 4 righe della sezione "apertura" (46–49, carico lungo l'apertura,
vedi sotto); lo schema 3 (v2.5.0) le 6 righe della sezione "viscoso" (40–45). Le righe 1–39 sono quelle
dello schema 2, quindi il tagging HEEDS esistente resta valido. Lo schema 2 (v2.2.1) aveva riordinato le
chiavi rispetto alla v2.1 (riferimenti dopo i carichi, eco
degli ingressi in fondo): andava fatto prima del primo tagging in HEEDS.

### Trim e grandezze di missione (v2.7.0)

Blocchi JSON `trim` (`enabled`, `dalpha_deg` 2, `max_shift_deg` 6, `tol_rel` 0,005) e `mission` (`W_N`, `V_cruise`,
`V_min`, `rho`, `b_half_max`, `clmax_file`, `clmax_placeholder`). Con `trim.enabled` l'`aoa` del caso è solo α1: run ad
α1 e α1 + 2° (sottocartelle `trim_1`, `trim_2`, i loro VTK vengono cancellati), α* lineare su L_N = W_N, terzo run ad α*
nella cartella del design: **tutte** le chiavi di carico vengono da lì; `aoa` = α1, `alpha_trim` = α*. Status 3 se
|α* − α1| > 6° o se |L − W|/W > 0,5 % dopo il terzo run; i tre α e le tre L_N sono in `run_info.txt`. La velocità del caso
deve essere `V_cruise`; `b_half` oltre `b_half_max` è un errore di setup. Sempre (anche senza trim): `Di_N`, `D0_N`,
`AR`, `e_span` (CL e CDi del log, 5 cifre), `M_root_Nm` (carichi di sezione in NEWTONS: L'(y), controllo ∫L'dy = L_N/2
in `run_info.txt`), `CL_req`, `Re_tip`. Sezione critica (solo con trim): per ogni sezione C_L* = C_L1 + (clmax − cl1)
(C_L2 − C_L1)/(cl2 − cl1) con clmax(Re) a Re = V_min c/ν da `clmax_file`; `CLmax_wing` = minimo, `eta_stall` = posizione.
`profiles/clmax_vs_Re.csv` è un **segnaposto** (1,2 costante) dichiarato nel file e nel JSON.

### Carico lungo l'apertura (v2.6.0)

Dopo l'export di carichi e VTK lo script crea `spanload.n_sections` (default 40) sezioni sul piano XZ, addensate
verso l'estremità (η = sin(π/2·t)), e fa calcolare a FlightStream i carichi di sezione (`CREATE_NEW_SURFACE_SECTION`,
`UPDATE_ALL_SURFACE_SECTIONS`, `COMPUTE_SURFACE_SECTIONAL_LOADS COEFFICIENTS`, `EXPORT_SURFACE_SECTIONAL_LOADS`,
manuale 26.1 p. 363 e p. 250). cl = CFz cos α − CFx sin α sulla corda locale. Uscite: `spanload.csv` (η, y, corda,
cl, CFx, CFz, cm) e le righe 46–49 di `results.txt`; in `run_info.txt` il controllo (2/Sref)∫cl·c dy contro CL
(−0,53 % sulla baseline; una nota ATTENZIONE oltre l'1 %). Richiede `wing_frame` con asse in apertura ±y; la
semiapertura viene dal CCS in `ccs_wing`, da `spanload.semispan_m` in `fixed`. Senza: righe 46–49 a −999 (status
invariato); file dei carichi di sezione mancante o illeggibile: status 4. `spanload.enabled = false` lo disattiva.

### Accoppiamento viscoso e separazione (v2.5.0, ESPLORATIVO; modello di separazione ABBANDONATO per quest'ala in v2.6.0)

`solver.viscous_coupling = true`: FlightStream fa prima il run inviscido fino a convergenza, poi un secondo
run con lo strato limite accoppiato (manuale p. 205); il log ha due tabelle di iterazioni e la numerazione
continua nella seconda. In `results.txt`: `iterations_inviscid`, `iterations_viscous` (iterazioni della
seconda fase), `converged_viscous` (residui finali di entrambe le fasi sotto la soglia); se la fase viscosa
non converge o manca, **status 3**. `separation.model = "airfoil"`: modello Airfoil (Stratford); per il
manuale applica una pressione semi-empirica sulle facce separate **dopo** il run (p. 207): la soluzione del
solver non cambia (CL del log uguale a quello senza separazione), cambia la tabella dei carichi (CL, CMy).
CDi (vorticità) e CDo (attrito) non vedono la separazione: **non c'è una resistenza di pressione**.
`sep_marker_frac_up` = frazione del dorso con `Separation_marker` ≥ 0,5 (0 senza modello di separazione).
JSON di esempio: `configs/esplorativi/case_semiala_fixed_coupled.json` (C) e `configs/esplorativi/case_semiala_fixed_coupled_sep.json` (CS), con
`run.timeout_s = 600`. Risultati del DOE esplorativo e avvertenze: `STATO.md`. **Il modello di
separazione non è usabile per quest'ala** (diagnosi in `STATO.md` §3.13, sintesi in `REPORT_ALA.md` §4): resta
nel codice con default `none`, da non usare in HEEDS.

## Il JSON del caso

Le chiavi che iniziano con `_` sono commenti. Esempi: `case_semiala_fixed.json`, `case_semiala_ccs.json`.

| Chiave | Significato |
|---|---|
| `flightstream_exe` | percorso dell'eseguibile (vuoto = ricerca automatica) |
| `geometry.mode` | `fixed` (template .fsm) oppure `ccs_wing` (semiala da CCS); le altre chiavi di `geometry` dipendono dalla modalità e le legge solo `geometry.py` |
| `geometry.template_fsm` | (`fixed`) il .fsm già pronto: la mesh e il fluido vengono da lì |
| `geometry.reinitialize` | (`fixed`) `true` (default) = OPEN con `LOAD_SOLVER_INITIALIZATION DISABLE`, modello fisico e `INITIALIZE_SOLVER` dal blocco `solver`; `false` = inizializzazione e modello fisico salvati nel .fsm. La vecchia chiave `open_options` non è più ammessa (errore) |
| `geometry.profile`, `root_le_m`, `n_sections`, `size_by` | (`ccs_planform`, v2.7.0) profilo Selig (corda 1, LE in 0; `profiles/vespa_root.dat` da `profiles/estrai_vespa_root.py`), LE della radice [x, 0, z] in m, numero di sezioni (default 7, equidistanti), `c_root` (default) oppure `S_half` come variabile di dimensione (c_root = 2 S_half / (b_half (1 + taper))). Variabili: `c_root` o `S_half`, `taper`, `twist_tip_deg` (lineare in η, positivo a cabrare, attorno a c/4), `b_half`; linea dei quarti di corda dritta; Sref = area calcolata, Lref = MAC. Anche `te_type`, `root_cap_tol_m` e il blocco `mesh` come in ccs_wing |
| `geometry.base_ccs`, `te_type`, `root_cap_tol_m` | (`ccs_wing`) CCS di partenza, tipo di bordo d'uscita (`blended` = attuale; `sharp` NON fedele, CL −33 %; `blunt` richiede le base region, vedi STATO §3.14), tolleranza in y per togliere il tappo di radice |
| `mesh.u_pts`, `u_growth_type`, `u_growth_rate`, `u_periodicity`, `v_pts`, `v_growth_type`, `v_growth_rate`, `v_periodicity` | (`ccs_wing`, v2.6.0) righe `Mesh_U` (corda) e `Mesh_V` (apertura) del CCS, manuale 26.1 p. 82; default 120;3;1.1;2 e 64;1;1.0;1 = mesh attuale (convergenza: STATO §3.14). `geometry.mesh_u/mesh_v` non sono più accettate |
| `spanload.enabled`, `n_sections`, `semispan_m` | (v2.6.0) carico lungo l'apertura, vedi sopra; `semispan_m` obbligatoria in `fixed` |
| `case` | valori di default di `aoa` [deg], `velocity` [m/s], `sideslip` [deg], `altitude` [m] (solo con `override_fluid`) e delle variabili geometriche; `params.txt` li sovrascrive |
| `fluid.override_fluid` | `false` (default) = fluido del blocco `fluid` / del .fsm; `true` = fluido ISA alla quota `altitude`. Vale per tutte le modalità |
| `fluid.density`, `viscosity`, `pressure`, `temperature`, `specific_heat_ratio` | fluido del .fsm di riferimento [kg/m³, Pa·s, Pa, K, –]. `density` è sempre obbligatoria (q, L, D); in `ccs_wing` lo sono tutte (`FLUID_PROPERTIES`) |
| `solver.iterations`, `convergence`, `threads` | iterazioni massime, soglia di convergenza, thread del solver (0 = metà dei core logici, oggi 6 su 12). Il driver li fissa con `SET_MAX_PARALLEL_THREADS <n>` (manuale 26.1, p. 339) in ogni script; il manuale cita anche la variabile d'ambiente `OMP_NUM_THREADS` (p. 20), non usata |
| `solver.model`, `bl_type`, `roughness_nm`, `viscous_coupling`, `wall_collision_avoidance` | modello fisico: usato quando lo script inizializza la simulazione (`ccs_wing`, `fixed` con `reinitialize`); con `reinitialize = false` vale quello del .fsm |
| `solver.init_surfaces` | superfici di `INITIALIZE_SOLVER`: `[[indice, quad_mesher], …]` (es. `[[1, true]]`) oppure `-1` = tutte. Obbligatoria quando lo script inizializza |
| `solver.wake_termination_x`, `symmetry` | `"DEFAULT"` o un numero [m]; `"MIRROR"`, `"NONE"` (`ccs_wing` vuole `"MIRROR"`). `symmetry` obbligatoria quando lo script inizializza |
| `solver.vorticity_drag_boundaries` | superfici per il CDi di vorticità: lista di indici (es. `[1]`) oppure `-1` = tutte; `[]` = nessuna (`DELETE_VORTICITY_DRAG_BOUNDARIES`, CDi dall'integrazione della pressione, manuale p. 202 e 349; solo diagnostica, non validato) |
| `reference.sref_m2`, `lref_m` | area e lunghezza di riferimento. Obbligatorie in `fixed`; in `ccs_wing` `null` = calcolate dalla geometria (Sref = 2·S_semiala con symmetry_loads, Lref = MAC) |
| `reference.symmetry_loads` | carichi riportati al corpo intero (simmetria Mirror) |
| `reference.moment_point_m` | punto [x, y, z] in metri attorno a cui si calcolano i momenti; `null` = origine del frame 1, senza creare un nuovo sistema |
| `reference.moment_frame_index` | indice del nuovo sistema di riferimento (default 2). **Se il .fsm ha già sistemi utente, va aumentato** (es. 3) |
| `postproc.vtk_surfaces` | indici delle superfici da esportare nel VTK e usare per H/cf; `[]` = tutte |
| `postproc.strip`, `bin_width`, `xtr_threshold`, `te_window`, `exclude_le` | (`ccs_wing`) striscia in apertura, larghezza delle fasce in corda, soglia di transizione, finestra del bordo d'uscita, zona di ristagno esclusa |
| `separation.model`, `surfaces`, `valarezo`, `laminar_separation` | modello di separazione di FlightStream (manuale 26.1 p. 207, 340–341, 344), usato quando lo script inizializza la simulazione: `"none"` (default, comportamento validato) oppure `"airfoil"` (criterio di Stratford; **esplorativo, non validato**); superfici `[1]` o `-1` = tutte; Valarezo solo per ipersostentatori o freccia > 10°; `laminar_separation` = modello di separazione laminare per bassi Re. Lo script scrive sempre `DELETE_SEPARATION -1` (niente modelli rimasti nel .fsm) e `LAMINAR_SEPARATION` |
| `wing_frame` | assi dell'ala per le metriche di separazione: `{"chord_axis": "+x", "span_axis": "+y", "up_axis": "+z"}` (corda dal bordo d'attacco al bordo d'uscita, apertura dalla radice all'estremità, verso il dorso), opzionali `span_root_m` (default 0: si usano le facce con coordinata in apertura ≥ radice, cioè una semiala; le facce specchiate sono escluse) e `n_strips` (strisce in apertura, default 60). Assente o `null` = le cinque metriche di separazione valgono -999 (es. fusoliera); un valore non valido = status 1 |
| `postproc.sep_cf`, `le_xc`, `lo_te_xc`, `x_sep_eta`, `h_attached_xc_max` | (con `wing_frame`) soglia di separazione (cella separata se cf < −sep_cf, default 1e-5), x/c del bordo d'attacco per `sep_frac_up_le` (0,15), x/c del bordo d'uscita per `sep_frac_lo_te` (0,8), strisce usate per `x_sep_up` (η 0,05–0,95), x/c massimo per `H_max_attached_up` (0,95) |
| `run.timeout_s`, `run.save_fsm` | tempo massimo per FlightStream, per tentativo: circa 10 volte il tempo nominale del caso; ogni JSON ha il proprio (semiala: 240 s, per run di 15–27 s; default del driver se manca: 1800 s); salvare `case.fsm` nella cartella del design |
| `run.flightstream_process_names` | nomi dei processi di FlightStream per il controllo prima del lancio e la pulizia dopo (default `["FlightStream.exe"]`: in un run `-hidden` del 26.1 c'è un solo processo, senza figli) |
| `run.kill_stale_flightstream` | `false` (default): se c'è già un FlightStream attivo il run non parte e dà status 6; `true`: il driver lo chiude (anche la GUI, senza salvare) e poi lancia. Il driver non chiude mai altri processi se non è `true` |
| `run.license_retries`, `run.license_wait_s` | nuovi tentativi se la licenza non è disponibile (default 2, oltre al primo) e attesa prima di ognuno (default 60 s); poi `status = 6` |
| `heeds.success_statuses` | status per cui il processo esce con codice 0 (default `[0]`; es. `[0, 4]` nei DOE). Un valore non valido = status 1 |
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

Dalla diagnosi del 2026-10-04 (`STATO.md`): una cella separata ha cf < 0 e H bloccato a 3,9155; il
segno di cf è riferito alla linea di corrente superficiale (non alla corrente libera), quindi la zona
tra il ristagno e il bordo d'attacco **non** dà falsi positivi. `H_max` vale 3,9155 appena compare una
separazione e `sep_max` è sempre 0 senza modello di separazione: restano solo per compatibilità.
Le metriche si calcolano sulla semiala (facce d'estremità escluse), pesate sull'area:
- `sep_frac_up_le`: area separata del dorso a x/c < 0,15 / area del dorso (bolla di bordo d'attacco).
- `x_sep_up` (**diagnostica**): per ogni striscia in apertura (η 0,05–0,95) il primo x/c separato sul
  dorso dal bordo d'attacco; si scrive il minimo sulle strisce. **Convenzione: 1.0 = nessuna
  separazione sul dorso.** Comprende anche le bolle laminari corte prima della transizione (0,40 a 4°,
  1,0 a 8°, 0,02 a 12°): non è monotono con l'incidenza.
- `H_max_attached_up`, `x_H_max_attached_up` (**diagnostica**): H massimo sul dorso dove cf > 1e-5 e
  x/c ≤ 0,95, e il suo x/c (quanto lo strato limite attaccato è vicino alla separazione).
- `sep_frac_lo_te` (**diagnostica**): area separata del ventre a x/c > 0,8 / area del ventre (bolla del
  ventre al bordo d'uscita arrotondato).

**Per HEEDS:** il vincolo di separazione consigliato è `sep_frac_up_le` (es. `sep_frac_up_le ≤` una
soglia da scegliere per lo studio). `x_sep_up`, `H_max_attached_up`, `x_H_max_attached_up` e
`sep_frac_lo_te` sono solo diagnostica: **non usarli come vincoli né come obiettivi**. Con
`viscous_coupling = false` e senza modello di separazione i carichi restano comunque lineari.

Il metodo a pannelli con strato limite integrale non prevede la resistenza di pressione dovuta
alla separazione su corpi tozzi. `Sref` e `Lref` vanno scelti per il nuovo corpo.

## Da verificare

- Criterio di convergenza: `converged = 1` se i residui finali sono sotto `solver.convergence`,
  oppure se il solver si ferma prima di `solver.iterations` con residui finiti.
- Unità di `ORIGIN_*` in `EDIT_COORDINATE_SYSTEM` non documentate: l'origine viene comunque
  reimpostata con `SET_COORDINATE_SYSTEM_ORIGIN … METER`.
- Fisica: a 20 m/s il Reynolds sulla corda (≈ 4,7·10⁵) è sotto il campo del modello transizionale
  (5·10⁵–1,5·10⁶); H e cf sono indicatori comparativi.
