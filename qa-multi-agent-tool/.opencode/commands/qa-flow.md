---
description: Запускает полный QA workflow через Orchestrator
agent: qa-orchestrator
---

Обработай страницу `healthchecker-full` в проекте `DEMO`. Если страница недоступна, вызови `get_requirements` для `healthchecker-full`, `healthchecker-ready` и `healthchecker-demo`, чтобы увидеть, какие страницы реально отдаёт MCP, и используй первую доступную из них; в отчёте укажи, какая страница реально использовалась.

Выполни полный workflow: получи требования через MCP, вызови Requirement Reviewer, проверь Quality Gate, затем вызови Task Designer и Test Designer. Сохрани артефакты в новом `artifacts/<run-id>/`.

Проверь передачу контекста: в `tasks.md` и `tests.md` должны использоваться те же REQ-ID, что в `review.md`, а требования из `frozen_scope` не должны попадать в готовые результаты.

Создавай локальные demo-записи только если это явно разрешено аргументом пользователя: $ARGUMENTS. В отчёте укажи режим `demo` и не называй локальные записи Jira/Qase.
