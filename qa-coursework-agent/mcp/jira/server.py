"""Jira-like MCP server over stdio: writes are idempotent and can fail."""
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import create_item, find_item  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
STORE = Path(os.environ.get("QA_JIRA_STORE", str(ROOT / "data" / "jira_tasks.json")))
mcp = FastMCP("jira-write")


@mcp.tool()
def create_issue(project: str, external_key: str, title: str, description: str) -> dict:
    """Create a task. Repeating the same external_key returns the existing item."""
    return create_item(STORE, "task", project, external_key, title, description)


@mcp.tool()
def find_issue(project: str, external_key: str) -> dict:
    """Look up an existing task by project and external key."""
    return find_item(STORE, "task", project, external_key)


if __name__ == "__main__":
    mcp.run(transport="stdio")
