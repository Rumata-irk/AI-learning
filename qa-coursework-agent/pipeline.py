"""Pipeline for the coursework agent.

Deterministic by default: the same rules that the agent follows are applied
in code so that the eval run is reproducible in CI without a model.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


@dataclass
class PipelineResult:
    requirements: dict = field(default_factory=dict)
    tasks: dict = field(default_factory=dict)
    tests: dict = field(default_factory=dict)
    writes: list = field(default_factory=list)
    blocked_write: bool = False
    notes: list = field(default_factory=list)


def load_page(page_id: str) -> dict:
    pages = json.loads((DATA / "confluence_pages.json").read_text(encoding="utf-8"))
    if page_id not in pages:
        raise ValueError(f"Page not found: {page_id}")
    return pages[page_id]


def _split_requirements(text: str) -> list[dict]:
    items = []
    for raw in re.split(r"(?<=[.!?])\s+", text.strip()):
        sentence = raw.strip()
        if not sentence:
            continue
        items.append(sentence)
    return items


def review_requirements(page: dict) -> dict:
    """Analyse a page: requirements, issues, frozen scope, status."""
    from guardrails import guard

    body = page["body"]
    sentences = _split_requirements(body)
    requirements = []
    issues = []

    for idx, sentence in enumerate(sentences, start=1):
        req_id = f"REQ-{idx}"
        requirements.append({"id": req_id, "text": sentence, "evidence": sentence, "type": "functional"})

    injection_hits = guard.detect_injection(body)
    if injection_hits:
        issues.append({
            "id": "P-INJ",
            "kind": "security",
            "severity": "blocker",
            "blocking": True,
            "requirement_refs": [r["id"] for r in requirements],
            "scope": [r["id"] for r in requirements],
            "description": "В требованиях найдена инструкция, пытающаяся изменить правила агента",
            "question": "Подтвердите, что текст является данными, а не инструкцией для агента",
        })

    for req in requirements:
        text = req["text"].lower()
        if "не определен" in text or "не задан" in text or "неопределён" in text:
            issues.append({
                "id": f"P-{req['id'][4:]}",
                "kind": "gap",
                "severity": "blocker",
                "blocking": True,
                "requirement_refs": [req["id"]],
                "scope": [req["id"]],
                "description": f"Поведение не определено: {req['text']}",
                "question": "Какое поведение ожидается в этом случае?",
            })
        if re.search(r"через\s+(\d+)\s+секунд.*(не более|и не менее|ровно)", text):
            issues.append({
                "id": f"P-{req['id'][4:]}b",
                "kind": "conflict",
                "severity": "blocker",
                "blocking": True,
                "requirement_refs": [req["id"]],
                "scope": [req["id"]],
                "description": "Внутреннее противоречие в формулировке интервала",
                "question": "Какой интервал считать корректным?",
            })

    frozen = {}
    for issue in issues:
        if issue["blocking"]:
            for req_id in issue["requirement_refs"]:
                frozen.setdefault(req_id, []).append(issue["id"])

    frozen_scope = [{"requirement_refs": sorted(set(k for k, v in frozen.items() if ref in v)), "issue_refs": [ref], "reason": "blocker"}
                    for ref in {i for ids in frozen.values() for i in ids}]
    frozen_scope = [{"requirement_refs": [req_id for req_id, refs in frozen.items() if ref in refs], "issue_refs": [ref], "reason": "blocker"} for ref in sorted({r for refs in frozen.values() for r in refs})]

    if not issues:
        status = "ready"
    elif len(frozen) >= len(requirements):
        status = "blocked"
    else:
        status = "ready_partial"

    return {
        "artifact": "requirements_analysis",
        "version": "1.0",
        "page_id": page.get("page_id", ""),
        "status": status,
        "requirements": requirements,
        "issues": issues,
        "frozen_scope": frozen_scope,
        "clarifications": [
            {"id": f"CLR-{issue['id']}", "question": issue["question"], "requirement_refs": issue["requirement_refs"]}
            for issue in issues
        ],
        "notes": injection_hits,
    }


def design_tasks(review: dict) -> dict:
    frozen = {r for item in review.get("frozen_scope", []) for r in item["requirement_refs"]}
    tasks, drafts = [], []
    for idx, req in enumerate(review["requirements"], start=1):
        entry = {
            "id": f"TASK-{idx}",
            "summary": req["text"][:80],
            "requirement_refs": [req["id"]],
            "acceptance_criteria": [f"Наблюдаемо: {req['text']}"] if req["id"] not in frozen else [],
            "status": "ready" if req["id"] not in frozen else "pending_clarification",
        }
        if req["id"] in frozen:
            entry["frozen_by"] = sorted({i["id"] for i in review["issues"] if req["id"] in i["requirement_refs"]})
            drafts.append(entry)
        else:
            tasks.append(entry)
    return {"artifact": "jira_tasks", "version": "1.0", "tasks": tasks, "drafts": drafts}


def design_tests(review: dict) -> dict:
    frozen = {r for item in review.get("frozen_scope", []) for r in item["requirement_refs"]}
    scenarios, drafts = [], []
    for idx, req in enumerate(review["requirements"], start=1):
        entry = {
            "id": f"TC-{idx}",
            "title": f"Проверка требования {req['id']}",
            "type": "positive",
            "requirement_refs": [req["id"]],
            "expected_result": req["text"],
            "status": "ready" if req["id"] not in frozen else "blocked_by_clarification",
        }
        if req["id"] in frozen:
            entry["frozen_by"] = sorted({i["id"] for i in review["issues"] if req["id"] in i["requirement_refs"]})
            drafts.append(entry)
        else:
            scenarios.append(entry)
    return {"artifact": "test_model", "version": "1.0", "scenarios": scenarios, "drafts": drafts}


def run(page_id: str, mode: str = "design") -> PipelineResult:
    from guardrails import guard

    page = load_page(page_id)
    review = review_requirements(page)
    tasks = design_tasks(review)
    tests = design_tests(review)
    result = PipelineResult(requirements=review, tasks=tasks, tests=tests)

    for kind, artifact in (("requirements", review), ("tasks", tasks), ("tests", tests)):
        errors = guard.validate_artifact(kind, artifact)
        if errors:
            result.notes.extend(errors)

    if mode == "write":
        allowed, reasons = guard.can_write(review)
        if not allowed:
            result.blocked_write = True
            result.notes.extend(reasons)
            return result
        ready_tasks, ready_tests = guard.select_write_items(tasks, tests)
        for item in ready_tasks:
            result.writes.append(("task", item["id"]))
        for item in ready_tests:
            result.writes.append(("case", item["id"]))

    return result
