"""Generate the sample artifact run for the coursework project."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pipeline  # noqa: E402


def main():
    out = ROOT / "artifacts" / "sample-run"
    out.mkdir(parents=True, exist_ok=True)
    page = pipeline.load_page("HC-101")
    (out / "source.md").write_text(
        f"# Requirements\n\n- Page: `HC-101`\n- Title: {page['title']}\n\n{page['body']}\n",
        encoding="utf-8",
    )
    run = pipeline.run("HC-101", mode="design")
    (out / "review.json").write_text(json.dumps(run.requirements, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "tasks.json").write_text(json.dumps(run.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "tests.json").write_text(json.dumps(run.tests, ensure_ascii=False, indent=2), encoding="utf-8")

    blocked = pipeline.run("HC-105", mode="write")
    report = f"""# Sample run report

- Page: `HC-101` (clean requirements)
- Status: `{run.requirements['status']}`
- Ready tasks: {len(run.tasks['tasks'])}
- Draft tasks: {len(run.tasks['drafts'])}
- Ready scenarios: {len(run.tests['scenarios'])}
- Draft scenarios: {len(run.tests['drafts'])}

## Quality Gate

`ready` — блокирующих проблем нет, запись разрешена.

## Guardrail check on an injected page

- Page: `HC-105`
- Requirements status: `{blocked.requirements['status']}`
- Write blocked: `{blocked.blocked_write}`
- Security issues: {[i['id'] for i in blocked.requirements['issues'] if i['kind'] == 'security']}

Инструкция внутри требований зафиксирована как security-проблема, записи не создавались.
"""
    (out / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": run.requirements["status"], "path": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
