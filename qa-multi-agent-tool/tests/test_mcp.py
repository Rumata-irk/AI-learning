import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


def payload(result):
    return result.structuredContent or json.loads(result.content[0].text)


class MCPIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_tools_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["QA_LOCAL_STORE"] = str(Path(tmp) / "store.json")
            server = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp-local" / "server.py")], env=env)
            async with stdio_client(server) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertTrue({"get_requirements", "create_task", "create_test", "find_item"} <= {t.name for t in tools.tools})
                    page = await session.call_tool("get_requirements", {"page_id": "healthchecker-demo"})
                    self.assertFalse(page.isError)
                    self.assertIn("Prometheus", str(page.content))
                    args = {"project": "DEMO", "external_key": "run:task-1", "title": "Task", "description": "Acceptance criterion"}
                    first = await session.call_tool("create_task", args)
                    second = await session.call_tool("create_task", args)
                    self.assertFalse(first.isError)
                    self.assertFalse(second.isError)
                    self.assertTrue(payload(first)["created"])
                    self.assertFalse(payload(second)["created"])
                    self.assertEqual(payload(first)["item"]["id"], payload(second)["item"]["id"])
                    conflict = await session.call_tool("create_task", {**args, "title": "Different"})
                    self.assertTrue(conflict.isError)
                    test = await session.call_tool("create_test", {**args, "external_key": "run:tc-1"})
                    self.assertFalse(test.isError)
                    found = await session.call_tool("find_item", {"kind": "tests", "project": "DEMO", "external_key": "run:tc-1"})
                    self.assertEqual(len(payload(found)["items"]), 1)
                    missing = await session.call_tool("get_requirements", {"page_id": "missing"})
                    self.assertTrue(missing.isError)


if __name__ == "__main__":
    unittest.main()
