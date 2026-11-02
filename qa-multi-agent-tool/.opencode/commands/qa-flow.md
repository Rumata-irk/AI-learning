---
description: Запускает полный QA workflow через Orchestrator
agent: qa-orchestrator
---

Обработай страницу `healthchecker-demo` в проекте `DEMO`. Выполни полный workflow: получи требования через MCP, вызови Requirement Reviewer, проверь Quality Gate, затем вызови Task Designer и Test Designer. Сохрани артефакты в новом `artifacts/<run-id>/`. Создавай локальные demo-записи только если это явно разрешено аргументом пользователя: $ARGUMENTS. В отчёте укажи режим `demo` и не называй локальные записи Jira/Qase.
