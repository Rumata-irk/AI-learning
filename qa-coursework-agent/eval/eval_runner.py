"""Eval runner: loads the golden dataset, runs the pipeline, scores results.

Usage:
    python eval/eval_runner.py            # deterministic judge
    python eval/eval_runner.py --llm      # LLM-as-a-Judge
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pipeline  # noqa: E402
from eval import evaluator  # noqa: E402

DATASET = ROOT / "eval" / "golden_dataset.json"
RESULTS = ROOT / "eval" / "results"
PASS_THRESHOLD = 1.0


def load_cases() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))["cases"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="использовать LLM-as-a-Judge")
    args = parser.parse_args()

    cases = load_cases()
    results = []
    for case in cases:
        try:
            run = pipeline.run(case["page_id"], mode=case.get("mode", "design"))
            outcome = evaluator.evaluate(case, run, use_llm=args.llm)
        except Exception as exc:  # noqa: BLE001
            outcome = {"case_id": case["id"], "name": case["name"], "category": case["category"],
                       "passed": False, "score": 0.0, "reasons": [f"ошибка выполнения: {exc}"],
                       "facts": {}, "judge": "llm" if args.llm else "deterministic"}
        results.append(outcome)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pass_rate = round(passed / total, 4) if total else 0.0
    gate_passed = pass_rate >= PASS_THRESHOLD

    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {"pass_rate": pass_rate, "passed": passed, "total": total,
               "quality_gate": "PASSED" if gate_passed else "FAILED",
               "judge": "llm" if args.llm else "deterministic", "results": results}
    (RESULTS / "eval_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "report.md").write_text(render_report(payload), encoding="utf-8")

    print(json.dumps({"pass_rate": pass_rate, "gate": payload["quality_gate"], "judge": payload["judge"]}, ensure_ascii=False))
    return 0 if gate_passed else 1


def render_report(payload: dict) -> str:
    lines = [
        "# Eval report",
        "",
        f"- Кейсов: {payload['total']}",
        f"- Пройдено: {payload['passed']}",
        f"- Pass rate: {payload['pass_rate']}",
        f"- Quality Gate: {payload['quality_gate']}",
        f"- Judge: {payload['judge']}",
        "",
        "| Кейс | Категория | Результат | Причины |",
        "|---|---|---|---|",
    ]
    for r in payload["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        reasons = "; ".join(r["reasons"]) or "—"
        lines.append(f"| {r['case_id']} {r['name']} | {r['category']} | {status} | {reasons} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
