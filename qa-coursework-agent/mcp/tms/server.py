"""TMS-like (Qase) MCP server over stdio: idempotent writes, fail-after support."""
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import create_item, find_item  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
STORE = Path(os.environ.get("QA_TMS_STORE", str(ROOT / "data" / "tms_cases.json")))
mcp = FastMCP("tms-write")


@mcp.tool()
def create_case(project: str, external_key: str, title: str, description: str) -> dict:
    """Create a test case. Repeating the same external_key returns the existing item."""
    return create_item(STORE, "case", project, external_key, title, description)


@mcp.tool()
def find_case(project: str, external_key: str) -> dict:
    """Look up an existing test case by project and external key."""
    return find_item(STORE, "case", project, external_key)


if __name__ == "__main__":
    mcp.run(transport="stdio")
