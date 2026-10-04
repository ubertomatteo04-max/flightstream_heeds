@echo off
cd /d "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\probes"
echo probe_1_solo_file
"C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe" -hidden -script "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\probes\probe_1_solo_file.txt"
if exist FlightStreamLog.txt move /y FlightStreamLog.txt probe_1_solo_file_FlightStreamLog.txt >nul
echo probe_2_entrambi
"C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe" -hidden -script "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\probes\probe_2_entrambi.txt"
if exist FlightStreamLog.txt move /y FlightStreamLog.txt probe_2_entrambi_FlightStreamLog.txt >nul
echo probe_3_solo_loadinit
"C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe" -hidden -script "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\probes\probe_3_solo_loadinit.txt"
if exist FlightStreamLog.txt move /y FlightStreamLog.txt probe_3_solo_loadinit_FlightStreamLog.txt >nul
echo probe_4_csys
"C:\Program Files\Altair\2026.1\flightstream\FlightStream.exe" -hidden -script "C:\Users\UtenteLocale\Desktop\fs_heeds_pipeline\fs_heeds_pipeline\probes\probe_4_csys.txt"
if exist FlightStreamLog.txt move /y FlightStreamLog.txt probe_4_csys_FlightStreamLog.txt >nul
