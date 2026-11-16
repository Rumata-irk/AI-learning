"""Read-only Confluence-like MCP server over stdio."""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent.parent
PAGES = ROOT / "data" / "confluence_pages.json"
mcp = FastMCP("confluence-read-only")


@mcp.tool()
def get_page(page_id: str) -> dict:
    """Read a requirements page. This tool cannot modify content."""
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    if page_id not in pages:
        raise ValueError(f"Page not found: {page_id}")
    page = pages[page_id]
    return {"page_id": page_id, "title": page["title"], "body": page["body"], "children": page.get("children", [])}


@mcp.tool()
def search(query: str) -> dict:
    """Search page titles and bodies by substring."""
    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    hits = []
    for page_id, page in pages.items():
        text = f"{page['title']} {page['body']}".lower()
        if query.lower() in text:
            hits.append({"page_id": page_id, "title": page["title"]})
    return {"items": hits}


if __name__ == "__main__":
    mcp.run(transport="stdio")
