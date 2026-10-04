"""run_fs.bat e heeds_mock.py --root: codice di uscita propagato e output nella cartella del design.

    python -m unittest discover -s tests -v

Solo Windows. Non lancia FlightStream:
  - uscita 0: --extract-only su carichi/log veri (tests/fixtures) + VTK illeggibile = status 4,
    con heeds.success_statuses = [0, 4] (quindi successo);
  - uscita 1: chiave sconosciuta in params.txt (status 1) oppure --dry-run (status 1).
Cartelle di lavoro e JSON in percorsi con spazi, come puo' capitare con HEEDS.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
BAT = os.path.join(ROOT, "run_fs.bat")
EXTRACT = ["--extract-only", "--loads", os.path.join(FIX, "loads_a04.txt"),
           "--log", os.path.join(FIX, "log_a04.txt"), "--vtk", os.path.join(FIX, "vtk_rotto.txt")]


def q(s):
    return f'"{s}"'


@unittest.skipUnless(os.name == "nt", "run_fs.bat solo su Windows")
class TestRunFsBat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fs heeds ")
        cfgdir = os.path.join(self.tmp, "json con spazi")
        os.makedirs(cfgdir)
        with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
        cfg["heeds"] = {"success_statuses": [0, 4]}
        self.config = os.path.join(cfgdir, "case prova.json")
        with open(self.config, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def design(self, name, params):
        d = os.path.join(self.tmp, "Design 1", name)
        os.makedirs(d)
        with open(os.path.join(d, "params.txt"), "w", encoding="utf-8") as f:
            f.write(params)
        return d

    def check_outputs(self, d, status):
        with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
            res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
        self.assertEqual(res["status"], status)
        self.assertTrue(os.path.isfile(os.path.join(d, "run_info.txt")))

    def cases(self):
        """(nome, params, argomenti in piu', codice atteso, status atteso)."""
        return [("ok_extract", "aoa = 4\nvelocity = 20\n", EXTRACT, 0, "4"),
                ("ko_chiave", "aoa = 4\nvelocity = 20\nchiave_sbagliata = 1\n", [], 1, "1"),
                ("ko_dryrun", "aoa = 4\nvelocity = 20\n", ["--dry-run"], 1, "1")]

    def test_direct_process(self):
        """Il .bat lanciato direttamente come processo (cio' che fa HEEDS con l'Execution command)."""
        for name, params, extra, rc, st in self.cases():
            d = self.design("diretto_" + name, params)
            p = subprocess.run([BAT, "--config", self.config] + extra, cwd=d, capture_output=True, text=True)
            self.assertEqual(p.returncode, rc, name)
            self.check_outputs(d, st)

    def test_cmd_c(self):
        """Variante per HEEDS: cmd /c ""...\\run_fs.bat" --config "...json"" (virgolette esterne)."""
        for name, params, extra, rc, st in self.cases():
            d = self.design("cmdc_" + name, params)
            inner = " ".join([q(BAT), "--config", q(self.config)] + [q(x) for x in extra])
            p = subprocess.run(f'cmd /d /c "{inner}"', cwd=d, capture_output=True, text=True)
            self.assertEqual(p.returncode, rc, name)
            self.check_outputs(d, st)

    def test_cmd_call(self):
        """Da un altro script cmd con call: l'errorlevel arriva al chiamante."""
        for name, params, extra, rc, st in self.cases():
            d = self.design("call_" + name, params)
            script = os.path.join(d, "prova.cmd")
            with open(script, "w", encoding="utf-8", newline="\r\n") as f:
                f.write("@echo off\n")
                f.write(f"call {q(BAT)} --config {q(self.config)} {' '.join(q(x) for x in extra)}\n")
                f.write("echo EXIT=%ERRORLEVEL%\n")
                f.write("exit /b %ERRORLEVEL%\n")
            p = subprocess.run(["cmd", "/d", "/c", script], cwd=d, capture_output=True, text=True)
            self.assertEqual(p.returncode, rc, name)
            self.assertIn(f"EXIT={rc}", p.stdout)
            self.check_outputs(d, st)

    def test_powershell(self):
        for name, params, extra, rc, st in self.cases():
            d = self.design("ps_" + name, params)
            args = " ".join(["'--config'", f"'{self.config}'"] + [f"'{x}'" for x in extra])
            ps = f"Set-Location -LiteralPath '{d}'; & '{BAT}' {args}; exit $LASTEXITCODE"
            p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, rc, name)
            self.check_outputs(d, st)

    def test_heeds_mock_root_with_spaces(self):
        root = os.path.join(self.tmp, "studio HEEDS con spazi")
        for var, extra, rc, st in (("aoa=4", ["--"] + EXTRACT, 0, "4"), ("chiave_sbagliata=1", [], 1, "1")):
            subprocess.run([sys.executable, os.path.join(ROOT, "heeds_mock.py"), "--config", self.config,
                            "--var", var, "--root", root] + extra, capture_output=True, text=True)
            with open(os.path.join(root, "summary.csv"), encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]["exit_code"], rows[0]["status"]), (str(rc), st), var)
            d = os.path.join(root, "Design_1", "Analysis_1")
            self.check_outputs(d, st)
            for fn in ("params.txt", "results.txt", "run_info.txt", "driver_stdout.txt"):
                self.assertTrue(os.path.isfile(os.path.join(d, fn)), fn)
            with open(os.path.join(d, "driver_stdout.txt"), encoding="utf-8") as f:
                last = f.read().strip().splitlines()[-1]
            self.assertEqual(last, f"FS_DRIVER_RESULT status={st} success={1 - rc}")


if __name__ == "__main__":
    unittest.main()
