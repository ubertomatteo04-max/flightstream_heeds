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
            self.assertIn("Design3-ERROR\tstatus = 1", bad)
            self.assertIn("Design4\tstatus = 6 (FlightStream gia' attivo", bad)
            self.assertIn("scartati: 2", p.stdout)


if __name__ == "__main__":
    unittest.main()
