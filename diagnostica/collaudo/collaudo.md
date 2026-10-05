# Collaudo end-to-end v2.6.0 (run_fs.bat via heeds_mock.py), generato da collaudo.py

Righe 2–39 di results.txt confrontate per chiave con i DOE precedenti; la riga 1 (`schema_version`) cambia per costruzione.

## fixed contro Study_2 (HEEDS, v2.4.1)

| aoa | status | CL | CD | CMy | L_N [N] | righe 1 (nuovo / prima) | righe 2–39 diverse | diff. max assoluta (chiave) | diff. max relativa | chiavi assenti nel riferimento |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0.1905 | 0.0129 | -0.098 | 85.041 | 4 / 2 | 0 | 0 (-) | 0 % | – |
| 2 | 0 | 0.3838 | 0.0155 | -0.1484 | 171.332 | 4 / 2 | 0 | 0 (-) | 0 % | – |
| 4 | 0 | 0.5767 | 0.0202 | -0.1993 | 257.444 | 4 / 2 | 0 | 0 (-) | 0 % | – |
| 6 | 0 | 0.769 | 0.0279 | -0.2502 | 343.289 | 4 / 2 | 0 | 0 (-) | 0 % | – |
| 8 | 0 | 0.9605 | 0.0383 | -0.3009 | 428.776 | 4 / 2 | 0 | 0 (-) | 0 % | – |
| 10 | 0 | 1.151 | 0.0502 | -0.3515 | 513.817 | 4 / 2 | 0 | 0 (-) | 0 % | – |
| 12 | 0 | 1.3403 | 0.0642 | -0.4016 | 598.323 | 4 / 2 | 0 | 0 (-) | 0 % | – |

## ccs_wing contro mock_runs_ccs (v2.2.x)

| chord_scale | status | CL | CD | CMy | L_N [N] | righe 1 (nuovo / prima) | righe 2–39 diverse | diff. max assoluta (chiave) | diff. max relativa | chiavi assenti nel riferimento |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.9 | 0 | 0.587 | 0.02 | -0.2029 | 235.838 | 4 / assente | 0 | 0 (-) | 0 % | sep_frac_up_le, x_sep_up, H_max_attached_up, x_H_max_attached_up, sep_frac_lo_te |
| 1 | 0 | 0.5767 | 0.0202 | -0.1993 | 257.445 | 4 / assente | 0 | 0 (-) | 0 % | sep_frac_up_le, x_sep_up, H_max_attached_up, x_H_max_attached_up, sep_frac_lo_te |
| 1.1 | 0 | 0.5678 | 0.0203 | -0.1962 | 278.819 | 4 / assente | 0 | 0 (-) | 0 % | sep_frac_up_le, x_sep_up, H_max_attached_up, x_H_max_attached_up, sep_frac_lo_te |

**ESITO: righe 2–39 identiche in tutti i design**
