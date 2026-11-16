"""Local, persistent demonstration tools exposed over MCP stdio.

Environment variables:
  QA_LOCAL_STORE       path to the JSON store (default demo/store.json)
  QA_LOCAL_FAIL_AFTER  if set to N>0, the (N+1)-th successful write fails
                       once, then the counter is cleared; used to reproduce
                       a partial-failure scenario during tests
"""
import json
import os
import tempfile
import threading
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "demo" / "requirements.json"
STORE = Path(os.environ.get("QA_LOCAL_STORE", str(ROOT / "demo" / "store.json")))
LOCK = threading.Lock()
mcp = FastMCP("qa-local")


def _fail_after():
    raw = os.environ.get("QA_LOCAL_FAIL_AFTER", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _load():
    if not STORE.exists():
        return {"tasks": [], "tests": [], "writes": 0}
    data = json.loads(STORE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list) or not isinstance(data.get("tests"), list):
        raise ValueError("Invalid local store; refusing to overwrite it")
    data.setdefault("writes", 0)
    return data


def _save(data):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".qa-store-", suffix=".tmp", dir=STORE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(name, STORE)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@mcp.tool()
def get_requirements(page_id: str) -> dict:
    """Read a requirements page from the local demo fixture, not Confluence."""
    pages = json.loads(DATA.read_text(encoding="utf-8"))
    if page_id not in pages:
        raise ValueError(f"Demo page not found: {page_id}")
    page = pages[page_id]
    if isinstance(page, str):
        return {"source": "local-demo", "page_id": page_id, "title": page_id, "text": page}
    body = page["body"]
    text = "\n".join(body) if isinstance(body, list) else body
    return {"source": "local-demo", "page_id": page_id, "title": page.get("title", page_id), "text": text}


def _create(kind, project, external_key, title, description):
    if not all(isinstance(x, str) and x.strip() for x in (project, external_key, title, description)):
        raise ValueError("project, external_key, title and description must be non-empty")
    with LOCK:
        store = _load()
        for item in store[kind]:
            if item["project"] == project and item["external_key"] == external_key:
                if item["title"] != title or item["description"] != description:
                    raise ValueError("External key already exists with different content")
                return {"created": False, "item": item}
        limit = _fail_after()
        if limit is not None and store["writes"] >= limit:
            store["writes"] = 0
            _save(store)
            raise RuntimeError("Simulated partial failure after the write limit; retry to continue")
        prefix = "TASK" if kind == "tasks" else "TC"
        item = {"id": f"LOCAL-{prefix}-{len(store[kind]) + 1}", "project": project,
                "external_key": external_key, "title": title, "description": description}
        store[kind].append(item)
        store["writes"] = store.get("writes", 0) + 1
        _save(store)
        return {"created": True, "item": item}


@mcp.tool()
def create_task(project: str, external_key: str, title: str, description: str) -> dict:
    """Create or retrieve an idempotent local demonstration task, not a Jira issue."""
    return _create("tasks", project, external_key, title, description)


@mcp.tool()
def create_test(project: str, external_key: str, title: str, description: str) -> dict:
    """Create or retrieve an idempotent local demonstration test, not a Qase test."""
    return _create("tests", project, external_key, title, description)


@mcp.tool()
def find_item(kind: str, project: str, external_key: str) -> dict:
    """Find an existing local task or test by project and external key."""
    if kind not in ("tasks", "tests"):
        raise ValueError("kind must be tasks or tests")
    with LOCK:
        matches = [x for x in _load()[kind] if x["project"] == project and x["external_key"] == external_key]
    return {"items": matches}


if __name__ == "__main__":
    mcp.run(transport="stdio")
