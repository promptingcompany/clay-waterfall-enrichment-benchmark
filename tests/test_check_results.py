"""Published numbers in README.md and RESULTS.md match results/summary.csv."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FILES = ("scripts/check_results.py", "results/summary.csv", "README.md", "RESULTS.md")


def check(repo):
    return subprocess.run([sys.executable, "-I", str(repo / "scripts" / "check_results.py")], capture_output=True, text=True)


class CheckResults(unittest.TestCase):
    def test_committed_files_match_summary(self):
        run = check(REPO)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_a_changed_number_fails(self):
        # 101% can't be a rate, so it's a number summary.csv doesn't give; 58% is one it gives, but for another cut.
        for name, pattern, wrong in (("RESULTS.md", r"\| \d+%", "| 101%"),   # first rate in a generated table
                                     ("README.md", r"\d+%", "101%"),         # the headline rate
                                     ("README.md", r"\d+%", "58%"),
                                     ("README.md", "## Results", "## Outcome")):   # no Results section to check
            with self.subTest(file=name, wrong=wrong), tempfile.TemporaryDirectory() as tmp:
                for f in FILES:
                    (Path(tmp) / f).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(REPO / f, Path(tmp) / f)
                text = (Path(tmp) / name).read_text(encoding="utf-8")
                edited, n = re.subn(pattern, wrong, text, count=1)
                self.assertEqual(n, 1)
                (Path(tmp) / name).write_text(edited, encoding="utf-8")
                run = check(Path(tmp))
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
