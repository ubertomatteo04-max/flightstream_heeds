# HEEDS: procedura per il primo Evaluation Only

Procedura passo-passo per collegare la pipeline a HEEDS MDO 2026 sul PC dove gira FlightStream.
I nomi di menu e campi di HEEDS scritti qui sono solo quelli già noti; tutto il resto è segnato
**DA VERIFICARE** e va controllato nella GUI o nel manuale di HEEDS al primo uso.

`<REPO>` = `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline` (cartella di questo file).

## File da usare

| Modalità | JSON del caso (`--config`) | File di input da taggare | File di output da taggare |
|---|---|---|---|
| fixed (variabile: aoa, velocity, sideslip) | `<REPO>\case_semiala_fixed.json` | `<REPO>\baseline\fixed\params_baseline.txt` | `<REPO>\baseline\fixed\results_baseline.txt` |
| ccs_wing (variabili: aoa, velocity, chord_scale) | `<REPO>\case_semiala_ccs.json` | `<REPO>\baseline\ccs\params_baseline.txt` | `<REPO>\baseline\ccs\results_baseline.txt` |

Le baseline sono run reali lanciati con `run_fs.bat` in una cartella `Design_1\Analysis_1` (2026-10-04,
v2.3.0): aoa = 4°, V = 20 m/s, CL 0,5767, CDi 0,0077, CDo 0,0125, CMy −0,1993, Re 474985. Per il primo
Evaluation Only usa **fixed**: un design deve ridare esattamente `results_baseline.txt`.

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

- **Input:** `params.txt`, con **Target = Analysis folder**. Come contenuto parti da
  `<REPO>\baseline\fixed\params_baseline.txt`. Il driver legge il file di nome **`params.txt`** nella
  cartella dell'analisi. *Se HEEDS lo copia con il nome originale (`params_baseline.txt`): DA VERIFICARE.*
  In quel caso aggiungi `--params params_baseline.txt` alle Command options (passo 4).
- **Output:** `results.txt` (scritto dal driver nella cartella dell'analisi, sempre, anche in caso di
  errore). Per il tagging usa come esempio `<REPO>\baseline\fixed\results_baseline.txt`.
- Non servono altri file: il JSON e i file della geometria (`..\semiala_run01.fsm`, CCS) sono letti
  dal loro percorso assoluto, risolto rispetto alla cartella del JSON.

## Passo 3 — Run in

**Run in = Analysis folder.** È il default ed è l'unico che non limita l'esecuzione in parallelo.
Il driver scrive tutti gli output (script FlightStream, `loads.txt`, `fs_log.txt`, `surface.vtk`,
`results.txt`, `run_info.txt`) nella cartella corrente, cioè quella dell'analisi del design; non scrive
file fuori da quella cartella. Percorsi con spazi: supportati (verificati con run reali di `fixed` e
`ccs_wing`).

## Passo 4 — Execution command (varianti A e B)

HEEDS concatena **Execution command** e **Command options** con uno spazio. `run_fs.bat` fissa
l'interprete Python (riga `set "PY=..."`), trova `fs_driver.py` accanto a sé, inoltra gli argomenti e
restituisce il codice di uscita del driver.

**Variante A (prima scelta)**

| Campo | Valore |
|---|---|
| Execution command | `"<REPO>\run_fs.bat"` |
| Command options | `--config "<REPO>\case_semiala_fixed.json"` |

**Variante B** — se HEEDS non esegue un `.bat` direttamente (le virgolette esterne sono obbligatorie:
`cmd /c` toglie la prima e l'ultima)

| Campo | Valore |
|---|---|
| Execution command | `cmd` |
| Command options | `/c ""<REPO>\run_fs.bat" --config "<REPO>\case_semiala_fixed.json""` |

**Quale variante serve: DA VERIFICARE al primo Evaluation Only.** Entrambe sono provate in locale
(`tests/test_run_fs.py`): codice di uscita 0 e 1 propagati, anche con cartelle e JSON con spazi.
Per `ccs_wing` cambia solo il JSON (`case_semiala_ccs.json`). Se serve (passo 2), aggiungi
`--params params_baseline.txt` in fondo alle Command options (dentro le virgolette esterne nella variante B).

## Passo 5 — Esecuzione in parallelo

**Num. designs to execute simultaneously = 1.** La licenza è una sola e il driver rifiuta di lanciare
FlightStream se ce n'è già uno attivo (`status = 6`): con più design in parallelo tutti tranne uno
fallirebbero.

Timeout del design in HEEDS *(nome del campo: DA VERIFICARE)*: maggiore del tempo massimo del driver,
così è il driver a chiudere FlightStream e a scrivere `status = 2` o `6`. Caso peggiore con i JSON della
semiala: `(license_retries + 1) × timeout_s + license_retries × license_wait_s` = 3 × 240 + 2 × 60 = 840 s
→ in HEEDS almeno **15 minuti**. Un run normale dura 15–45 s (più lento con il PC carico).

## Passo 6 — Success condition

In **Conditions → Success**:

1. **"Compare analysis successful return value" = 0** (codice di uscita di `run_fs.bat`: 0 se lo status
   è in `heeds.success_statuses` del JSON, default `[0]`);
2. **AND "File contains"** `schema_version = 2` nel file `results.txt`. Garantisce che `results.txt` abbia
   lo schema su cui sono state taggate le risposte: se un giorno lo schema cambia, i design falliscono
   invece di leggere righe sbagliate. *Come HEEDS combina due condizioni in AND: DA VERIFICARE.*

Alternativa al codice di uscita: "File contains" `success=1` nel file `run_info.txt` (ultima riga, sempre
presente: `FS_DRIVER_RESULT status=<n> success=<0|1>`).

**Nessuna Finished condition**: l'esecuzione è locale e il comando finisce quando il design è finito.

`heeds.success_statuses`: `[0]` per l'ottimizzazione; `[0, 4]` per i DOE in cui H/cf non sono obiettivi
(status 4 = CL/CD validi, manca solo lo strato limite). Non metterci mai 1, 2, 3, 5, 6.

## Passo 7 — Tagging

### Variabili (input, delimitatore `=`)

Tagga il numero a destra di `=` sulle righe seguenti (le prime tre righe sono commenti, ignorati dal driver).

| Riga | fixed (`baseline\fixed\params_baseline.txt`) | ccs_wing (`baseline\ccs\params_baseline.txt`) | Unità | Note |
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

Tagga il numero a destra di `=` di ogni riga di `results_baseline.txt`. **L'ordine delle 39 righe è
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
| 13 | `L_N` | carichi | 257.447 | 257.445 | obiettivo/vincolo (N) |
| 14 | `D_N` | carichi | 9.01757 | 9.01748 | obiettivo/vincolo (N) |
| 15 | `Sref_m2` | riferimenti | 1.8221 | 1.82208 | controllo |
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

## Passo 8 — Study

1. **Evaluation Only** a aoa = 4° (fixed): deve coincidere con `baseline\fixed\results_baseline.txt` e con
   il mock (CL 0,5767, CDi 0,0077, CDo 0,0125, CMy −0,1993, Re 474985).
2. Poi **DOE Full factorial** su `aoa` (fixed), e su `chord_scale` (ccs_wing).
3. Poi **SHERPA** con obiettivo `L_over_D` (oppure `L_N`/`D_N`), non CL.

## Passo 9 — Saved designs

- **Error designs = Rename** (`Design<X>-ERROR`): restano su disco, con `run_info.txt` che spiega lo status.
- **Success designs = All designs** nel primo DOE; poi **Best designs**, perché i VTK pesano (≈ 10 MB a
  design).
- Nei DOE spunta **"Do not stop HEEDS for a design-based error"**.

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

## Checklist del primo Evaluation Only

- [ ] GUI di FlightStream chiusa, login Altair One valido.
- [ ] Nella cartella del design ci sono `params.txt` (con il nome giusto, passo 2), `fs_script.txt`,
      `results.txt`, `run_info.txt`.
- [ ] Variante A o B del comando: annotare quale funziona (e aggiornare questo file).
- [ ] `results.txt` comincia con `schema_version = 2`; HEEDS legge gli stessi valori del file e di
      `baseline\fixed\results_baseline.txt`.
- [ ] Il design risulta riuscito (codice di uscita 0 AND "File contains" `schema_version = 2`).
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
