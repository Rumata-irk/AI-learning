# Artifact Contracts

Контракты описывают артефакты, которыми обмениваются этапы флоу.
Элементы контракта — Producer, Consumer, Schema, Version, Validation,
Error Handling. Общее правило: следующий этап получает конкретный
проверенный артефакт, а не историю диалога предыдущего этапа.

Хранение: файлы `requirements_analysis.json`, `jira_tasks.json`,
`test_model.json`, `final_report.md` в каталоге `artifacts_path`
конкретного run'а. Повторный запуск этапа не переписывает предыдущую
версию, а создает артефакт с увеличенным `version`.

---

## 1. requirements_analysis

| Элемент | Значение |
|---|---|
| Producer | Agent + Skill `requirement_review` v1+ |
| Consumer | Skill `task_design`, Skill `test_design`, человек при эскалации |
| Version | 1.1 |
| Validation | QG-1 в agent instruction + Completion Criteria skill |
| Error Handling | Пустой или невалидный артефакт: этапы 4–6 не запускаются; агент повторяет этап анализа (Self-Refine, не более 2 итераций), затем эскалация |

```json
{
  "artifact": "requirements_analysis",
  "version": "1.1",
  "source": {"system": "confluence", "page": "<id или url>"},
  "status": "ready | ready_partial | blocked",
  "requirements": [
    {
      "id": "REQ-1",
      "text": "формулировка требования",
      "type": "functional | business_rule | constraint | non_functional",
      "evidence": "цитата из источника",
      "criticality": "high | medium | low"
    }
  ],
  "acceptance_criteria": [
    {"id": "AC-1", "requirement_ref": "REQ-1", "criterion": "формулировка из источника"}
  ],
  "dependencies": [
    {"from": "REQ-1", "to": "REQ-2 | внешняя система", "kind": "requirement | integration"}
  ],
  "issues": [
    {
      "id": "ISS-1",
      "kind": "ambiguity | conflict | gap | assumption",
      "requirement_refs": ["REQ-1"],
      "description": "что зафиксировано",
      "evidence": ["цитата 1", "цитата 2 — для conflict обязательны обе"],
      "blocking": true,
      "scope": ["REQ-1", "REQ-4"]
    }
  ],
  "frozen_scope": [
    {
      "requirement_refs": ["REQ-1", "REQ-4"],
      "issue_refs": ["ISS-1"],
      "reason": "unresolved conflict"
    }
  ],
  "risks": [
    {"id": "RSK-1", "description": "риск", "requirement_refs": ["REQ-2"]}
  ]
}
```

Значение полей:

- `issues[].blocking` — влияет ли проблема на проектирование. `true` — область
  замораживается, `false` — вопрос выносится в отчет, работа продолжается.
- `issues[].scope` — требования, которых касается проблема: по ним
  проектирование не ведется.
- `frozen_scope` — объединенный перечень замороженных областей. Поля
  `requirement_refs` и `issue_refs` обязательны, `reason` — краткое
  основание.

Статус артефакта выводится из `frozen_scope` по единому правилу:

| Условие | `status` | Поведение флоу |
|---|---|---|
| Нет проблем с `blocking: true` | `ready` | проектирование ведется по всем требованиям |
| Есть `blocking: true`, и `frozen_scope` не покрывает требования, от которых зависят остальные | `ready_partial` | проектирование ведется по незамороженной части, замороженная область уходит в эскалацию |
| `frozen_scope` покрывает всю область либо затрагивает требования, от которых зависят остальные | `blocked` | проектирование не начинается, эскалация |

Решение «продолжать ли по незамороженной части» принимает агент по этой
таблице и не требует решения человека. Решение о трактовке
противоречия всегда принимает человек и передается через эскалацию —
агент трактовку не выбирает.

---

## 2. jira_tasks

| Элемент | Значение |
|---|---|
| Producer | Agent + Skill `task_design` v1+ |
| Consumer | Jira Tool (создание задач), итоговый отчет, Skill `test_design` (task_refs) |
| Version | 1.1 |
| Validation | QG-2: основание REQ-ID у каждой задачи, проверяемые критерии приемки, дубли проверены |
| Error Handling | Невалидный артефакт — этап не выполняется; несоответствие после частичного создания задач в Jira — остановка и эскалация с перечнем созданных/несозданных |

```json
{
  "artifact": "jira_tasks",
  "version": "1.1",
  "input": {"artifact": "requirements_analysis", "version": "1.1"},
  "project_key": "<context: jira_project>",
  "tasks": [
    {
      "id": "TASK-1",
      "created_key": null,
      "summary": "Реализовать ...",
      "goal": "зачем, ссылкой на REQ",
      "description": "поведение, подтвержденное требованиями",
      "acceptance_criteria": [
        {"criterion": "проверяемый пункт", "requirement_ref": "REQ-1"}
      ],
      "priority": "highest | high | medium | low",
      "dependencies": ["TASK-2"],
      "requirement_refs": ["REQ-1", "REQ-3"],
      "status": "to_create | created | duplicate_of:KEY | pending_clarification"
    }
  ],
  "coverage": [
    {"requirement_id": "REQ-1", "task_ids": ["TASK-1"]}
  ],
  "not_covered": [
    {"requirement_id": "REQ-9", "reason": "unresolved conflict", "issue_ref": "ISS-3"}
  ],
  "clarification_requests": [
    {
      "id": "CLR-1",
      "requirement_refs": ["REQ-4"],
      "question": "какой результат считать выполнением задачи",
      "blocks": ["TASK-2"]
    }
  ]
}
```

Поле `created_key` заполняется агентом из фактического ответа Jira после
создания — подтверждение от инструмента, а не из генерации.

Ограничения схемы:

- `acceptance_criteria` не может содержать подмену критерия ссылкой на
  требование («соответствует REQ-1»): если конкретный критерий в
  требованиях не задан, у задачи пустой `acceptance_criteria`, статус
  `pending_clarification` и запись в `clarification_requests`. Такая
  задача в Jira не создается.
- `clarification_requests[].question` — конкретный вопрос, а не
  «уточнить требования»; `blocks` указывает, что именно заблокировано
  (ID задачи, REQ-ID или область тестирования).

---

## 3. test_model

| Элемент | Значение |
|---|---|
| Producer | Agent + Skill `test_design` v1+ |
| Consumer | выбранная TMS (загрузка сценариев), итоговый отчет |
| Version | 1.1 |
| Validation | QG-3: покрытие, типы сценариев, трассировка, отсутствие дублей |
| Error Handling | TMS недоступна — артефакт сохраняется локально, факт фиксируется в отчете; невалидный артефакт — самокоррекция до 2 итераций, затем эскалация |

Формат совместим с полями Qase/TestRail/Allure TestOps/TestIT; при
загрузке конкретная TMS может потребовать маппинга полей, содержимое
артефакта при этом не меняется.

```json
{
  "artifact": "test_model",
  "version": "1.1",
  "input": {"artifact": "requirements_analysis", "version": "1.1"},
  "tms_project": "<context: tms_project>",
  "scenarios": [
    {
      "id": "TC-1",
      "created_id": null,
      "title": "что и при каком условии проверяется",
      "type": "positive | negative | boundary",
      "precondition": "состояние системы до шагов",
      "steps": [
        {"no": 1, "action": "атомарное действие", "data": "тестовые данные"}
      ],
      "expected_result": "единственный проверяемый факт",
      "priority": "P1 | P2 | P3",
      "requirement_refs": ["REQ-1"],
      "task_refs": ["TASK-1"],
      "automation": "yes | no | partial"
    }
  ],
  "coverage_matrix": [
    {
      "requirement_id": "REQ-1",
      "positive": ["TC-1"],
      "negative": ["TC-4"],
      "boundary": ["not_applicable: границы в требованиях не заданы"]
    }
  ],
  "not_covered": [
    {"requirement_id": "REQ-8", "reason": "blocked requirement", "issue_ref": "ISS-2"}
  ],
  "stats": {
    "positive": 12,
    "negative": 7,
    "boundary": 5,
    "requirements_without_negative": [
      {"requirement_id": "REQ-6", "reason": "not_applicable: условие нарушения не задано"}
    ]
  }
}
```

Значения ячеек матрицы:

- список ID сценариев — тип покрыт;
- `not_applicable: <обоснование>` — тип к требованию неприменим
  (нет условия нарушения или границ в требованиях); это обоснованное
  решение, а не пробел покрытия, сценарий ради заполнения ячейки не
  создается;
- `[GAP]: <что именно не задано>` — проверка предполагалась, но данных в
  требованиях нет; значение выносится в отчет как запрос уточнения.

---

## 4. final_report

| Элемент | Значение |
|---|---|
| Producer | Agent (этап 7) |
| Consumer | человек / команда |
| Version | 1.0 |
| Validation | содержит статусы всех этапов, ID созданных сущностей из ответов инструментов, все эскалации |
| Error Handling | формируется даже при остановке флоу — с отмеченными незавершенными этапами |

markdown-структура обязательных разделов:

1. `Итог` — общий статус run: complete / partial / stopped + причины.
2. `Этапы` — таблица: этап, skill и версия, gate, статус.
3. `Найденные проблемы` — ambiguity / conflict / gap / assumption,
   риск, ссылки REQ/ISS; отдельно замороженная область (`frozen_scope`)
   и статус анализа (`ready` / `ready_partial` / `blocked`).
4. `Задачи Jira` — TASK-ID → фактический ключ из ответа Jira, либо
   причина, по которой задача не создавалась (дубль, `pending_clarification`);
   список запросов уточнения `clarification_requests` с конкретными
   вопросами.
5. `Тестовая модель` — статистика по типам, покрытие critical
   требований, ссылочная карта REQ → TC, обоснования `not_applicable`
   по типам проверок.
6. `Эскалации и требуемые данные` — что нужно от человека для
   продолжения; по замороженной области — конкретный вопрос и
   перечень REQ-ID.
