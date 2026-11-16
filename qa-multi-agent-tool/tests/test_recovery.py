import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SERVER = str(ROOT / "mcp-local" / "server.py")


def payload(result):
    return result.structuredContent or json.loads(result.content[0].text)


def item(project, key, title):
    return {"project": project, "external_key": key, "title": title, "description": "criteria"}


class RecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_partial_failure_then_resume_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "store.json"
            env = os.environ.copy()
            env["QA_LOCAL_STORE"] = str(store)
            env["QA_LOCAL_FAIL_AFTER"] = "2"
            server = StdioServerParameters(command=sys.executable, args=[SERVER], env=env)

            async with stdio_client(server) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    first = await session.call_tool("create_task", item("DEMO", "run:1", "A"))
                    second = await session.call_tool("create_task", item("DEMO", "run:2", "B"))
                    third = await session.call_tool("create_task", item("DEMO", "run:3", "C"))
                    self.assertFalse(first.isError)
                    self.assertFalse(second.isError)
                    self.assertTrue(third.isError, "third write must fail to simulate partial failure")

            # A new process must resume from the same store.
            env.pop("QA_LOCAL_FAIL_AFTER")
            server = StdioServerParameters(command=sys.executable, args=[SERVER], env=env)
            async with stdio_client(server) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    again1 = await session.call_tool("create_task", item("DEMO", "run:1", "A"))
                    again2 = await session.call_tool("create_task", item("DEMO", "run:2", "B"))
                    again3 = await session.call_tool("create_task", item("DEMO", "run:3", "C"))
                    self.assertFalse(payload(again1)["created"], "existing record must not be duplicated")
                    self.assertFalse(payload(again2)["created"], "existing record must not be duplicated")
                    self.assertTrue(payload(again3)["created"], "missing record must be created on resume")
                    self.assertEqual(payload(again1)["item"]["id"], payload(again1)["item"]["id"])

            data = json.loads(store.read_text(encoding="utf-8"))
            self.assertEqual(len(data["tasks"]), 3)
            self.assertEqual(sorted(t["external_key"] for t in data["tasks"]), ["run:1", "run:2", "run:3"])


if __name__ == "__main__":
    unittest.main()
