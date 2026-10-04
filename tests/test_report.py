"""heeds_report.py: lettura delle cartelle dei design, CSV e scarto dei design con status diverso da 0.

    python -m unittest discover -s tests -v

Studio finto con la struttura di HEEDS (HEEDS_0\\Design<N>\\Analysis_1\\results.txt, anche -ERROR).
I grafici non sono controllati qui (richiedono matplotlib).
"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def results(status, aoa, cl, ld):
    return (f"schema_version = 2\nstatus = {status}\nconverged = 1\niterations = 91\nCL = {cl}\nCD = 0.02\n"
            f"CMy = -0.2\nL_over_D = {ld}\naoa = {aoa}\nvelocity = 20\n")


class TestHeedsReport(unittest.TestCase):
    def test_study(self):
        with tempfile.TemporaryDirectory(prefix="studio finto ") as study:
            designs = {"Design2": results(0, 4, 0.5767, 28.5495), "Design1": results(0, 0, 0.1905, 14.7674),
                       "Design3-ERROR": results(1, 8, -999, -999), "Design4": results(6, 12, -999, -999)}
            for name, text in designs.items():
                d = os.path.join(study, "HEEDS_0", name, "Analysis_1")
                os.makedirs(d)
                with open(os.path.join(d, "results.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
            with open(os.path.join(study, "HEEDS_0", "Design4", "Analysis_1", "run_info.txt"), "w", encoding="utf-8") as f:
                f.write("status = 6\n- FlightStream gia' attivo (FlightStream.exe PID 123)\nFS_DRIVER_RESULT status=6 success=0\n")
            out = os.path.join(study, "rep")
            p = subprocess.run([sys.executable, os.path.join(ROOT, "heeds_report.py"), "--study", study, "--out", out,
                                "--no-mock"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            with open(os.path.join(out, "report.csv"), encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r["design"] for r in rows], ["Design1", "Design2"])      # ordinati per aoa
            self.assertEqual([r["aoa"] for r in rows], ["0", "4"])
            self.assertEqual(rows[1]["CL"], "0.5767")
            with open(os.path.join(out, "scartati.txt"), encoding="utf-8") as f:
                bad = f.read()
            self.assertIn("Design3-ERROR\tcartella -ERROR (design in errore per HEEDS), status = 1", bad)
            self.assertIn("Design4\tstatus = 6 (FlightStream gia' attivo", bad)
            self.assertIn("scartati: 2", p.stdout)


MOCK = [(0, 0.1905, 0.0129, -0.098, 14.7674), (4, 0.5767, 0.0202, -0.1993, 28.5495), (8, 0.9605, 0.0383, -0.3009, 25.0783)]


def make_study(study, values, error_names=()):
    """Studio finto: un design per (aoa, CL, CD, CMy, L/D); i nomi in error_names diventano Design<N>-ERROR."""
    for i, (aoa, cl, cd, cmy, ld) in enumerate(values, 1):
        name = f"Design{i}" + ("-ERROR" if f"Design{i}" in error_names else "")
        d = os.path.join(study, "HEEDS_0", name, "Analysis_1")
        os.makedirs(d)
        with open(os.path.join(d, "results.txt"), "w", encoding="utf-8") as f:
            f.write(f"schema_version = 2\nstatus = 0\nCL = {cl}\nCD = {cd}\nCMy = {cmy}\nL_over_D = {ld}\naoa = {aoa}\n")


class TestVerifyAgainstMock(unittest.TestCase):
    def run_check(self, values, error_names=(), expect="0,4,8"):
        with tempfile.TemporaryDirectory(prefix="verifica ") as tmp:
            mock = os.path.join(tmp, "summary.csv")
            with open(mock, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["design", "status", "aoa", "CL", "CD", "CMy", "L_over_D"])
                for i, row in enumerate(MOCK, 1):
                    w.writerow([f"Design_{i:03d}", 0] + list(row))
            study = os.path.join(tmp, "studio")
            make_study(study, values, error_names)
            p = subprocess.run([sys.executable, os.path.join(ROOT, "heeds_report.py"), "--study", study,
                                "--check-against-mock", mock, "--expect-n", "3", "--expect-aoa", expect],
                               capture_output=True, text=True)
            with open(os.path.join(study, "report", "verifica.md"), encoding="utf-8") as f:
                md = f.read()
            return p.returncode, p.stdout, md

    def test_pass(self):
        rc, out, md = self.run_check(MOCK)
        self.assertEqual(rc, 0, out)
        self.assertIn("**VERIFICA OK**", md)
        self.assertEqual(md.count("| PASS |"), 3)

    def test_altered_value_fails(self):
        altered = [MOCK[0], (4, 0.5768, 0.0202, -0.1993, 28.5495), MOCK[2]]     # CL +1,7e-4 relativo
        rc, out, md = self.run_check(altered)
        self.assertEqual(rc, 1)
        self.assertIn("VERIFICA FALLITA", md)
        self.assertIn("aoa = 4: CL diff", md)
        self.assertIn("| FAIL |", md)

    def test_error_design_and_missing_aoa_fail(self):
        rc, out, md = self.run_check(MOCK, error_names=("Design2",))
        self.assertEqual(rc, 1)
        self.assertIn("Design2-ERROR", md)
        self.assertIn("valori di aoa diversi dagli attesi", md)


if __name__ == "__main__":
    unittest.main()
