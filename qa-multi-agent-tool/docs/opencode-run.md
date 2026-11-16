# Результаты реальных прогонов в OpenCode

## Прогоны /qa-flow (qa-multi-agent-tool)

| Прогон | Страница | Итог | Причина |
|---|---|---|---|
| `20261116-084706` | `healthchecker-demo` | `BLOCKED` | требования слишком куцые, всё заморожено |
| `20261116-090012-healthchecker-demo` | `healthchecker-demo` | `BLOCKED` | OpenCode работал на конфигурации до добавления `healthchecker-full` |
| `20261116-090639` | `healthchecker-full` | `BLOCKED` | в данных был конфликт «набор метрик» ↔ одна метрика и не задан контракт запроса |

Что подтверждено всеми прогонами:

- MCP `qa-local` загружается, требования читаются, `source.md` создаётся с
  временем получения;
- Requirement Reviewer получает исходник и ссылается на него в `review.md`;
- Quality Gate останавливает workflow, если требования недоопределены;
- при `blocked` Task Designer и Test Designer не вызываются, отчёт создаётся.

Третий прогон — полезный negative-тест: агент нашёл конфликт между
«набором метрик `marketplace_api.health`» и единственной
`marketplace_api_health_status`, то есть gate не пропускает противоречивые
требования.

## Изменения по итогам прогонов

- добавлены страницы `healthchecker-full` и `healthchecker-ready`;
- `healthchecker-full` переписан: одна метрика, явный контракт запроса
  (GET `/api/v1/query`, параметр `query`), критерий успеха в теле ответа,
  отсчёт интервала от завершения предыдущего опроса;
- единственный оставленный пробел — поведение при недоступности Prometheus;
  ожидается `ready_partial` с готовыми задачами и черновиками по REQ с пробелом.

## Как проверить позитивный путь

1. Перезапустить OpenCode Desktop (команды и данные читаются при старте).
2. Открыть `qa-multi-agent-tool` и выполнить `/qa-flow`.
3. В `source.md` должна быть страница `healthchecker-full`, в `report.md` —
   `PARTIAL`, готовые задачи и черновики, а в `tasks.md`/`tests.md` — те же
   REQ-ID, что в `review.md`.
