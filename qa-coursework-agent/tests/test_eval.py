import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class EvalTest(unittest.TestCase):
    def test_eval_passes_quality_gate(self):
        result = subprocess.run([sys.executable, str(ROOT / "eval" / "eval_runner.py")], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["pass_rate"], 1.0)
        self.assertEqual(payload["gate"], "PASSED")
        self.assertEqual(payload["judge"], "deterministic")

        data = json.loads((ROOT / "eval" / "results" / "eval_results.json").read_text(encoding="utf-8"))
        self.assertEqual(data["total"], len(data["results"]))
        self.assertEqual({r["category"] for r in data["results"]},
                         {"golden", "ambiguity", "contradiction", "critical", "injection", "boundary"})
        for case in data["results"]:
            self.assertTrue(case["passed"], f"{case['case_id']}: {case['reasons']}")


if __name__ == "__main__":
    unittest.main()
