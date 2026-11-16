"""Guardrails for the coursework agent.

They are plain Python so that both the agent flow and the eval runner can
apply the same rules without an LLM.
"""
import re
from typing import Any

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions",
    r"system\s+prompt",
    r"you\s+are\s+now\s+(an?\s+)?admin",
    r"disregard\s+your\s+rules",
    r"не\s+обращай\s+внимания\s+на\s+(предыдущие\s+)?инструкции",
    r"игнорируй\s+(все\s+)?(предыдущие\s+)?инструкции",
    r"покажи\s+(свой\s+)?системный\s+промпт",
    r"создай\s+(задачу|тест)\s+без\s+проверки",
]

SECRET_PATTERNS = [
    r"api[_-]?key\s*[:=]\s*\S+",
    r"bearer\s+[A-Za-z0-9._\-]{12,}",
    r"(password|пароль)\s*[:=]\s*\S+",
]

REQUIRED_ARTIFACT_KEYS = {
    "requirements": ("status", "requirements", "issues", "frozen_scope"),
    "tasks": ("tasks", "drafts"),
    "tests": ("scenarios", "drafts"),
}


def detect_injection(text: str) -> list[str]:
    """Return matched injection markers found in untrusted text."""
    hits = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def redact_secrets(text: str) -> str:
    """Remove obvious secrets before they reach artifacts or logs."""
    result = text
    for pattern in SECRET_PATTERNS:
        result = re.sub(pattern, "[REDACTED]", result, flags=re.IGNORECASE)
    return result


def validate_artifact(kind: str, data: Any) -> list[str]:
    """Check that a stage artifact has the fields the next stage relies on."""
    keys = REQUIRED_ARTIFACT_KEYS.get(kind)
    if keys is None:
        return [f"unknown artifact kind: {kind}"]
    if not isinstance(data, dict):
        return [f"{kind}: artifact is not an object"]
    errors = [f"{kind}: missing field {k}" for k in keys if k not in data]
    if kind == "requirements":
        reqs = data.get("requirements") or []
        issue_ids = {i.get("id") for i in data.get("issues", [])}
        for idx, req in enumerate(reqs):
            if not req.get("id") or not req.get("evidence"):
                errors.append(f"{kind}: requirement #{idx} has no id or evidence")
        for frozen in data.get("frozen_scope", []):
            for ref in frozen.get("issue_refs", []):
                if ref not in issue_ids:
                    errors.append(f"{kind}: frozen_scope references unknown issue {ref}")
    if kind == "tasks":
        for task in data.get("tasks", []):
            if not task.get("requirement_refs"):
                errors.append(f"{kind}: task {task.get('id')} has no requirement_refs")
            if not task.get("acceptance_criteria"):
                errors.append(f"{kind}: ready task {task.get('id')} has no acceptance criteria")
        for draft in data.get("drafts", []):
            if not draft.get("frozen_by"):
                errors.append(f"{kind}: draft {draft.get('id')} is not marked as frozen")
    if kind == "tests":
        for case in data.get("scenarios", []):
            if not case.get("requirement_refs"):
                errors.append(f"{kind}: scenario {case.get('id')} has no requirement_refs")
    return errors


def can_write(requirements: dict) -> tuple[bool, list[str]]:
    """Writing to Jira/TMS is only allowed when no blocking issue is open."""
    blockers = [i for i in requirements.get("issues", []) if i.get("blocking") or i.get("severity") == "blocker"]
    if blockers:
        return False, [f"blocking issue {i.get('id')} blocks external writes" for i in blockers]
    if requirements.get("status") == "blocked":
        return False, ["requirements status is blocked"]
    frozen = requirements.get("frozen_scope") or []
    if frozen:
        return False, [f"frozen scope present: {frozen}"]
    return True, []


def select_write_items(tasks: dict, tests: dict) -> tuple[list[dict], list[dict]]:
    """Only ready arrays are eligible; drafts and frozen items never are."""
    ready_tasks = [
        t for t in tasks.get("tasks", [])
        if t.get("acceptance_criteria") and not t.get("frozen_by") and t.get("status", "ready") == "ready"
    ]
    ready_tests = [
        c for c in tests.get("scenarios", [])
        if c.get("requirement_refs") and not c.get("frozen_by") and c.get("status", "ready") == "ready"
    ]
    return ready_tasks, ready_tests
