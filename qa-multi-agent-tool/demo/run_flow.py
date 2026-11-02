"""Deterministic offline demonstration of the multi-agent workflow.

This is a validation harness for artifacts and gates. It does not claim to
run an LLM agent and it does not create Jira/Qase records.
"""
import json
import re
import sys
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
    issues = [{"id": "ISS-1", "kind": "gap", "requirement_refs": ["REQ-1"], "description": "Не определено поведение при недоступности Prometheus", "blocking": True, "scope": ["REQ-1"]}]
    review = {"artifact": "requirements_analysis", "version": "1.1", "run_id": run_id, "status": "ready_partial", "requirements": requirements, "issues": issues, "frozen_scope": [{"requirement_refs": ["REQ-1"], "issue_refs": ["ISS-1"], "reason": "missing failure behavior"}], "clarifications": [{"id": "CLR-1", "question": "Какой результат и статус должен возвращать Healthchecker при недоступности Prometheus?", "requirement_refs": ["REQ-1"]}]}
    dump(out / "review.json", review)

    tasks = {"artifact": "jira_tasks", "version": "1.1", "mode": "demo", "tasks": [
        {"id": "TASK-1", "summary": "Получать marketplace_api.health из Prometheus", "requirement_refs": ["REQ-1"], "acceptance_criteria": [], "status": "pending_clarification", "clarification_refs": ["CLR-1"]},
        {"id": "TASK-2", "summary": "Опросить Prometheus с интервалом 60 секунд", "requirement_refs": ["REQ-2"], "acceptance_criteria": ["Интервал между опросами составляет 60 секунд"], "status": "ready"},
        {"id": "TASK-3", "summary": "Сохранять последнее успешное значение метрики", "requirement_refs": ["REQ-3"], "acceptance_criteria": ["После успешного опроса доступно последнее значение метрики"], "status": "ready"},
    ], "clarification_requests": review["clarifications"]}
    dump(out / "tasks.json", tasks)

    tests = {"artifact": "test_model", "version": "1.1", "mode": "demo", "scenarios": [
        {"id": "TC-1", "title": "Получение метрики при доступном Prometheus", "type": "positive", "requirement_refs": ["REQ-1"], "status": "blocked_by_clarification"},
        {"id": "TC-2", "title": "Опрос выполняется через 60 секунд", "type": "boundary", "requirement_refs": ["REQ-2"], "status": "ready"},
        {"id": "TC-3", "title": "Сохранение последнего значения после успешного опроса", "type": "positive", "requirement_refs": ["REQ-3"], "status": "ready"},
    ], "coverage_exceptions": [{"requirement_id": "REQ-1", "type": "negative", "reason": "Поведение при ошибке не задано в требованиях"}]}
    dump(out / "test_model.json", tests)

    report = f"""# Demo workflow report\n\n- Run: `{run_id}`\n- Mode: `demo`\n- Final status: `PARTIAL`\n- Requirement review: `ready_partial`\n- Tasks ready for external creation: 2\n- Tasks pending clarification: 1\n- Test scenarios: 3\n- External Jira/Qase writes: 0\n\n## Quality Gates\n\n- QG-1: passed with `ready_partial`; REQ-1 frozen due to missing failure behavior.\n- QG-2: passed for ready tasks; TASK-1 is not ready for creation.\n- QG-3: passed for independent requirements; negative coverage for REQ-1 is explicitly not generated.\n\n## Clarification required\n\nCLR-1: {review['clarifications'][0]['question']}\n\nArtifacts are in this directory. Local MCP data is not Jira or Qase data.\n"""
    (out / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"run_id": run_id, "status": "PARTIAL", "artifacts": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
