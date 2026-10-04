# HEEDS: procedura (Evaluation Only riuscito, DOE su aoa)

Procedura passo-passo per collegare la pipeline a Simcenter HEEDS MDO 2604.0 sul PC dove gira
FlightStream. Fonte dei nomi di menu e opzioni: il manuale installato
`C:\Program Files\Siemens\SimcenterHEEDS-2604.0\MDO\docs\en\HEEDSMDO.pdf` (pagine citate come "PDF p. N",
numero di pagina del file) e quanto visto nella GUI al primo Evaluation Only. Quello che non è né nel
manuale né verificato è segnato **DA VERIFICARE**.

`<REPO>` = `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline` (cartella di questo file).

## Esito del primo Evaluation Only (2026-10-04)

Progetto `C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala.heeds`, "Evaluate baseline design":
1 design, 0 errori, 53 s. status 0, CL 0,5767, CD 0,0202, CMy −0,1993, L_over_D 28,5495, aoa 4: uguale al
riferimento e a `heeds_inputs\fixed\results.txt` (39 righe, stesse chiavi e stessi valori).

Verificato in quell'occasione:
- **Variante A** del comando (`run_fs.bat` eseguito direttamente): funziona, `cmd /c` non serve. Codice di
  uscita 0 registrato da HEEDS in `<studio>\.aux\Process_execution_actions.log`.
- Nomi dei file: HEEDS copia `params.txt` nella cartella dell'analisi e legge `results.txt` dalla stessa
  cartella. `params.txt` scritto da HEEDS: `aoa = 4.00000` (punto decimale, 5 decimali).
- Tagging delimitato per posizione (riga, colonna 2): funziona. Delimitatori del parser di HEEDS:
  `\,;"=()'\t\s` (anche la virgola: per questo il separatore decimale deve essere il punto).
- Advanced Options: Max execution time = 1200 accettato; Default decimal delimiter = Period (opzioni:
  "From portal" (default), "Period", "Comma").
- Tempi (`POST_0\Design1\Analysis_1\Analysis.log`): comando 50,6 s, di cui FlightStream 48,9 s; driver
  ≈ 1,7 s; HEEDS ≈ 2 s (pulizia delle cartelle prima, estrazione delle risposte dopo). Nessun
  `FlightStream.exe` rimasto.
- Lo Study_1 di default è **Parameter Optimization (SHERPA, 35 valutazioni)**: senza un obiettivo dà
  "The study contains setup errors" e non parte nemmeno "Evaluate baseline design". Risolto con
  l'obiettivo Maximize `L_over_D`. Per i DOE usare un altro tipo di studio (passo 8).

## File da usare

HEEDS legge l'output con lo **stesso nome del file taggato**, e il driver legge `params.txt` e scrive
`results.txt`: per questo i file da aggiungere in HEEDS sono le copie delle baseline già rinominate in
`heeds_inputs\<modalità>\`.

| Modalità | JSON del caso (`--config`) | Input da aggiungere e taggare | Output da aggiungere e taggare |
|---|---|---|---|
| fixed (variabili: aoa, velocity, sideslip) | `<REPO>\case_semiala_fixed.json` | `<REPO>\heeds_inputs\fixed\params.txt` | `<REPO>\heeds_inputs\fixed\results.txt` |
| ccs_wing (variabili: aoa, velocity, chord_scale) | `<REPO>\case_semiala_ccs.json` | `<REPO>\heeds_inputs\ccs\params.txt` | `<REPO>\heeds_inputs\ccs\results.txt` |

`heeds_inputs\<modalità>\params.txt` e `results.txt` sono copie identiche di
`baseline\<modalità>\params_baseline.txt` e `results_baseline.txt`. Le baseline sono run reali lanciati con `run_fs.bat` in una cartella `Design_1\Analysis_1` (2026-10-04,
v2.3.0; fixed rilanciata in v2.3.1 con Sref = 1,82208): aoa = 4°, V = 20 m/s, CL 0,5767, CDi 0,0077,
CDo 0,0125, CMy −0,1993, Re 474985. Per il primo Evaluation Only usa **fixed**: un design deve ridare
esattamente `heeds_inputs\fixed\results.txt`.

## Prima di cominciare (checklist)

- [ ] **GUI di FlightStream chiusa** (Gestione attività: nessun `FlightStream.exe`). Il driver non lancia
      se c'è già un FlightStream attivo: `status = 6`, con i PID in `run_info.txt`.
- [ ] **Login Altair One valido.** La licenza di FlightStream su questo PC è Altair One ("hosted HWU"),
      legata all'**utente Windows**: HEEDS deve eseguire i design in locale e con lo stesso utente (niente
      esecuzione remota o con un altro account). Prima di uno studio lungo apri Altair License Utility
      e verifica il login. *Durata del token di Altair One: DA VERIFICARE.* Se il token scade durante lo
      studio, i design danno `status = 6` (licenza) dopo circa 3 minuti ciascuno.
- [ ] Test locali superati: `python -m unittest discover -s tests -v` nella cartella `<REPO>`.
- [ ] Facoltativo: `python heeds_mock.py --config case_semiala_fixed.json --var aoa=4 --root "C:\HEEDS prove\mock"`
      deve dare status 0 e CL 0,5767 (stesso comando che userà HEEDS).

## Passo 1 — Process e Analysis

Nel **Process** crea **una Analysis** con portale **"General (no portals)"**.

## Passo 2 — Files tab: input e output

- **Input:** aggiungi `<REPO>\heeds_inputs\fixed\params.txt` con **Target = Analysis folder**. HEEDS lo
  copia con questo nome nella cartella dell'analisi di ogni design, dove il driver legge `params.txt`.
  Alternativa, se si vuole partire da un file con un altro nome (es. `baseline\fixed\params_baseline.txt`):
  **Properties → Target → "Optionally enter a new file name"** = `params.txt`. Ultima alternativa, non più
  necessaria: lasciare il nome originale e aggiungere `--params <nome del file>` alle Command options.
- **Output:** aggiungi `<REPO>\heeds_inputs\fixed\results.txt`. HEEDS legge, nella cartella dell'analisi,
  il file con lo stesso nome del file taggato: `results.txt`, scritto dal driver sempre, anche in caso
  di errore.
- Non servono altri file: il JSON e i file della geometria (`..\semiala_run01.fsm`, CCS) sono letti
  dal loro percorso assoluto, risolto rispetto alla cartella del JSON.

## Passo 3 — Run in

**Run in = Analysis folder.** È il default ed è l'unico che non limita l'esecuzione in parallelo.
Il driver scrive tutti gli output (script FlightStream, `loads.txt`, `fs_log.txt`, `surface.vtk`,
`results.txt`, `run_info.txt`) nella cartella corrente, cioè quella dell'analisi del design; non scrive
file fuori da quella cartella. Percorsi con spazi: supportati (verificati con run reali di `fixed` e
`ccs_wing`).

## Passo 4 — Execution command (variante A, verificata)

HEEDS concatena **Execution command** e **Command options** con uno spazio (`Analysis.log`: `*COMMAND`).

| Campo | Valore usato e verificato |
|---|---|
| Portal | General (no portals) |
| Compute resource | Local |
| Execution command | `<REPO>\run_fs.bat` |
| Command options | `--config "<REPO>\case_semiala_fixed.json"` |

`run_fs.bat` fissa l'interprete Python (riga `set "PY=..."`), trova `fs_driver.py` accanto a sé, inoltra
gli argomenti e restituisce il codice di uscita del driver. La variante B (`cmd /c ""<REPO>\run_fs.bat"
--config "...""`) non serve; resta provata in `tests/test_run_fs.py`. Per `ccs_wing` cambiano il JSON
(`case_semiala_ccs.json`) e i file del passo 2 (`heeds_inputs\ccs\`).

## Passo 5 — Esecuzione in parallelo

**Num. designs to execute simultaneously = 1.** La licenza è una sola e il driver rifiuta di lanciare
FlightStream se ce n'è già uno attivo (`status = 6`): con più design in parallelo tutti tranne uno
fallirebbero.

Nell'**Execution tab → Analysis Execution Options → Advanced Options** dell'Analysis (PDF p. 125–126 e
133–134):

- **Max execution time = 1200 s**, solo come **rete di sicurezza**. Il timeout primario è quello del
  driver (`run.timeout_s` = 240 s nei JSON della semiala): è il driver a chiudere FlightStream e a scrivere
  `status = 2` o `6`. Caso peggiore di un design nel driver: 3 × 240 + 2 × 60 = 840 s. Manuale (PDF p. 133):
  *"If the analysis is not complete and this time limit is reached, Simcenter HEEDS marks the design as
  complete. Simcenter HEEDS tries to post-process the results at that time. The design will not be marked
  as an error unless there is an error in extracting the results. You must define a success condition if
  you expect some designs to exceed the Max execution time but want those designs to be marked as
  errors."* Il manuale non dice se il comando viene chiuso (**DA VERIFICARE**): il design diventa errore
  grazie alla Success condition del passo 6 (all'avvio il driver cancella il vecchio `results.txt`, quindi
  manca `schema_version = 2`). **Dopo un caso del genere controllare Gestione attività** e chiudere a mano
  un eventuale `FlightStream.exe`, altrimenti i design successivi danno `status = 6`.
- **Default decimal delimiter = Period** (opzioni nella GUI: "From portal", "Period", "Comma"; il default
  "From portal" è il valore del portale). Il PC è in italiano; `params.txt` e `results.txt` usano il punto e
  il driver rifiuta `4,0` con `status = 1`.
- **If an error occurs**: lasciare il default **"Stop process for current design, discard design data"**
  (testo visto nella GUI). Il manuale (PDF p. 133) dice solo *"It can either stop the process or continue
  to the next analysis"*: riguarda le analisi successive **dello stesso design**; con una sola Analysis non
  cambia nulla. A far proseguire lo studio con gli altri design è l'opzione dello Study tab (passo 9).
  Elenco completo delle opzioni: **DA VERIFICARE** nella GUI (il manuale non lo riporta per l'analisi).
- **If a constraint is infeasible** = "Continue to next analysis" (default); **Capture analysis output**
  spuntato: l'output del driver finisce in `POST_0\Design<N>\<Analysis>\Tool_<Analysis>_output.msg`.

## Passo 6 — Success condition (DA CONFIGURARE: nel primo Evaluation Only non c'era)

Senza Success condition HEEDS accetta un design se riesce a leggere le risposte (nel `.rpt` dello studio:
`successCondition: NONE`). Per il manuale (PDF p. 161) è proprio il caso da evitare: risultati parziali letti
come buoni. Nel manuale il controllo del codice di uscita e la condizione su file sono due meccanismi
**distinti**, entrambi nella stessa Analysis; vanno usati tutti e due.

**6a. Codice di uscita** (Advanced Options, PDF p. 126, passo 7 della procedura):
1. Process → seleziona `Analysis_1` → **Execution tab → Analysis Execution Options → Advanced Options**.
2. Spunta **"Compare analysis successful return value"** e inserisci **0**.
   (`run_fs.bat` restituisce 0 solo se lo status è in `heeds.success_statuses` del JSON, default `[0]`.)

**6b. Condizione su `results.txt`** (Managing conditions, PDF p. 154–161):
1. Nel gruppo **Tools** del ribbon **Process** clicca **Manage Conditions**.
2. Nel dialogo **Manage Conditions** clicca **Add Condition** e scegli il tipo **File contains** (*"Searches a
   file for text. If the text is found, the condition is marked as true."*). File: `results.txt`; testo:
   `schema_version = 2`. *(Come si sceglie il file e se il campo accetta gli spazi del testo: DA VERIFICARE;
   in alternativa cercare `schema_version`, che c'è solo nella riga 1.)*
3. **Close**.
4. Seleziona `Analysis_1` → **Execution tab → Analysis Execution Options → campo Conditions** → si apre il
   dialogo **Conditions** → in **Condition Event** scegli **Success** → seleziona la condizione creata.
5. **Evaluate in**: **Analysis folder** (default per Success) e Compute resource **Local**.

Effetto combinato (AND): il design è riuscito solo se il codice di uscita è 0 **e** `results.txt` contiene
`schema_version = 2`; altrimenti è un errore (*"If the condition is not met, the analysis is marked as an
error"*, PDF p. 129). *Che il confronto del codice di uscita e la Success condition si sommino così:
dal manuale è implicito (ognuno marca errore da solo), DA VERIFICARE con la prova di errore della checklist.*

**Alternativa tutta in una condizione** (operatori and/or tra gli elementi, PDF p. 156 e 158: *"The second and
subsequent items in the list allow you to choose how the item is combined with the previous item:
logical or, and."*): una sola condizione con due elementi, **File contains** `schema_version = 2` in
`results.txt` **and** **File contains** `success=1` in `run_info.txt` (ultima riga del driver,
`FS_DRIVER_RESULT status=<n> success=<0|1>`). `run_info.txt` non è un file di input/output dell'Analysis:
il manuale dice che per una success condition *"the file may be included in the analysis using a condition.
In addition, a generic file can be added as a condition"* (PDF p. 157) — **DA VERIFICARE** come.

**Nessuna Finished condition**: per il manuale serve solo per esecuzione remota o code di job (PDF p. 160);
qui l'esecuzione è locale.

`heeds.success_statuses`: `[0]` per l'ottimizzazione; `[0, 4]` per i DOE in cui H/cf non sono obiettivi
(status 4 = CL/CD validi, manca solo lo strato limite). Non metterci mai 1, 2, 3, 5, 6.

## Passo 7 — Tagging

### Variabili (input, delimitatore `=`)

Tagga il numero a destra di `=` sulle righe seguenti (le prime tre righe sono commenti, ignorati dal driver).

| Riga | fixed (`heeds_inputs\fixed\params.txt`) | ccs_wing (`heeds_inputs\ccs\params.txt`) | Unità | Note |
|---|---|---|---|---|
| 4 | `aoa = 4.0` | `aoa = 4.0` | deg | angolo d'attacco |
| 5 | `velocity = 20.0` | `velocity = 20.0` | m/s | velocità di volo e di riferimento |
| 6 | `sideslip = 0.0` | `chord_scale = 1.0` | deg / – | `chord_scale`: fattore sulla corda, > 0 |

- Nel primo Evaluation Only tagga solo `aoa`; poi `chord_scale` (con il JSON `ccs`).
- Il driver accetta qualsiasi formato di stampa numerico di HEEDS (`4`, `4.0`, `4.000000E+00`,
  `-1.5E-01`, CRLF, spazi); rifiuta con `status = 1` valori non numerici, chiavi ripetute o sconosciute.
- `altitude` non è ammessa (il fluido è quello del JSON); in `ccs_wing` `sideslip` deve restare 0.
- Le variabili non presenti nel file prendono il valore del blocco `case` del JSON.

### Risposte (output, delimitatore `=`)

Tagga il numero a destra di `=` di ogni riga di `heeds_inputs\<modalità>\results.txt`. **L'ordine delle 39 righe è
fisso** e uguale per tutte le modalità (`RESULTS_SCHEMA`, `schema_version = 2`); le chiavi non pertinenti
alla modalità valgono `-999`; le chiavi future si aggiungeranno solo in fondo al file.

| Riga | Chiave | Sezione | Baseline fixed | Baseline ccs_wing | Uso |
|---|---|---|---|---|---|
| 1 | `schema_version` | stato | 2 | 2 | controllo (Success condition) |
| 2 | `status` | stato | 0 | 0 | **vincolo** `status = 0` |
| 3 | `converged` | stato | 1 | 1 | diagnostica |
| 4 | `iterations` | stato | 91 | 91 | diagnostica |
| 5 | `CL` | carichi | 0.5767 | 0.5767 | risposta (confrontabile solo a Sref costante) |
| 6 | `CD` | carichi | 0.0202 | 0.0202 | risposta (confrontabile solo a Sref costante) |
| 7 | `CDi` | carichi | 0.0077 | 0.0077 | risposta (confrontabile solo a Sref costante) |
| 8 | `CDo` | carichi | 0.0125 | 0.0125 | risposta (confrontabile solo a Sref costante) |
| 9 | `CMx` | carichi | 0 | 0 | risposta (confrontabile solo a Sref costante) |
| 10 | `CMy` | carichi | -0.1993 | -0.1993 | risposta (confrontabile solo a Sref costante) |
| 11 | `CMz` | carichi | 0 | 0 | risposta (confrontabile solo a Sref costante) |
| 12 | `L_over_D` | carichi | 28.5495 | 28.5495 | **obiettivo** consigliato |
| 13 | `L_N` | carichi | 257.444 | 257.445 | obiettivo/vincolo (N) |
| 14 | `D_N` | carichi | 9.01747 | 9.01748 | obiettivo/vincolo (N) |
| 15 | `Sref_m2` | riferimenti | 1.82208 | 1.82208 | controllo |
| 16 | `Lref_m` | riferimenti | 0.345091 | 0.345091 | controllo |
| 17 | `Re_ref` | riferimenti | 474985 | 474985 | controllo |
| 18 | `q_Pa` | riferimenti | 245 | 245 | controllo |
| 19 | `xtr_up` | strato_limite | -999 | 0.378162 | diagnostica (solo ccs_wing) |
| 20 | `xtr_lo` | strato_limite | -999 | 0.932521 | diagnostica (solo ccs_wing) |
| 21 | `H_te_up` | strato_limite | -999 | 1.72966 | diagnostica (solo ccs_wing) |
| 22 | `H_te_lo` | strato_limite | -999 | 2.47022 | diagnostica (solo ccs_wing) |
| 23 | `H_max_up` | strato_limite | -999 | 3.21253 | diagnostica (solo ccs_wing) |
| 24 | `H_max_lo` | strato_limite | -999 | 3.9155 | diagnostica (solo ccs_wing) |
| 25 | `cf_min_up` | strato_limite | -999 | 0.000392584 | diagnostica (solo ccs_wing) |
| 26 | `cf_min_lo` | strato_limite | -999 | -0.000800156 | diagnostica (solo ccs_wing) |
| 27 | `area_frac_cf_neg` | strato_limite | 0.0175283 | 0.0175283 | compatibilità (non usare) |
| 28 | `H_max` | strato_limite | 3.9155 | 3.9155 | compatibilità (non usare) |
| 29 | `sep_max` | strato_limite | 0 | 0 | compatibilità (non usare) |
| 30 | `sep_frac_up_le` | strato_limite | 0 | 0 | **vincolo** di separazione consigliato |
| 31 | `x_sep_up` | strato_limite | 0.397943 | 0.397943 | solo diagnostica |
| 32 | `H_max_attached_up` | strato_limite | 3.53439 | 3.53439 | solo diagnostica |
| 33 | `x_H_max_attached_up` | strato_limite | 0.397943 | 0.397943 | solo diagnostica |
| 34 | `sep_frac_lo_te` | strato_limite | 0.0306049 | 0.0306049 | solo diagnostica |
| 35 | `aoa` | ingressi | 4 | 4 | controllo |
| 36 | `velocity` | ingressi | 20 | 20 | controllo |
| 37 | `altitude` | ingressi | -999 | -999 | controllo |
| 38 | `sideslip` | ingressi | 0 | 0 | controllo |
| 39 | `chord_scale` | ingressi | -999 | 1 | controllo |

Uso consigliato:
- **Obiettivo:** `L_over_D` (riga 12), oppure `L_N` / `D_N` (righe 13–14). Con `chord_scale` Sref cambia da
  un design all'altro e i coefficienti (CL, CD, CM…) **non** sono confrontabili tra design.
- **Vincoli:** `status = 0` (riga 2; *come HEEDS esprime un'uguaglianza: DA VERIFICARE*, es. `≤ 0` e `≥ 0`);
  separazione: `sep_frac_up_le` (riga 30) ≤ una soglia da scegliere.
- **Solo diagnostica, non vincoli né obiettivi:** righe 3–4, 19–29, 31–34.
- **Controllo:** righe 1, 15–18, 35–39 (eco dei valori effettivamente usati).

## Passo 8 — Study: DOE su aoa (0, 2, 4, 6, 8, 10, 12)

**Il Full factorial di HEEDS non serve qui:** il manuale lo prevede solo come metodo a 2 livelli e a 3
livelli (PDF p. 1005–1008: "2-Level sampling methods", "3-Level sampling methods"). Per avere esattamente 7
valori si usa lo **Sweep** (dialogo **Define Variable Sweep**, PDF p. 935): *"A sweep creates designs with
all possible combinations of the selected variables"* — cioè un fattoriale completo su N livelli — con
colonne **Min**, **Max**, **# values**, **Increment** e **Total number of designs**.

**Procedura consigliata: nuovo studio "Evaluation Only - User prescribed"** (PDF p. 916–918, 929–933). Il
manuale lo indica per *"Run design sweeps by varying one or more parameters"* e *"Objectives and constraints
are not required"*. Creare uno studio nuovo lascia intatto Study_1.
1. **Study tab → freccia accanto a Create Study** (oppure tasto destro sul progetto → Create Study).
2. Dialogo **Create New Study**: Study name `Study_2`; Study type **Evaluation Only - User prescribed**;
   **Copy data from** = `Study_1` con **Copy variable definitions** e **Copy response goals**. **OK**.
3. Nel nuovo studio: **Study tab → Methods** → definire i design (PDF p. 932: *"In an Evaluation Only - User
   prescribed study, select the Study tab and then click Methods. You can define the designs here."*).
4. Clicca **Sweep** → nel dialogo **Define Variable Sweep** lascia spuntato solo `aoa`: **Min = 0**,
   **Max = 12**, **# values = 7** (Increment calcolato = 2). **Total number of designs = 7**. Conferma con
   **Replace** (sostituisce i design esistenti) *(passaggi esatti nel dialogo: DA VERIFICARE)*.
5. Opzioni del passo 9, poi Run. La cartella dello studio sarà
   `C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala_Study_2` (nome = `<Progetto>_<Studio>`).

**Alternativa DOE** (stesso risultato): Create Study con Study type **DOE - Screening and Data
Characterization** → **Study tab → Methods** → spunta **Factor** per `aoa` → Sampling Method **Custom sampling
(RSM only)** → **Define Designs** → **Sweep** come al punto 4 (PDF p. 932–933 e 1005).

**Cambiare il tipo di Study_1** invece di crearne uno nuovo: sul Study tab c'è la lista **Study type** (PDF
p. 890–891); funziona allo stesso modo, ma rilanciare uno studio **cancella le sue cartelle `HEEDS_0` e
`POST_0`** (visto in `.aux\Process_execution_actions.log`: "Remove previous HEEDS folder"). Meglio uno
studio nuovo per ogni DOE.

**Resolution** (solo per gli studi di ottimizzazione, PDF p. 728): sul **Parameters tab**, campo
**Resolution** della variabile continua; *"The resolution defines a set of evenly spaced values between and
including your minimum and maximum values."* Oggi `aoa` ha Min 0, Max 12, Resolution 101 (passo 0,12°):
per uno SHERPA su aoa a passi di 2° basterebbe Resolution 7. Non serve per lo sweep.

Dopo il DOE su aoa: sweep su `chord_scale` (progetto con `case_semiala_ccs.json` e `heeds_inputs\ccs\`),
poi **SHERPA** (Parameter Optimization) con obiettivo `L_over_D` (oppure `L_N`/`D_N`), non CL.

## Passo 9 — Opzioni per il DOE (Study tab, PDF p. 892–894)

- **Saved Designs → Success designs = All designs** (*"Saves the input and output files for all designs
  that are evaluated in the study run"*). Altre opzioni: None, Best designs, All best designs, All feasible
  designs, Save baseline. Dopo il primo DOE usare Best designs: i VTK pesano ≈ 10 MB a design.
- **Saved Designs → Error Designs = Rename** (*"Renames the Design<X> folder with the error designs to
  Design<X>-ERROR"*). Altre opzioni: Keep, Delete.
- **Run Options → "Do not stop HEEDS for a design-based error"** spuntato: *"Informs Simcenter HEEDS MDO not
  to exit if the first design, or any user-defined designs, is an error. It also tells Simcenter HEEDS MDO
  to continue processing DOE studies even if there are errors."* È **questa** l'opzione che fa proseguire il
  DOE con gli altri design (nello Study_1 di oggi era `no`).
- **If an error occurs** (Analysis, passo 5): default "Stop process for current design, discard design
  data", vedi sopra.
- Nota: lo Study_1 di default è SHERPA e richiede un obiettivo anche per "Evaluate baseline design"
  (osservato nella GUI); lo studio "Evaluation Only - User prescribed" non ne richiede.

## Dove guardare quando un design fallisce

`<studio>` = cartella dello studio, es. `C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\semiala_Study_1`.

| File | Contenuto |
|---|---|
| `<studio>\HEEDS_0\Design<N>\Analysis_1\run_info.txt` | **primo file da aprire**: status del driver, motivo, ultima riga `FS_DRIVER_RESULT` |
| `<studio>\HEEDS_0\Design<N>\Analysis_1\` | anche `params.txt` scritto da HEEDS, `results.txt`, `fs_script.txt`, `fs_stdout.txt` (FlightStream, compresa la licenza), `fs_log.txt`, `loads.txt`, `surface.vtk` |
| `<studio>\HEEDS_0\Design<N>\design_variable_and_parameter_values` | valori delle variabili del design scritti da HEEDS |
| `<studio>\POST_0\Design<N>\Analysis_1\Tool_Analysis_1_output.msg` | output del driver catturato da HEEDS (Capture analysis output) |
| `<studio>\POST_0\Design<N>\Analysis_1\Analysis.log` | comando eseguito, orari di inizio e fine, `*STATUS` (SUCCESS/errore), estrazione di ogni risposta |
| `<studio>\POST_0\Design<N>\Analysis_1\<risposta>.heeds.out` | valore letto per ogni risposta (`STATUS = Success`) |
| `<studio>\.aux\Process_execution_actions.log` | ogni azione di HEEDS con orari e **codice di uscita** del comando (`JC-Dn:end … <exit code>`) |
| `<studio>\Study_1.log`, `Study_1.mes` | log dello studio (licenza HEEDS, design valutati, avvisi come "parallel option has NOT been enabled") |
| `<studio>\HEEDS0.rpt` | riepilogo della configurazione (variabili con Resolution, risposte, Advanced Options, `successCondition`, `saveDesigns`…) |
| `<studio>\HEEDS0.res` | tabella dei design valutati con tutte le risposte (CSV) |
| `<studio>\M_in_Analysis_1_params.txt`, `M_out_Analysis_1_results.txt` | definizione del tagging (riga, colonna, delimitatori) |
| `<studio>\Study_1.in`, `Process1.in`, `Definitions.in`, … | input del solutore HEEDS generati dal progetto |

Attenzione: HEEDS ha copiato `params.txt` nella **cartella del progetto**
(`C:\Users\UtenteLocale\Desktop\heeds\semiala_fixed\params.txt`) e usa quella copia (`inputFile: …,
projectFolder`): se cambia `heeds_inputs\…\params.txt` nel repo, va ricaricato in HEEDS.

## Passo 10 — Design con status 2 o 6, Stop

- Status 2 (timeout) e 6 (licenza, o FlightStream già attivo) dipendono dalla macchina, non dal design:
  in HEEDS risultano errori. Vanno rilanciati con **Add more designs / Study restart** *(DA VERIFICARE
  nella GUI)*. Il motivo è in `run_info.txt` della cartella del design.
- **"Retry if not successful or fails to start"** ritenterebbe anche gli errori deterministici (status 1,
  3, 5): lascialo **disattivato** all'inizio.
- **Test dello Stop (primo Evaluation Only):** avvia un design, premi Stop mentre FlightStream gira, poi
  apri Gestione attività e cerca `FlightStream.exe`. *Se HEEDS chiude anche i processi figli del comando:
  DA VERIFICARE.* Se resta un `FlightStream.exe` orfano, **chiudilo a mano** (Gestione attività → Termina
  attività) prima di riavviare lo studio: altrimenti il design successivo dà `status = 6` ("FlightStream
  già attivo", PID in `run_info.txt`). `run.kill_stale_flightstream = true` nel JSON lo farebbe in
  automatico, ma chiuderebbe anche una GUI aperta senza salvare: default `false`.

## Checklist (prima del DOE)

- [ ] GUI di FlightStream chiusa, login Altair One valido.
- [ ] Execution tab → Advanced Options: Max execution time = 1200 s, Default decimal delimiter = punto.
- [ ] Nella cartella del design ci sono `params.txt` (copiato da HEEDS con questo nome), `fs_script.txt`,
      `results.txt`, `run_info.txt`.
- [ ] `results.txt` comincia con `schema_version = 2`; HEEDS legge gli stessi valori del file e di
      `heeds_inputs\fixed\results.txt`.
- [ ] Success condition configurata (passo 6: codice di uscita 0 e "File contains" `schema_version = 2`) e
      design riuscito.
- [ ] Prova di errore: una chiave sbagliata in `params.txt` (es. `aoa_x = 4`) → `status = 1`, codice di
      uscita 1, design rinominato `Design<X>-ERROR`.
- [ ] Test dello Stop (passo 10): nessun `FlightStream.exe` orfano, oppure chiuso a mano.

## Riferimento: status e contratto

| status | Significato | Coefficienti scritti? |
|---|---|---|
| 0 | ok | sì |
| 1 | errore di setup o generico (file mancante, `params.txt` non valido, chiave non ammessa, JSON non valido, coefficienti incompleti, dry-run) | no |
| 2 | timeout (`run.timeout_s`, per tentativo) | no |
| 6 | FlightStream non disponibile: licenza (dopo `run.license_retries` nuovi tentativi) oppure FlightStream già attivo prima del lancio | no |
| 3 | solver non convergente | sì, solo per diagnosi |
| 5 | risultati non fisici (CD ≤ 0, CDo < 0, valori non finiti) | sì, solo per diagnosi |
| 4 | H/cf non estraibili (CL/CD validi) | sì |

Se valgono più condizioni insieme conta la prima dall'alto (1, 2, 6, 3, 5, 4). `results.txt` e
`run_info.txt` sono scritti **sempre**; il motivo di uno status diverso da 0 è in `run_info.txt`.
Dettagli del driver, del JSON e delle metriche: `README.md`.
