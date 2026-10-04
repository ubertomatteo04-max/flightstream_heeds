"""Processi FlightStream: controllo prima del lancio (status 6), kill_stale_flightstream e chiusura
dell'albero al timeout (status 2), senza FlightStream vero.

    python -m unittest discover -s tests -v

Solo Windows. Il "FlightStream gia' attivo" e' una copia di ping.exe rinominata FlightStream.exe
(stesso nome che il driver cerca); il "FlightStream che non finisce" e' un .bat che avvia quella
copia e la aspetta. Ogni test chiude i processi che ha creato.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fs_driver  # noqa: E402

PING = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "PING.EXE")


@unittest.skipUnless(os.name == "nt", "controllo dei processi solo su Windows")
class TestFlightStreamProcesses(unittest.TestCase):
    def setUp(self):
        if fs_driver.running_flightstream(["FlightStream.exe"]):
            self.skipTest("c'e' gia' un FlightStream.exe attivo: chiuderlo prima dei test")
        self.tmp = tempfile.mkdtemp(prefix="fs proc ")
        self.fake = os.path.join(self.tmp, "FlightStream.exe")
        shutil.copy(PING, self.fake)
        self.started = []

    def tearDown(self):
        for p in self.started:
            if p.poll() is None:
                p.kill()
                p.wait()
        for pid, _ in fs_driver.running_flightstream(["FlightStream.exe"]):
            fs_driver._taskkill(pid)                         # solo i finti: setUp ha verificato che non ce n'erano
        time.sleep(1)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def start_fake(self, seconds=120):
        p = subprocess.Popen([self.fake, "-n", str(seconds), "127.0.0.1"], stdout=subprocess.DEVNULL)
        self.started.append(p)
        time.sleep(0.5)
        return p

    def driver(self, run_changes, exe):
        """Run del driver (fixed) con --exe; restituisce (codice, results, run_info, secondi)."""
        with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
        cfg["run"].update(run_changes)
        d = tempfile.mkdtemp(dir=self.tmp, prefix="design ")
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write("aoa = 4\nvelocity = 20\n")
        t0 = time.time()
        p = subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                            "--workdir", d, "--exe", exe], capture_output=True, text=True)
        dt = time.time() - t0
        with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
            res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            info = f.read()
        return p.returncode, res, info, dt

    def quick_exe(self):
        """Finto eseguibile che termina subito (nessun risultato -> status 1)."""
        bat = os.path.join(self.tmp, "esce_subito.bat")
        with open(bat, "w", newline="\r\n") as f:
            f.write("@echo off\necho Checking out Altair units...Success!\nexit /b 0\n")
        return bat

    def test_busy_gives_status6_and_does_not_kill(self):
        fake = self.start_fake()
        rc, res, info, dt = self.driver({}, self.quick_exe())
        self.assertEqual((res["status"], rc), ("6", 1))
        self.assertIn(f"PID {fake.pid}", info)
        self.assertIsNone(fake.poll(), "il processo estraneo non deve essere chiuso con kill_stale = false")
        self.assertGreaterEqual(dt, fs_driver.STALE_WAIT_S)          # ha aspettato prima di rinunciare

    def test_kill_stale_closes_and_runs(self):
        fake = self.start_fake()
        rc, res, info, dt = self.driver({"kill_stale_flightstream": True}, self.quick_exe())
        self.assertIsNotNone(fake.poll(), "con kill_stale = true il processo va chiuso")
        self.assertIn("kill_stale_flightstream: chiusi", info)
        self.assertEqual(res["status"], "1")                        # lanciato: il finto exe non da' risultati

    def test_timeout_kills_whole_tree(self):
        bat = os.path.join(self.tmp, "non_finisce.bat")
        with open(bat, "w", newline="\r\n") as f:
            f.write(f'@echo off\necho Checking out Altair units...Success!\n"{self.fake}" -n 120 127.0.0.1 >nul\n')
        rc, res, info, dt = self.driver({"timeout_s": 4}, bat)
        self.assertEqual((res["status"], rc), ("2", 1))
        self.assertIn("FlightStream.exe (PID", info)                 # il figlio era stato visto nell'albero
        self.assertNotIn("ancora attivi", info)
        self.assertEqual(fs_driver.running_flightstream(["FlightStream.exe"]), [], "processi orfani dopo il timeout")
        self.assertLess(dt, 20)


if __name__ == "__main__":
    unittest.main()
