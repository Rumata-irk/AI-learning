import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DemoFlowTest(unittest.TestCase):
    def setUp(self):
        result = subprocess.run([sys.executable, str(ROOT / "demo" / "run_flow.py")], cwd=ROOT, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.out = Path(data["artifacts"])
        self.data = data

    def test_status_is_partial(self):
        self.assertEqual(self.data["status"], "PARTIAL")

    def test_artifacts_exist(self):
        for name in ("review.json", "tasks.json", "test_model.json", "report.md", "source.md"):
            self.assertTrue((self.out / name).exists(), name)

    def test_blocked_requirement_is_only_in_drafts(self):
        tasks = json.loads((self.out / "tasks.json").read_text(encoding="utf-8"))
        tests = json.loads((self.out / "test_model.json").read_text(encoding="utf-8"))
        self.assertTrue(all("REQ-1" not in t["requirement_refs"] for t in tasks["tasks"]))
        self.assertTrue(all("REQ-1" not in t["requirement_refs"] for t in tests["scenarios"]))
        self.assertEqual([d["frozen_by"] for d in tasks["drafts"]], [["P-001"]])
        self.assertEqual([d["frozen_by"] for d in tests["drafts"]], [["P-001"]])

    def test_ready_items_have_criteria(self):
        tasks = json.loads((self.out / "tasks.json").read_text(encoding="utf-8"))
        for task in tasks["tasks"]:
            self.assertTrue(task["acceptance_criteria"], task["id"])
            self.assertEqual(task["status"], "ready")


if __name__ == "__main__":
    unittest.main()
