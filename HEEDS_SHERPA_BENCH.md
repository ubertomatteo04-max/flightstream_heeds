# Benchmark SHERPA sulla rastremazione – scheda per la GUI di HEEDS

**File da selezionare in HEEDS (Files tab):**

| ruolo | percorso completo |
|---|---|
| input (template, tag della variabile) | `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\heeds_inputs\planform_S\params.txt` |
| output (template, tag delle risposte) | `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\heeds_inputs\planform_S\results.txt` |
| JSON (nel comando) | `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\configs\esplorativi\case_planform_taper_S.json` |

Dati letti dai file reali il 2026-10-06 (`heeds_inputs\planform_S\`, `configs\esplorativi\case_planform_taper_S.json`,
dry-run del driver senza FlightStream). Driver v2.7.0, schema 6. Procedura generale: `HEEDS_SETUP.md`.

`heeds_inputs\planform_S\` è la cartella del benchmark (`size_by: "S_half"`). **Non usare** `heeds_inputs\planform\`:
quella è la baseline con `size_by: "c_root"` (riga 7 = `c_root`) e con questo JSON dà status 1 ("chiavi non ammesse:
['c_root']"). `results.txt` di planform_S = risultato reale del design taper 1,00 del DOE 7C (stesso JSON, 2026-10-06).

## 1. Cartella, analisi, comando

- **Progetto HEEDS:** nuovo progetto in `C:\Users\UtenteLocale\Desktop\heeds\semiala_planform\` (accanto a
  `semiala_fixed\`; percorso senza spazi). HEEDS deve girare in locale con lo stesso utente Windows del login Altair One.
- **Analisi:** una sola (Analysis_1), tipo comando (Execution command), **Run in = Analysis folder**.
- **Comando** (con le virgolette):

```
"C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\run_fs.bat" --config "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\configs\esplorativi\case_planform_taper_S.json"
```

- JSON: modalità `ccs_planform`, `size_by: "S_half"`, trim attivo (`trim.enabled = true`, W = 147,15 N, V_cruise 20 m/s,
  α1 = aoa del params, α2 = α1 + 2°), `heeds.success_statuses = [0]`, `run.timeout_s = 240` per run, clmax **segnaposto**
  (`profiles/clmax_vs_Re.csv`, 1,2 costante; il clmax di XFOIL non è attivo, come deciso).
- Nota: `configs\esplorativi\README.md` dice "non usare in HEEDS"; questo JSON è l'eccezione voluta per il benchmark.
- **File:** input `heeds_inputs\planform_S\params.txt` (§2), output `heeds_inputs\planform_S\results.txt` (§3); percorsi
  completi nella tabella in testa.

## 2. params.txt di base: `heeds_inputs\planform_S\params.txt` (righe numerate, come le vede HEEDS)

Contenuto reale del file (righe 1–4 commenti ereditati dalla baseline planform; riga 7 = `S_half`):

| riga | contenuto | ruolo nel benchmark |
|---|---|---|
| 1 | `# params_baseline.txt - modalita ccs_planform (case_semiala_planform.json): file per il tagging delle variabili in HEEDS.` | commento |
| 2 | `# Variabili: aoa [deg], velocity [m/s], c_root [m] (oppure S_half [m2] con geometry.size_by = "S_half"), taper [-],` | commento |
| 3 | `# twist_tip_deg [deg, positivo a cabrare], b_half [m]. sideslip = 0 (Mirror). Valori = baseline (rettangolare, non svergolata).` | commento |
| 4 | `# Con trim.enabled (case_semiala_planform.json) aoa e' solo alfa1, il primo tentativo; alfa* esce in alpha_trim.` | commento |
| 5 | `aoa = 0.0` | fisso (α1 del trim) |
| 6 | `velocity = 20.0` | fisso (= V_cruise, obbligatorio con il trim) |
| 7 | `S_half = 0.911041` | fisso (area della semiala, m²) |
| **8** | **`taper = 1.0`** | **VARIABILE: 0,25–1,00, baseline 1,00** (tag: riga 8, colonna 2) |
| 9 | `twist_tip_deg = 0.0` | fisso |
| 10 | `b_half = 2.64` | fisso (m) |

Fissi anche nel JSON: `size_by: "S_half"`, trim attivo. Le righe fisse si possono lasciare non taggate (il driver le legge
dal file); se si taggano, vanno come costanti con questi valori.

## 3. results.txt: `heeds_inputs\planform_S\results.txt` (schema 6, 64 righe) – risposte del benchmark

| risposta | riga | chiave | baseline (taper 1) | uso |
|---|---|---|---|---|
| status | **2** | `status` | 0 | vincolo = 0 (oltre al codice di uscita) |
| Di_N | **56** | `Di_N` | 1.13727 | **obiettivo: minimo** |
| D_N | **14** | `D_N` | 6.51759 | solo monitor (quantizzato: gradini di 0,045 N, vedi §6) |
| e_span | **64** | `e_span` | 0.887519 | monitor |
| alpha_trim | **55** | `alpha_trim` | 1.43952 | monitor (α* del trim) |
| Re_tip | **62** | `Re_tip` | 474985 | monitor |
| CLmax_wing | **59** | `CLmax_wing` | 1.08579 | monitor, clmax **segnaposto** |
| eta_stall | **61** | `eta_stall` | 0.0588636 | monitor, clmax **segnaposto** |

Valori di baseline da `heeds_inputs\planform_S\results.txt` (run reale, taper 1,00, size_by S_half, status 0).

<details><summary>Tabella completa riga → chiave (64 righe)</summary>

| riga | chiave | riga | chiave | riga | chiave | riga | chiave |
|---|---|---|---|---|---|---|---|
| 1 | schema_version | 17 | Re_ref | 33 | x_H_max_attached_up | 49 | cl_sec_eta05 |
| 2 | status | 18 | q_Pa | 34 | sep_frac_lo_te | 50 | c_root |
| 3 | converged | 19 | xtr_up | 35 | aoa | 51 | taper |
| 4 | iterations | 20 | xtr_lo | 36 | velocity | 52 | twist_tip_deg |
| 5 | CL | 21 | H_te_up | 37 | altitude | 53 | b_half |
| 6 | CD | 22 | H_te_lo | 38 | sideslip | 54 | S_half |
| 7 | CDi | 23 | H_max_up | 39 | chord_scale | 55 | alpha_trim |
| 8 | CDo | 24 | H_max_lo | 40 | viscous_coupling | 56 | Di_N |
| 9 | CMx | 25 | cf_min_up | 41 | separation_model | 57 | D0_N |
| 10 | CMy | 26 | cf_min_lo | 42 | iterations_inviscid | 58 | M_root_Nm |
| 11 | CMz | 27 | area_frac_cf_neg | 43 | iterations_viscous | 59 | CLmax_wing |
| 12 | L_over_D | 28 | H_max | 44 | converged_viscous | 60 | CL_req |
| 13 | L_N | 29 | sep_max | 45 | sep_marker_frac_up | 61 | eta_stall |
| 14 | D_N | 30 | sep_frac_up_le | 46 | cl_sec_max | 62 | Re_tip |
| 15 | Sref_m2 | 31 | x_sep_up | 47 | eta_cl_sec_max | 63 | AR |
| 16 | Lref_m | 32 | H_max_attached_up | 48 | cl_sec_root | 64 | e_span |

</details>

Tagging: delimitatore `=`, valore in colonna 2 (come nello Study_2). Riga 35 (`aoa`) = α1, non α*.

## 4. Numeri in params.txt

- Separatore decimale: **punto** (Advanced Options → Default decimal delimiter = **Period**). La virgola è anche un
  delimitatore del parser di HEEDS: `0,25` darebbe un errore (status 1).
- Formato accettato dal driver: qualsiasi stampa numerica di HEEDS (`0.25`, `0.250000`, `2.50000E-01`, `1`); HEEDS
  nello Study_2 ha scritto 6 cifre significative (`aoa = 0.00000`, `aoa = 10.0000`). Non accettati: virgola, `D` come
  esponente, testo.

## 5. Timeout e Success condition

- Tempo misurato (7C, stessi design): **49–57 s per design** in tutto (3 run di FlightStream da ≈ 17 s, più il
  driver); il primo design dopo un avvio può arrivare a ≈ 80 s.
- Timeout primario: il driver (`run.timeout_s = 240` per ogni run). Caso peggiore di un design: 3 run × (3 tentativi ×
  240 s + 2 attese licenza × 60 s) = **2520 s**.
- **Max execution time in HEEDS (rete di sicurezza): 3000 s.** Con 1200 s (Study_2) un design con problemi di licenza
  potrebbe essere interrotto prima che il driver scriva status 2/6.
- **Success condition: la stessa dello Study_2**: Execution → Analysis Execution Options → Conditions → Success →
  "Compare analysis successful return value" = **0**.

## 6. Risultato atteso (dalla 7C, stesso JSON, griglia 0,25–1,00 passo 0,05)

- Minimo di `Di_N` per **taper tra circa 0,33 e 0,43** (0,35 e 0,40 coincidono: 1,0578 N; parabola 0,382).
- **Di_N ≈ 1,058 N**, **e_span ≈ 0,954**; α* ≈ 1,354°; taper 1 → Di_N 1,1373 N, e_span 0,888.
- Con il segnaposto: CLmax_wing ≈ 1,14 e eta_stall ≈ 0,57–0,66 vicino all'ottimo.
- Usare **Di_N**, non D_N, come obiettivo: D_N è quantizzato a 4 decimali di CD (gradini di 0,045 N, 0,7 %): SHERPA
  vedrebbe un altopiano a gradini. Rumore di Di_N lungo il taper < 0,05 %.

## 7. Preflight (prima di lanciare)

- [ ] Nessun `FlightStream.exe` attivo (Gestione attività; GUI di FlightStream chiusa): altrimenti status 6.
- [ ] Login Altair One valido con lo stesso utente Windows di HEEDS (aprire FlightStream una volta e chiuderlo).
- [ ] `preflight.bat` → `PREFLIGHT OK` (driver, interpreti, i tre JSON di produzione e i loro heeds_inputs).
- [ ] Preflight sul JSON del benchmark → `PREFLIGHT OK` (usa `heeds_inputs\planform_S\`; verificato il 2026-10-06):
      `python preflight.py --config configs\esplorativi\case_planform_taper_S.json`
- [ ] (facoltativo) Dry-run del comando del §1 con `heeds_inputs\planform_S\params.txt` in una cartella di prova
      (aggiungere `--dry-run`): atteso `FS_DRIVER_RESULT status=1 success=0` con "trim: dry-run" in `run_info.txt`
      (status 1 è normale in dry-run; verificato il 2026-10-06: Sref 1,82208, c_root derivato 0,345091).
- [ ] Cartella del progetto HEEDS nuova o pulita (nessun `HEEDS_0\Design*` di prove precedenti); nessuna cartella aperta
      in Esplora risorse dentro le cartelle dei design (Windows può bloccare la pulizia).
- [ ] Max execution time = 3000 s, decimal delimiter = Period, Success condition = return value 0.
