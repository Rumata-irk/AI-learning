# QA Coursework Agent

Мультиагентная система на OpenCode: получает требования из Confluence,
проводит ревью с Quality Gate, создаёт задачи в Jira и тест-кейсы в TMS.
Защищена от prompt injection и от записи при блокирующих проблемах.

## Состав

```
qa-coursework-agent/
├── opencode.json              MCP: confluence (read), jira (write), tms (write)
├── AGENTS.md                  правила проекта и доверия к данным
├── .opencode/
│   ├── agents/                qa-orchestrator, requirement-reviewer, task-manager, test-designer
│   ├── skills/                requirement-review, task-management, test-design
│   └── commands/              run-coursework-flow
├── mcp/
│   ├── confluence/server.py   read-only источник требований
│   ├── jira/server.py         запись задач, идемпотентность
│   ├── tms/server.py          запись тест-кейсов, идемпотентность
│   └── common.py              общая логика записи
├── guardrails/guard.py        проверки безопасности и готовности
├── pipeline.py                детерминированный движок флоу
├── data/confluence_pages.json демонстрационные требования
├── eval/
│   ├── golden_dataset.json    6 кейсов: golden, ambiguity, contradiction, critical, injection, boundary
│   ├── evaluator.py           оценка: детерминированная или LLM-as-a-Judge
│   ├── eval_runner.py         прогон, метрики, Quality Gate, отчёт
│   └── results/               eval_results.json и report.md
└── artifacts/                 результаты запусков
```

## Запуск в OpenCode

```powershell
python -m pip install -r requirements.txt
opencode
```

Команда: `/run-coursework-flow`. По умолчанию используется страница `HC-101`.
Агенты, skills и `opencode.json` применяются после перезапуска OpenCode.

## Оценка агентов (eval)

```powershell
python eval/eval_runner.py          # детерминированная оценка
python eval/eval_runner.py --llm    # LLM-as-a-Judge (нужен QA_JUDGE_API_KEY)
```

Результат: `eval/results/report.md` с pass rate и таблицей кейсов.
Quality Gate eval проходит только при pass rate = 1.0.

Golden dataset покрывает:

| ID | Категория | Что проверяется |
|---|---|---|
| EVAL-001 | golden | штатный флоу: ready, задачи и тесты создаются |
| EVAL-002 | ambiguity | поведение при отказе не задано → блокер и заморозка |
| EVAL-003 | contradiction | два интервала опроса → конфликт и вопрос человеку |
| EVAL-004 | critical | неопределённый резервный источник → частичная готовность |
| EVAL-005 | injection | инструкция внутри требований → security-блокер, запись запрещена |
| EVAL-006 | boundary | границы 60 с и 5 с, неопределённое число повторов |

## Guardrails

- **Prompt injection**: инструкции внутри требований считаются данными.
  Найденная попытка изменить правила даёт `security`-блокер и запрет записи.
- **Запрет записи при блокерах**: при наличии `blocking`-проблем или
  непустого `frozen_scope` запись в Jira/TMS не выполняется.
- **Разделение готовых и черновиков**: создаются только элементы массивов
  `tasks` и `scenarios`; `drafts` всегда исключены.
- **Идемпотентность и восстановление**: повторный вызов с тем же внешним
  ключом возвращает существующую запись. `QA_FAIL_AFTER=N` воспроизводит
  частичный сбой, после которого прогон продолжается без дублей.
- **Секреты**: хранятся в переменных окружения, в артефакты и логи не попадают.

## Ограничения

Внешние системы заменены локальными MCP-серверами с той же структурой
вызовов (чтение/запись, внешний ключ, ошибки). Чтобы подключить реальные
сервисы, замените команды `mcp/*` на MCP-серверы Confluence, Jira и Qase и
передайте токены через переменные окружения.

## Проверка

```powershell
python -m unittest discover -s tests -v
python eval/eval_runner.py
```
