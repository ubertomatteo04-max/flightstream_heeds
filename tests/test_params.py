"""params.txt: formati di stampa di HEEDS accettati, errori rifiutati con status 1.

    python -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fs_driver  # noqa: E402


def write(d, data):
    """Scrive params.txt cosi' com'e' (bytes: controllo esatto di CRLF e dell'ultima riga)."""
    p = os.path.join(d, "params.txt")
    with open(p, "wb") as f:
        f.write(data)
    return p


class TestReadParams(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, data):
        return fs_driver.read_params(write(self.tmp.name, data))

    def test_float_formats(self):
        for text, val in (("4", 4.0), ("4.0", 4.0), ("4.", 4.0), (".5", 0.5), ("4.000000E+00", 4.0),
                          ("4.0e0", 4.0), ("-1.5E-01", -0.15), ("+2", 2.0), ("1.0000000000000000E+01", 10.0),
                          ("0.000000e+00", 0.0), ("-0", 0.0)):
            self.assertEqual(self.read(f"aoa = {text}\n".encode()), {"aoa": val}, text)

    def test_spaces_crlf_last_line_bom(self):
        data = b"\xef\xbb\xbf# commento\r\n  aoa   =   4.000000E+00   \r\n\r\nvelocity=2.000000E+01"
        self.assertEqual(self.read(data), {"aoa": 4.0, "velocity": 20.0})
        self.assertEqual(self.read(b"aoa\t=\t4\t# gradi\n"), {"aoa": 4.0})

    def test_rejected(self):
        bad = {b"aoa = quattro\n": "non numerico", b"aoa = 4,0\n": "non numerico", b"aoa = 4 5\n": "non numerico",
               b"aoa = nan\n": "non numerico", b"aoa = inf\n": "non numerico", b"aoa = 1_000\n": "non numerico",
               b"aoa = 0x10\n": "non numerico", b"aoa = \n": "non numerico", b"aoa = 4.0D+00\n": "non numerico",
               b"aoa 4\n": "chiave = valore", b"aoa == 4\n": "chiave = valore", b"aoa = 4 = 5\n": "chiave = valore",
               b"= 4\n": "nome di variabile", b"a oa = 4\n": "nome di variabile", b"4aoa = 4\n": "nome di variabile",
               b"aoa = 4\naoa = 6\n": "piu' di una volta"}
        for data, msg in bad.items():
            with self.assertRaises(ValueError, msg=data) as cm:
                self.read(data)
            self.assertIn(msg, str(cm.exception), data)

    def test_driver_status1_on_bad_params(self):
        """Attraverso il driver: params.txt sbagliato -> status 1, codice di uscita 1, motivo in run_info."""
        with open(os.path.join(ROOT, "case_semiala_fixed.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["geometry"]["template_fsm"] = os.path.join(ROOT, "..", "semiala_run01.fsm")
        d = self.tmp.name
        with open(os.path.join(d, "case.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        for data in (b"aoa = 4\r\naoa = 4\r\n", b"aoa = 4.0.0\r\n", b"aoa: 4\r\n"):
            write(d, data)
            p = subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config",
                                os.path.join(d, "case.json"), "--workdir", d, "--dry-run"], capture_output=True, text=True)
            with open(os.path.join(d, "results.txt"), encoding="utf-8") as f:
                res = dict(ln.strip().split(" = ", 1) for ln in f if " = " in ln)
            with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
                info = f.read()
            self.assertEqual((res["status"], p.returncode), ("1", 1), data)
            self.assertIn("params.txt riga", info, data)
        # stesso file con i formati di HEEDS: il dry-run arriva fino allo script (status 1 solo per il dry-run)
        write(d, b"aoa = 4.000000E+00\r\nvelocity = 2.000000E+01\r\nsideslip = 0.000000E+00")
        subprocess.run([sys.executable, os.path.join(ROOT, "fs_driver.py"), "--config", os.path.join(d, "case.json"),
                        "--workdir", d, "--dry-run"], capture_output=True, text=True)
        with open(os.path.join(d, "run_info.txt"), encoding="utf-8") as f:
            self.assertIn("dry-run", f.read())
        with open(os.path.join(d, "fs_script.txt"), encoding="utf-8") as f:
            self.assertIn("SOLVER_SET_AOA 4\n", f.read())


if __name__ == "__main__":
    unittest.main()
