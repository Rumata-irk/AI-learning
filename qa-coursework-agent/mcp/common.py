"""Shared helpers for the coursework MCP servers."""
import json
import os
import tempfile
import threading
from pathlib import Path

WRITE_LOCK = threading.Lock()


def fail_after():
    raw = os.environ.get("QA_FAIL_AFTER", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def load_store(path: Path):
    if not path.exists():
        return {"items": [], "writes": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError(f"Invalid store {path}; refusing to overwrite")
    data.setdefault("writes", 0)
    return data


def save_store(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".store-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def create_item(path: Path, kind: str, project: str, external_key: str, title: str, description: str):
    if not all(isinstance(x, str) and x.strip() for x in (project, external_key, title, description)):
        raise ValueError("project, external_key, title and description must be non-empty")
    with WRITE_LOCK:
        store = load_store(path)
        for item in store["items"]:
            if item["kind"] == kind and item["project"] == project and item["external_key"] == external_key:
                if item["title"] != title or item["description"] != description:
                    raise ValueError("External key exists with different content")
                return {"created": False, "item": item}
        limit = fail_after()
        if limit is not None and store["writes"] >= limit:
            store["writes"] = 0
            save_store(path, store)
            raise RuntimeError("Simulated partial failure; retry to resume")
        item = {
            "id": f"{kind.upper()}-{len([i for i in store['items'] if i['kind'] == kind]) + 1}",
            "kind": kind,
            "project": project,
            "external_key": external_key,
            "title": title,
            "description": description,
        }
        store["items"].append(item)
        store["writes"] = store.get("writes", 0) + 1
        save_store(path, store)
        return {"created": True, "item": item}


def find_item(path: Path, kind: str, project: str, external_key: str):
    with WRITE_LOCK:
        store = load_store(path)
    return {"items": [i for i in store["items"] if i["kind"] == kind and i["project"] == project and i["external_key"] == external_key]}
