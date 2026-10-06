# Studio SHERPA completo della semiala – scheda per la GUI di HEEDS

**File da selezionare in HEEDS (Files tab):**

| ruolo | percorso completo |
|---|---|
| input (template, tag delle variabili) | `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\heeds_inputs\planform_full\params.txt` |
| output (template, tag delle risposte) | `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\heeds_inputs\planform_full\results.txt` |
| JSON (nel comando) | `C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\case_semiala_planform_full.json` |

Dati letti dai file reali il 2026-10-06 (driver v2.8.2, schema 8). `results.txt` di planform_full = run reale della
baseline con questo JSON (status 0). Procedura generale della GUI: `HEEDS_SETUP.md`; benchmark già fatto:
`HEEDS_SHERPA_BENCH.md` (che resta sul clmax segnaposto).

## 1. Caso, mesh, comando

- **Modello:** `ccs_planform` (size_by `c_root`), configurazione D (disaccoppiata, senza modello di separazione), trim
  su W = 147,15 N a V_cruise = 20 m/s (3 run di FlightStream per design: α1 = 0°, α1 + 2°, α*), V_min = 12 m/s,
  **clmax di XFOIL** (`xfoil/clmax_vs_Re.csv`, Ncrit 9, Re = V_min·c/ν).
- **Mesh U120 × V64** (Mesh_U 120;3;1.1;2, Mesh_V 64;1;1.0;1), scritta nel JSON. Motivazione (7E): i vincoli
  (M_root_Nm, CLmax_wing) sono convergenti entro lo 0,5 %; la differenza di Di_N fra design è stabile entro 0,41 punti
  percentuali fra le mesh; D_N ha un'incertezza di mesh di circa il 3 %, concentrata su D0_N.
- **Comando** (Execution command, Run in = Analysis folder):

```
"C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\run_fs.bat" --config "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\case_semiala_planform_full.json"
```

## 2. Variabili (params.txt, righe numerate come le vede HEEDS)

| riga | contenuto | ruolo | intervallo | baseline |
|---|---|---|---|---|
| 1–4 | commenti | – | – | – |
| 5 | `aoa = 0.0` | fisso (α1 del trim) | – | 0 |
| 6 | `velocity = 20.0` | fisso (= V_cruise, obbligatorio) | – | 20 |
| **7** | `c_root = 0.345091293` | **variabile** continua | **0,276 – 0,552 m** | 0,345091 |
| **8** | `taper = 1.0` | **variabile** continua | **0,4 – 1,0** | 1,0 |
| **9** | `twist_tip_deg = 0.0` | **variabile** continua | **−5 – +1°** (positivo a cabrare) | 0 |
| **10** | `b_half = 2.64` | **variabile** continua | **2,112 – 3,04 m** | 2,64 |

Tag: riga N, colonna 2, delimitatore `=`. Separatore decimale **punto** (Default decimal delimiter = Period).
`b_half` non può superare 3,04 (`mission.b_half_max`): oltre, status 1.

## 3. Obiettivo, vincoli, risposte di controllo

| tipo | risposta | riga | condizione |
|---|---|---|---|
| **obiettivo** | `D_N` | 14 | **minimo** (D_N = Di_N + D0_N, N) |
| vincolo | `stall_margin` | 65 | **≥ 0** (CLmax_wing / CL_req − 1: ala ammissibile allo stallo a 12 m/s) |
| vincolo | `eta_stall` | 61 | **≤ 0,6** (stallo non verso l'estremità) |
| vincolo | `Re_tip` | 62 | **≥ 2·10⁵** (c_tip ≥ 0,1453 m: con taper 0,4 serve c_root ≥ 0,363 m) |
| successo | `status` | 2 | = 0 tramite la Success condition (codice di uscita 0) |
| controllo | `Di_N` | 56 | – |
| controllo | `D0_N` | 57 | – |
| controllo | `alpha_trim` | 55 | – |
| controllo | `e_span` | 64 | – |
| controllo | `Sref_m2` (S_ref) | 15 | – |
| controllo | `M_root_Nm` | 58 | – |
| controllo | `CLmax_wing`, `CL_req` | 59, 60 | – |

**Differenze di D_N sotto il 3 % fra design non sono significative** (incertezza di mesh, 7E).

## 4. Valori attesi della baseline (Evaluate baseline)

Righe taggate, dal `results.txt` reale di planform_full (c_root 0,345091, taper 1, twist 0, b_half 2,64):

| riga | chiave | valore atteso |
|---|---|---|
| 2 | status | 0 |
| 14 | D_N | 6.55887 |
| 15 | Sref_m2 | 1.82208 |
| 55 | alpha_trim | 1.43952 |
| 56 | Di_N | 1.13727 |
| 57 | D0_N | 5.4216 |
| 58 | M_root_Nm | 89.6064 |
| 59 | CLmax_wing | 1.21927 |
| 60 | CL_req | 0.915638 |
| 61 | eta_stall | 0.0588636 |
| 62 | Re_tip | 474985 |
| 64 | e_span | 0.887519 |
| 65 | stall_margin | 0.331607 |

## 5. Budget, tempi, opzioni dello studio

- **150 valutazioni** SHERPA.
- Tempo per design: 58–76 s misurati nella 7F (driver + 3 run di FlightStream) + circa 14 s di HEEDS (benchmark:
  68 s in HEEDS contro 54 s col driver da solo) → **circa 80 s**. **150 valutazioni ≈ 3,3 h.**
- **Max execution time = 3000 s: basta.** È solo la rete di sicurezza: il caso peggiore del driver (3 run × (3
  tentativi × 240 s + 2 attese licenza × 60 s)) è 2520 s < 3000 s; il tempo normale è circa 80 s.
- Success condition: "Compare analysis successful return value" = **0** (come nello Study_2 e nel benchmark).
- **"If an error occurs": non fermare lo studio.** Nel benchmark era `errorMode: STOP`. Qui alcuni design danno
  errore per ragioni fisiche, non della macchina: ali piccole con |α* − α1| > 6° (status 3, sono anche non ammissibili
  allo stallo). Impostare di continuare sugli errori e salvare i design in errore (`dontStopOnDesignErrors`,
  `saveErrorDesigns`, come nello Study_2).
- Design in errore per cause esterne (status 2 o 6): rivalutarli con *Share designs* (HEEDS_SETUP passo 10).

## 6. Criteri di accettazione del risultato SHERPA

- **Riferimento ammissibile noto:** rettangolare c_root 0,26 m, b_half 2,64 m, twist 0 → D_N **5,242 N**,
  stall_margin +1,3 % (7F). **Il migliore di SHERPA deve stare sotto 5,24 N**, altrimenti l'ottimizzazione non ha
  funzionato (o i vincoli sono sbagliati).
- **Stima dell'ottimo:** D_N ≈ **4,9 N**, b_half ≈ **3,04** (limite superiore), stall_margin ≈ **0** (vincolo
  attivo), eta_stall ≤ 0,6.
- **Se c_root finisce sul limite inferiore (0,276 m): segnalarlo**, il limite va allargato.
- Un guadagno rispetto al riferimento sotto il 3 % non è significativo (incertezza di mesh): va confermato con la 7H.

## 7. Dopo SHERPA – verifica (7H) – **da non eseguire ora**

Rilanciare **baseline** e **design migliore** con due mesh: U120 × V64 (quella dello studio) e **U180 × V64**
(growth rate in corda 1,0656, come nella 7E). Riportare per ciascuno ΔD_N, ΔDi_N, ΔD0_N (migliore − baseline) e
stall_margin. **Il guadagno è credibile solo se ΔD_N sulla mesh fine ha lo stesso segno ed è > 3 %.**

## 8. Prima di lanciare

- [ ] Nessun `FlightStream.exe` attivo; login Altair One valido con lo stesso utente Windows di HEEDS.
- [ ] `preflight.bat` → `PREFLIGHT OK` (controlla anche `case_semiala_planform_full.json` con `heeds_inputs\planform_full\`).
- [ ] Progetto/studio HEEDS nuovo o cartella pulita; nessuna cartella dei design aperta in Esplora risorse.
- [ ] Variabili (§2) continue con i limiti indicati; obiettivo e vincoli come nel §3; Max execution time 3000 s;
      decimal delimiter Period; non fermare lo studio sugli errori.
- [ ] Evaluate baseline: i valori del §4.

## 9. Tabella completa di results.txt (schema 8, 65 righe; valori della baseline di planform_full)

| riga | chiave | baseline | riga | chiave | baseline |
|---|---|---|---|---|---|
| 1 | schema_version | 8 | 34 | sep_frac_lo_te | 0 |
| 2 | status | 0 | 35 | aoa | 0 |
| 3 | converged | 1 | 36 | velocity | 20 |
| 4 | iterations | 91 | 37 | altitude | -999 |
| 5 | CL | 0.3297 | 38 | sideslip | 0 |
| 6 | CD | 0.0146 | 39 | chord_scale | -999 |
| 7 | CDi | 0.0025 | 40 | viscous_coupling | 0 |
| 8 | CDo | 0.0121 | 41 | separation_model | 0 |
| 9 | CMx | 0 | 42 | iterations_inviscid | 91 |
| 10 | CMy | -0.1343 | 43 | iterations_viscous | 0 |
| 11 | CMz | 0 | 44 | converged_viscous | -999 |
| 12 | L_over_D | 22.5822 | 45 | sep_marker_frac_up | 0 |
| 13 | L_N | 147.181 | 46 | cl_sec_max | 0.361868 |
| 14 | D_N | 6.55887 | 47 | eta_cl_sec_max | 0.0588636 |
| 15 | Sref_m2 | 1.82208 | 48 | cl_sec_root | 0.361768 |
| 16 | Lref_m | 0.345091 | 49 | cl_sec_eta05 | 0.352178 |
| 17 | Re_ref | 474985 | 50 | c_root | 0.345091 |
| 18 | q_Pa | 245 | 51 | taper | 1 |
| 19 | xtr_up | 0.531822 | 52 | twist_tip_deg | 0 |
| 20 | xtr_lo | 0.685353 | 53 | b_half | 2.64 |
| 21 | H_te_up | 1.64487 | 54 | S_half | 0.911041 |
| 22 | H_te_lo | 1.4917 | 55 | alpha_trim | 1.43952 |
| 23 | H_max_up | 3.16694 | 56 | Di_N | 1.13727 |
| 24 | H_max_lo | 2.9686 | 57 | D0_N | 5.4216 |
| 25 | cf_min_up | 0.00043866 | 58 | M_root_Nm | 89.6064 |
| 26 | cf_min_lo | 0.000553971 | 59 | CLmax_wing | 1.21927 |
| 27 | area_frac_cf_neg | 0 | 60 | CL_req | 0.915638 |
| 28 | H_max | 3.20021 | 61 | eta_stall | 0.0588636 |
| 29 | sep_max | 0 | 62 | Re_tip | 474985 |
| 30 | sep_frac_up_le | 0 | 63 | AR | 15.3003 |
| 31 | x_sep_up | 1 | 64 | e_span | 0.887519 |
| 32 | H_max_attached_up | 3.20021 | 65 | stall_margin | 0.331607 |
| 33 | x_H_max_attached_up | 0.443023 | | | |
