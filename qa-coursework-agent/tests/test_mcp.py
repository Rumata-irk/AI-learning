import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
CONFLUENCE = str(ROOT / "mcp" / "confluence" / "server.py")
JIRA = str(ROOT / "mcp" / "jira" / "server.py")
TMS = str(ROOT / "mcp" / "tms" / "server.py")


def payload(result):
    return result.structuredContent or json.loads(result.content[0].text)


def issue(project, key, title):
    return {"project": project, "external_key": key, "title": title, "description": "criterion"}


class MCPTest(unittest.IsolatedAsyncioTestCase):
    async def test_confluence_is_read_only(self):
        async with stdio_client(StdioServerParameters(command=sys.executable, args=[CONFLUENCE], env=os.environ.copy())) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                self.assertEqual(names, {"get_page", "search"})
                page = await session.call_tool("get_page", {"page_id": "HC-101"})
                self.assertFalse(page.isError)
                missing = await session.call_tool("get_page", {"page_id": "nope"})
                self.assertTrue(missing.isError)

    async def test_jira_write_idempotent_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["QA_JIRA_STORE"] = str(Path(tmp) / "jira.json")
            env["QA_FAIL_AFTER"] = "1"
            async with stdio_client(StdioServerParameters(command=sys.executable, args=[JIRA], env=env)) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    first = await session.call_tool("create_issue", issue("CW", "run:1", "A"))
                    second = await session.call_tool("create_issue", issue("CW", "run:2", "B"))
                    self.assertFalse(first.isError)
                    self.assertTrue(second.isError, "second write must fail (partial failure)")

            env.pop("QA_FAIL_AFTER")
            async with stdio_client(StdioServerParameters(command=sys.executable, args=[JIRA], env=env)) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    again1 = await session.call_tool("create_issue", issue("CW", "run:1", "A"))
                    again2 = await session.call_tool("create_issue", issue("CW", "run:2", "B"))
                    self.assertFalse(payload(again1)["created"], "must not duplicate")
                    self.assertTrue(payload(again2)["created"], "missing item must be created")
                    conflict = await session.call_tool("create_issue", issue("CW", "run:1", "Changed"))
                    self.assertTrue(conflict.isError)

    async def test_tms_write_and_find(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["QA_TMS_STORE"] = str(Path(tmp) / "tms.json")
            async with stdio_client(StdioServerParameters(command=sys.executable, args=[TMS], env=env)) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    created = await session.call_tool("create_case", issue("CW", "run:tc-1", "TC"))
                    self.assertFalse(created.isError)
                    found = await session.call_tool("find_case", {"project": "CW", "external_key": "run:tc-1"})
                    self.assertEqual(len(payload(found)["items"]), 1)


if __name__ == "__main__":
    unittest.main()
