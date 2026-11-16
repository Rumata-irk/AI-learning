# AI-learning

Практические проекты по QA-автоматизации с AI-агентами: от отдельных
промптов и skills до мультиагентных систем с оценкой качества.

## Проекты

### `qa-requirements-agent`

Инструкция агента и три skill для работы с требованиями: анализ
требований, проектирование задач, тест-дизайн. Контракты артефактов и
правила продолжения при проблемных требованиях описаны в самом проекте.

### `qa-multi-agent-tool`

Мультиагентный workflow в OpenCode: `qa-orchestrator`, `requirement-reviewer`,
`task-designer`, `test-designer`. Разделены результаты, готовые к записи, и
черновики по замороженным требованиям; есть локальный MCP-сервер с
идемпотентностью, восстановлением после частичного сбоя и offline demo.

```powershell
cd qa-multi-agent-tool
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
opencode   # команда /qa-flow
```

### `qa-coursework-agent`

Полный курс: три внешние системы через MCP (Confluence read-only, Jira и
TMS с записью), три специализированных агента, оркестратор с Quality Gate,
guardrails против prompt injection, golden dataset из шести eval-кейсов и
автоматический прогон с pass rate. LLM-as-a-Judge включается флагом `--llm`.

```powershell
cd qa-coursework-agent
python -m pip install -r requirements.txt
python eval/eval_runner.py          # детерминированная оценка
python -m unittest discover -s tests -v
opencode   # команда /run-coursework-flow
```

## Как это устроено

- **Агент ≠ Skill ≠ Tool.** Агент принимает решения, skill содержит
  профессиональную логику, tool выполняет действие во внешней системе.
- **Артефакты вместо истории диалога.** Этапы передают друг другу
  проверенные файлы, а не пересказ.
- **Quality Gates.** Нельзя перейти к следующему этапу или создать записи
  во внешней системе, если требования имеют блокирующие проблемы.
- **Черновики отделены от готового.** Записи создаются только из готовых
  массивов артефактов.
- **Оценка агентов.** Golden dataset + evaluator + pass rate как метрика
  качества системы.
