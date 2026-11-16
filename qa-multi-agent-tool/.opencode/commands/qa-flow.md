---
description: Запускает полный QA workflow через Orchestrator
agent: qa-orchestrator
---

Обработай страницу `healthchecker-full` в проекте `DEMO`. Выполни полный workflow: получи требования через MCP, вызови Requirement Reviewer, проверь Quality Gate, затем вызови Task Designer и Test Designer. Сохрани артефакты в новом `artifacts/<run-id>/`.

Проверь передачу контекста: в `tasks.md` и `tests.md` должны использоваться те же REQ-ID, что в `review.md`, а требования из `frozen_scope` не должны попадать в готовые результаты.

Создавай локальные demo-записи только если это явно разрешено аргументом пользователя: $ARGUMENTS. В отчёте укажи режим `demo` и не называй локальные записи Jira/Qase.
