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
| Version | 1.0 |
| Validation | QG-1 в agent instruction + Completion Criteria skill |
| Error Handling | Пустой или невалидный артефакт: этапы 4–6 не запускаются; агент повторяет этап анализа (Self-Refine, не более 2 итераций), затем эскалация |

```json
{
  "artifact": "requirements_analysis",
  "version": "1.0",
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
      "blocking": true
    }
  ],
  "risks": [
    {"id": "RSK-1", "description": "риск", "requirement_refs": ["REQ-2"]}
  ]
}
```

---

## 2. jira_tasks

| Элемент | Значение |
|---|---|
| Producer | Agent + Skill `task_design` v1+ |
| Consumer | Jira Tool (создание задач), итоговый отчет, Skill `test_design` (task_refs) |
| Version | 1.0 |
| Validation | QG-2: основание REQ-ID у каждой задачи, проверяемые критерии приемки, дубли проверены |
| Error Handling | Невалидный артефакт — этап не выполняется; несоответствие после частичного создания задач в Jira — остановка и эскалация с перечнем созданных/несозданных |

```json
{
  "artifact": "jira_tasks",
  "version": "1.0",
  "input": {"artifact": "requirements_analysis", "version": "1.0"},
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
      "status": "to_create | created | duplicate_of:KEY"
    }
  ],
  "coverage": [
    {"requirement_id": "REQ-1", "task_ids": ["TASK-1"]}
  ],
  "not_covered": [
    {"requirement_id": "REQ-9", "reason": "unresolved conflict", "issue_ref": "ISS-3"}
  ]
}
```

Поле `created_key` заполняется агентом из фактического ответа Jira после
создания — подтверждение от инструмента, а не из генерации.

---

## 3. test_model

| Элемент | Значение |
|---|---|
| Producer | Agent + Skill `test_design` v1+ |
| Consumer | выбранная TMS (загрузка сценариев), итоговый отчет |
| Version | 1.0 |
| Validation | QG-3: покрытие, типы сценариев, трассировка, отсутствие дублей |
| Error Handling | TMS недоступна — артефакт сохраняется локально, факт фиксируется в отчете; невалидный артефакт — самокоррекция до 2 итераций, затем эскалация |

Формат совместим с полями Qase/TestRail/Allure TestOps/TestIT; при
загрузке конкретная TMS может потребовать маппинга полей, содержимое
артефакта при этом не меняется.

```json
{
  "artifact": "test_model",
  "version": "1.0",
  "input": {"artifact": "requirements_analysis", "version": "1.0"},
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
      "boundary": ["[GAP] граница не задана в требованиях"]
    }
  ],
  "not_covered": [
    {"requirement_id": "REQ-8", "reason": "blocked requirement", "issue_ref": "ISS-2"}
  ],
  "stats": {
    "positive": 12,
    "negative": 7,
    "boundary": 5,
    "requirements_without_negative": ["REQ-6"]
  }
}
```

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
   риск, ссылки REQ/ISS.
4. `Задачи Jira` — TASK-ID → фактический ключ из ответа Jira, либо
   причина, по которой задача не создавалась.
5. `Тестовая модель` — статистика по типам, покрытие critical
   требований, ссылочная карта REQ → TC.
6. `Эскалации и требуемые данные` — что нужно от человека для
   продолжения.
