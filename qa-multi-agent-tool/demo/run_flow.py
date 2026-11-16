"""Deterministic offline demonstration of the multi-agent workflow.

This is a validation harness for artifacts and gates. It does not claim to
run an LLM agent and it does not create Jira/Qase records.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "demo" / "requirements.json"
ARTIFACTS = ROOT / "artifacts"


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    out = ARTIFACTS / run_id
    out.mkdir(parents=True, exist_ok=False)
    source = json.loads(SOURCE.read_text(encoding="utf-8"))["healthchecker-demo"]
    (out / "source.md").write_text(source + "\n", encoding="utf-8")

    requirements = [
        {"id": "REQ-1", "text": "Healthchecker получает marketplace_api.health из Prometheus.", "evidence": "получает метрики функционального блока marketplace_api.health из Prometheus", "type": "functional"},
        {"id": "REQ-2", "text": "Интервал опроса составляет 60 секунд.", "evidence": "Интервал опроса составляет 60 секунд", "type": "functional"},
        {"id": "REQ-3", "text": "После успешного получения сохраняется последнее значение метрики.", "evidence": "сохраняет последнее значение метрики", "type": "functional"},
    ]
    issue = {"id": "P-001", "kind": "gap", "requirement_refs": ["REQ-1"], "description": "Не определено поведение при недоступности Prometheus", "severity": "blocker", "blocking": True, "scope": ["REQ-1"], "question": "Какой результат и статус должен возвращать Healthchecker при недоступности Prometheus?"}
    review = {
        "artifact": "requirements_analysis",
        "version": "2.0",
        "run_id": run_id,
        "status": "ready_partial",
        "requirements": requirements,
        "issues": [issue],
        "frozen_scope": [{"requirement_refs": ["REQ-1"], "issue_refs": ["P-001"], "reason": "missing failure behavior"}],
        "clarifications": [{"id": "CLR-1", "question": issue["question"], "requirement_refs": ["REQ-1"]}],
    }
    dump(out / "review.json", review)

    tasks = {
        "artifact": "jira_tasks",
        "version": "2.0",
        "mode": "demo",
        "tasks": [
            {"id": "TASK-2", "summary": "Опрашивать Prometheus с интервалом 60 секунд", "requirement_refs": ["REQ-2"], "acceptance_criteria": ["Последовательные плановые опросы выполняются с интервалом 60 секунд"], "status": "ready"},
            {"id": "TASK-3", "summary": "Сохранять последнее успешное значение метрики", "requirement_refs": ["REQ-3"], "acceptance_criteria": ["После успешного опроса доступно последнее значение метрики"], "status": "ready"},
        ],
        "drafts": [
            {"id": "DRAFT-TASK-1", "summary": "Получать marketplace_api.health из Prometheus", "requirement_refs": ["REQ-1"], "acceptance_criteria": [], "status": "pending_clarification", "frozen_by": ["P-001"], "clarification_refs": ["CLR-1"], "note": "Не подлежит созданию до снятия P-001"},
        ],
        "clarification_requests": review["clarifications"],
    }
    dump(out / "tasks.json", tasks)

    tests = {
        "artifact": "test_model",
        "version": "2.0",
        "mode": "demo",
        "scenarios": [
            {"id": "TC-2", "title": "Плановый опрос выполняется через 60 секунд", "type": "boundary", "requirement_refs": ["REQ-2"], "status": "ready"},
            {"id": "TC-3", "title": "Сохранение последнего значения после успешного опроса", "type": "positive", "requirement_refs": ["REQ-3"], "status": "ready"},
        ],
        "drafts": [
            {"id": "DRAFT-TC-1", "title": "Получение метрики при доступном Prometheus", "type": "positive", "requirement_refs": ["REQ-1"], "status": "blocked_by_clarification", "frozen_by": ["P-001"]},
        ],
        "coverage_exceptions": [
            {"requirement_id": "REQ-1", "type": "negative", "reason": "Поведение при отказе не задано в требованиях; область заморожена"},
        ],
    }
    dump(out / "test_model.json", tests)

    report = f"""# Demo workflow report

- Run: `{run_id}`
- Mode: `demo`
- Final status: `PARTIAL`
- Requirement review: `ready_partial`
- Ready tasks: {len(tasks["tasks"])}
- Draft tasks (не подлежат созданию): {len(tasks["drafts"])}
- Ready scenarios: {len(tests["scenarios"])}
- Draft scenarios (не подлежат созданию): {len(tests["drafts"])}
- External Jira/Qase writes: 0

## Quality Gates

- QG-1: `ready_partial` — `P-001` (blocker) заморозил `REQ-1`.
- QG-2: готовые задачи {", ".join(t["id"] for t in tasks["tasks"])}; черновик `DRAFT-TASK-1` исключён из записи.
- QG-3: готовые сценарии {", ".join(t["id"] for t in tests["scenarios"])}; негативная проверка по `REQ-1` не создана, причина зафиксирована.

## Черновики, не подлежащие созданию

- `DRAFT-TASK-1` (`REQ-1`) — заморожен `P-001`.
- `DRAFT-TC-1` (`REQ-1`) — заморожен `P-001`.

Следующий этап читает только массивы `tasks` и `scenarios`.

## Clarification required

CLR-1: {issue["question"]}

Artifacts are in this directory. Local MCP data is not Jira or Qase data.
"""
    (out / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"run_id": run_id, "status": "PARTIAL", "artifacts": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
