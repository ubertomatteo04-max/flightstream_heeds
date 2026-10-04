# Collegare fs_driver.py a HEEDS

Guida per quando la licenza HEEDS sarà attiva. Le voci di menu e i nomi dei campi di HEEDS
**non sono stati verificati**: dove compare *(da verificare)* va controllata la documentazione di
HEEDS. Prima di HEEDS, prova tutto con `heeds_mock.py` (vedi README).

## Cosa deve fare HEEDS per ogni design

1. Creare una cartella di lavoro per il design *(nome e posizione: da verificare)*.
2. Copiarci `params.txt` con i valori del design al posto di quelli di esempio.
3. Lanciare il comando qui sotto **in quella cartella**.
4. Leggere `results.txt` dalla stessa cartella.

## Comando

HEEDS esegue il comando con cartella corrente = la cartella dell'analisi del design, dove copia
`params.txt`. Il comando è `run_fs.bat` (accanto a `fs_driver.py`), che fissa l'interprete Python,
trova `fs_driver.py` con `%~dp0`, inoltra gli argomenti e restituisce il codice di uscita del driver.

Variante A (prima scelta):
```
"<CARTELLA>\run_fs.bat" --config "<CARTELLA>\case_semiala_fixed.json"
```
Variante B, se HEEDS non esegue un `.bat` direttamente (virgolette esterne obbligatorie: `cmd /c`
toglie la prima e l'ultima):
```
cmd /c ""<CARTELLA>\run_fs.bat" --config "<CARTELLA>\case_semiala_fixed.json""
```
**DA VERIFICARE al primo Evaluation Only** quale delle due serve. Entrambe sono provate in locale
(`tests/test_run_fs.py`): codice di uscita 0 e 1 propagati, anche con cartella di lavoro e JSON in
percorsi con spazi.

- `<CARTELLA>` = percorso assoluto di questa cartella (oggi
  `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline`). Il JSON va scelto in base al caso
  e va indicato con il percorso **assoluto**: tutti i percorsi del JSON (.fsm, CCS, eseguibile di
  FlightStream) sono risolti rispetto alla cartella del JSON, mai rispetto alla cartella corrente.
- Tutti gli output (script, carichi, log, VTK, `results.txt`, `run_info.txt`) vanno nella cartella
  corrente del design; il driver non scrive file fuori da quella cartella.
- L'interprete Python è fissato in testa a `run_fs.bat` (`set "PY=..."`, oggi
  `C:\Users\UtenteLocale\AppData\Local\Programs\Python\Python313\python.exe`): così non dipende dal PATH
  che vede HEEDS. Su un altro PC: `python -c "import sys; print(sys.executable)"` e correggere la riga.
- FlightStream: conviene impostare la variabile d'ambiente `FLIGHTSTREAM_EXE`, oppure riempire
  `flightstream_exe` nel JSON, così non dipende da cosa vede HEEDS. Su questo PC la ricerca
  automatica trova `C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe`.
- Cartelle di lavoro con spazi: **supportate**. Verificato il 2026-10-04 con run reali (FlightStream
  26.1) di `fixed` e `ccs_wing` in `C:\fs test\DOE aoa\Design_1\Analysis_1` e `C:\fs test\DOE ccs\...`:
  status 0, CL 0,5767, Re 474985. Lo script FlightStream scrive i percorsi senza virgolette (anche
  `FILE C:\fs test\...\case_ccs.csv`) e FlightStream li legge correttamente.
- **Un solo FlightStream alla volta.** Prima di ogni lancio il driver controlla che non ci sia già un
  processo `FlightStream.exe` (GUI aperta, processo orfano, un altro design): aspetta fino a 10 s e,
  se c'è ancora, **non lancia** e dà `status = 6` con i PID in `run_info.txt`. Quindi in HEEDS il numero
  di design eseguiti in parallelo deve essere 1, e la GUI di FlightStream va chiusa durante lo studio.
  Con `run.kill_stale_flightstream = true` nel JSON il driver chiude da solo quei processi (anche la
  GUI, con le modifiche non salvate): default `false`, non attivarlo se sullo stesso PC si usa la GUI.
- Timeout HEEDS: maggiore del tempo massimo del driver, così è il driver a gestire il timeout e a
  scrivere `status = 2` o `6` *(campo di timeout in HEEDS: da verificare)*. Caso peggiore:
  `(license_retries + 1) × timeout_s + license_retries × license_wait_s` (default 3 × 1800 + 2 × 60 s);
  in pratica un tentativo senza licenza si chiude in ≈ 15 s.

## Input: `params.txt`

Formato `chiave = valore`, una variabile per riga. In HEEDS va marcato *(il nome di questa
operazione, "tagging" o simile, è da verificare)* il valore a destra dell'uguale di ogni variabile
di progetto.

| Variabile | Unità | Modalità | Note |
|---|---|---|---|
| `aoa` | deg | tutte | angolo d'attacco |
| `velocity` | m/s | tutte | velocità di volo e di riferimento |
| `sideslip` | deg | tutte | deve restare 0 in `ccs_wing` (simmetria Mirror) |
| `altitude` | m | solo con `fluid.override_fluid = true` (tutte le modalità) | quota ISA (densità, viscosità); troposfera, < 11 000 m |
| `chord_scale` | – | solo `ccs_wing` | fattore sulla corda di tutte le sezioni, > 0 |

Di default il fluido è quello del blocco `fluid` del JSON (= quello del `.fsm` di riferimento) in
tutte le modalità: `altitude` in `params.txt` blocca il design con `status = 1` (messaggio in
`run_info.txt`).

- Nel file vanno solo le variabili che HEEDS fa variare; le altre prendono il valore del blocco
  `case` del JSON.
- Una chiave non ammessa (errore di battitura, o `chord_scale` con `fixed`) blocca il design con
  `status = 1`: è voluto, così un errore non passa inosservato.
- I range delle variabili sono da decidere per il tuo studio. Non sono scritti nel codice.

## Output: `results.txt`

Formato `chiave = valore`, sempre le stesse chiavi nello stesso ordine; `-999` = valore mancante.
In HEEDS ogni risposta si definisce leggendo il numero dopo `=` sulla riga della chiave
*(modalità di lettura per chiave o per riga: da verificare; le righe hanno posizione fissa)*.

Ordine fisso per tutte le modalità (`RESULTS_SCHEMA` in `fs_driver.py`, `schema_version = 2`, v2.2.1); le
chiavi non pertinenti alla modalità valgono -999. Le chiavi nuove si aggiungono solo in fondo al file.

| # | Risposta | Unità | Significato |
|---|---|---|---|
| 1 | `schema_version` | – | versione dello schema di results.txt (oggi 2); cambia a ogni modifica dell'elenco o dell'ordine delle chiavi |
| 2 | `status` | – | 0 ok, 1 errore, 2 timeout, 3 non convergente, 4 H/cf non estraibili, 5 non fisico, 6 FlightStream non disponibile (licenza, oppure FlightStream già attivo prima del lancio) |
| 3–4 | `converged`, `iterations` | – | 1 se convergente; iterazioni eseguite |
| 5–8 | `CL`, `CD`, `CDi`, `CDo` | – | coefficienti di portanza e resistenza (`CD = CDi + CDo`), riferiti a `Sref_m2` |
| 9–11 | `CMx`, `CMy`, `CMz` | – | coefficienti di momento attorno a `reference.moment_point_m` |
| 12 | `L_over_D` | – | CL/CD |
| 13–14 | `L_N`, `D_N` | N | portanza e resistenza: `C·q·Sref` |
| 15–17 | `Sref_m2`, `Lref_m`, `Re_ref` | m², m, – | riferimenti usati e Reynolds su Lref (quello scritto da FlightStream nella tabella dei carichi) |
| 18 | `q_Pa` | Pa | pressione dinamica ½ρV² (ρ = `fluid.density` del JSON, cioè quella del .fsm) |
| 19–20 | `xtr_up`, `xtr_lo` | – | x/c di transizione, dorso e ventre (solo `ccs_wing`) |
| 21–24 | `H_te_up`, `H_te_lo`, `H_max_up`, `H_max_lo` | – | fattore di forma al bordo d'uscita e massimo (solo `ccs_wing`) |
| 25–26 | `cf_min_up`, `cf_min_lo` | – | cf minimo in corda (solo `ccs_wing`) |
| 27–29 | `area_frac_cf_neg`, `H_max`, `sep_max` | – | frazione d'area con cf < 0, H massimo, marker di separazione massimo (tutte le modalità; compatibilità) |
| 30 | `sep_frac_up_le` | – | (con `wing_frame`) frazione dell'area del dorso separata a x/c < 0,15. **Vincolo di separazione consigliato** |
| 31 | `x_sep_up` | – | (con `wing_frame`) primo x/c separato sul dorso, minimo sulle strisce η 0,05–0,95; 1.0 = nessuna separazione. **Solo diagnostica** |
| 32–33 | `H_max_attached_up`, `x_H_max_attached_up` | – | (con `wing_frame`) H massimo sul dorso dove lo strato limite è attaccato (x/c ≤ 0,95) e il suo x/c. **Solo diagnostica** |
| 34 | `sep_frac_lo_te` | – | (con `wing_frame`) frazione dell'area del ventre separata a x/c > 0,8. **Solo diagnostica** |
| 35–39 | `aoa`, `velocity`, `altitude`, `sideslip`, `chord_scale` | come input | eco dei valori effettivamente usati (controllo; -999 se la variabile non esiste nella modalità) |

Senza `wing_frame` nel JSON le righe 30–34 valgono -999. Da non usare come vincoli o obiettivi:
`x_sep_up`, `H_max_attached_up`, `x_H_max_attached_up`, `sep_frac_lo_te` (diagnostica, vedi README).

## Vincolo obbligatorio: `status = 0`

- Definisci in HEEDS un vincolo `status = 0`, per esempio `status ≤ 0` con `status ≥ 0`
  *(come HEEDS esprime un vincolo di uguaglianza: da verificare)*.
- Con status 3, 4 o 5 i coefficienti sono scritti lo stesso, per diagnosi. Senza vincolo
  l'ottimizzatore li userebbe come buoni.
- Con status 2 (timeout) e 6 (licenza FlightStream non disponibile anche dopo
  `run.license_retries` nuovi tentativi, oppure FlightStream già attivo prima del lancio) non ci sono
  risultati e il design **non** è da
  considerare cattivo: dipende dalla macchina. Il vincolo `status = 0` lo esclude comunque; a fine
  studio conviene rilanciare i design con status 2 o 6 (motivo in `run_info.txt`). Se l'algoritmo di
  HEEDS penalizza i design falliti, molti status 6 possono falsare la ricerca: controlla la licenza
  prima di uno studio lungo.
- Se vuoi accettare anche i design in cui manca solo H/cf (CL/CD validi), il vincolo diventa
  `status = 0 oppure 4`. Decidilo in base alle risposte che usi.
- Il codice di uscita è 0 solo se lo status è in `heeds.success_statuses` del JSON (default `[0]`),
  altrimenti 1. La condizione di successo di HEEDS legge solo il codice di uscita o il contenuto di un
  file, non le risposte.
- **Success condition consigliata:** codice di uscita = 0 **AND** "File contains" `schema_version = 2`
  in `results.txt`. La seconda condizione garantisce che `results.txt` abbia lo schema su cui sono
  state taggate le risposte (se lo schema cambia, i design falliscono invece di leggere righe sbagliate).
  *(Come HEEDS combina due condizioni in AND: DA VERIFICARE nella GUI.)*
- Alternativa al codice di uscita: "File contains" `FS_DRIVER_RESULT status=0 success=1` su
  `run_info.txt` (ultima riga, sempre presente; `success` = 1 se lo status è in `success_statuses`, quindi
  con `[0, 4]` basta cercare `success=1`). Per un DOE in cui H/cf non servono: `"success_statuses": [0, 4]`.
- In ogni caso il motivo è in `run_info.txt` nella cartella del design.

## Obiettivi con geometria variabile

Con `chord_scale` (o un'altra variabile geometrica) `Sref` cambia da un design all'altro: i
coefficienti non sono confrontabili tra design. Usa come obiettivi `L_over_D` oppure `L_N` e `D_N`
(vedi README, "Nota per HEEDS").

## Checklist del primo Evaluation Only

- [ ] Il comando parte (variante A o B di "Comando") e nella cartella del design compaiono
      `fs_script.txt`, `results.txt`, `run_info.txt`.
- [ ] `results.txt` comincia con `schema_version = 2` e HEEDS legge gli stessi valori del file.
- [ ] Il design risulta riuscito con codice di uscita 0 e "File contains" `schema_version = 2`.
- [ ] **Stop di HEEDS:** avviare un design, premere Stop mentre FlightStream gira, poi aprire Gestione
      attività e cercare `FlightStream.exe`. *(Se HEEDS chiude anche i processi figli del comando:
      DA VERIFICARE.)* Se resta un `FlightStream.exe` orfano, **chiuderlo a mano** (Gestione attività →
      Termina attività) prima di riavviare lo studio: altrimenti il design successivo dà `status = 6`
      ("FlightStream già attivo", PID in `run_info.txt`).

## Ordine di lavoro consigliato

1. **Prove locali**: `--probes`, validazione e `heeds_mock.py` con 3–5 design (README).
   Lo script FlightStream generato segue il manuale 26.1 (riga vuota dopo ogni comando, OPEN con
   solo `LOAD_SOLVER_INITIALIZATION`, `INITIALIZE_SOLVER` esplicito, `CLEAR_SOLUTION`): con un'altra versione di FlightStream
   ripeti le prove di sintassi prima di collegare HEEDS.
2. **Evaluation Only** in HEEDS *(nome esatto del tipo di studio: da verificare)*: un solo design
   con i valori di validazione (aoa = 4, velocity = 20). Controlla che:
   - HEEDS crei la cartella e ci scriva `params.txt` con i valori giusti;
   - il comando parta in quella cartella (deve comparire `fs_script.txt`);
   - HEEDS legga da `results.txt` gli stessi numeri che vedi aprendo il file;
   - `status = 0` e i coefficienti coincidano con la validazione.
3. **Evaluation Only con un design sbagliato apposta** (es. una chiave errata in params.txt):
   HEEDS deve vedere `status = 1` e scartare il design.
4. **DOE** su pochi punti (es. `aoa` da 0 a 8 a passo 2), controllando tempi e status. Poi lo
   studio vero. Valutazioni in parallelo solo se le licenze FlightStream lo consentono, e sempre
   in cartelle separate.
