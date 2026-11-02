import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DemoFlowTest(unittest.TestCase):
    def test_creates_partial_artifacts_without_external_writes(self):
        result = subprocess.run([sys.executable, str(ROOT / "demo" / "run_flow.py")], cwd=ROOT, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        out = Path(data["artifacts"])
        self.assertEqual(data["status"], "PARTIAL")
        self.assertTrue((out / "review.json").exists())
        self.assertTrue((out / "tasks.json").exists())
        self.assertTrue((out / "test_model.json").exists())
        self.assertTrue((out / "report.md").exists())
        tasks = json.loads((out / "tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(tasks["tasks"][0]["status"], "pending_clarification")
        self.assertEqual(tasks["tasks"][0]["acceptance_criteria"], [])


if __name__ == "__main__":
    unittest.main()
