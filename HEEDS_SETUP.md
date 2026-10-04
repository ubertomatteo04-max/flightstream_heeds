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

```
"C:\Users\UtenteLocale\AppData\Local\Programs\Python\Python313\python.exe" "<CARTELLA>\fs_driver.py" --config "<CARTELLA>\case_semiala_fixed.json"
```

- `<CARTELLA>` = percorso assoluto di questa cartella (oggi
  `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline`). Il JSON va scelto in base al caso.
- Il percorso completo di `python.exe` evita sorprese se HEEDS non vede lo stesso PATH del
  terminale (sul tuo PC: quello indicato sopra; su un altro PC: `python -c "import sys; print(sys.executable)"`).
- FlightStream: conviene impostare la variabile d'ambiente `FLIGHTSTREAM_EXE`, oppure riempire
  `flightstream_exe` nel JSON, così non dipende da cosa vede HEEDS. Su questo PC la ricerca
  automatica trova `C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe`.
- Meglio cartelle di lavoro **senza spazi** nel percorso.
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

| Risposta | Unità | Significato |
|---|---|---|
| `status` | – | 0 ok, 1 errore, 2 timeout, 3 non convergente, 4 H/cf non estraibili, 5 non fisico, 6 licenza non disponibile |
| `converged`, `iterations` | – | 1 se convergente; iterazioni eseguite |
| `CL`, `CD`, `CDi`, `CDo` | – | coefficienti di portanza e resistenza (`CD = CDi + CDo`), riferiti a `Sref_m2` |
| `CMx`, `CMy`, `CMz` | – | coefficienti di momento attorno a `reference.moment_point_m` |
| `L_over_D` | – | CL/CD |
| `L_N`, `D_N` | N | portanza e resistenza: `C·q·Sref` |
| `q_Pa` | Pa | pressione dinamica ½ρV² (in `fixed` ρ = `fluid.density` del JSON, cioè quella del .fsm) |
| `xtr_up`, `xtr_lo` | – | x/c di transizione, dorso e ventre (solo `ccs_wing`) |
| `H_te_up`, `H_te_lo`, `H_max_up`, `H_max_lo` | – | fattore di forma al bordo d'uscita e massimo (solo `ccs_wing`) |
| `cf_min_up`, `cf_min_lo` | – | cf minimo in corda (solo `ccs_wing`) |
| `area_frac_cf_neg`, `H_max`, `sep_max` | – | frazione d'area con cf < 0, H massimo, marker di separazione massimo (tutte le modalità) |
| `aoa`, `velocity`, `altitude`, `sideslip`, `chord_scale` | come input | valori effettivamente usati (controllo; -999 se la variabile non esiste nella modalità) |
| `Sref_m2`, `Lref_m`, `Re_ref` | m², m, – | riferimenti usati e Reynolds su Lref (quello scritto da FlightStream nella tabella dei carichi) |

## Vincolo obbligatorio: `status = 0`

- Definisci in HEEDS un vincolo `status = 0`, per esempio `status ≤ 0` con `status ≥ 0`
  *(come HEEDS esprime un vincolo di uguaglianza: da verificare)*.
- Con status 3, 4 o 5 i coefficienti sono scritti lo stesso, per diagnosi. Senza vincolo
  l'ottimizzatore li userebbe come buoni.
- Con status 2 (timeout) e 6 (licenza FlightStream non disponibile anche dopo
  `run.license_retries` nuovi tentativi) non ci sono risultati e il design **non** è da
  considerare cattivo: dipende dalla macchina. Il vincolo `status = 0` lo esclude comunque; a fine
  studio conviene rilanciare i design con status 2 o 6 (motivo in `run_info.txt`). Se l'algoritmo di
  HEEDS penalizza i design falliti, molti status 6 possono falsare la ricerca: controlla la licenza
  prima di uno studio lungo.
- Se vuoi accettare anche i design in cui manca solo H/cf (CL/CD validi), il vincolo diventa
  `status = 0 oppure 4`. Decidilo in base alle risposte che usi.
- Il codice di uscita è 1 per ogni status diverso da 0. Se HEEDS considera "fallito" un design
  con codice di uscita ≠ 0 *(da verificare)*, quei design saranno comunque esclusi.
- In ogni caso il motivo è in `run_info.txt` nella cartella del design.

## Obiettivi con geometria variabile

Con `chord_scale` (o un'altra variabile geometrica) `Sref` cambia da un design all'altro: i
coefficienti non sono confrontabili tra design. Usa come obiettivi `L_over_D` oppure `L_N` e `D_N`
(vedi README, "Nota per HEEDS").

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
