
"""Reproducible A/B/C benchmark. Offline runs never access a model provider."""

import argparse
import asyncio
import json
import os
from collections import Counter
from pathlib import Path
from time import perf_counter

from app.agents.tutor_agent import TutorAgent
from app.core.config import get_settings
from app.core.llm_client import LLMError, close_llm_clients, get_llm_client
from app.services.workbench_analysis import analyze
from app.services.workbench_curriculum import CURRICULUM
from app.services.workbench_diagnosis import evaluate
from app.services.workbench_tutor import Tutor

ROOT = Path(__file__).resolve().parents[1]
OLD_TAGS = {
    "loop-boundary": ("循环边界", "循环范围", "off-by-one"),
    "empty-list": ("空列表", "空序列", "索引越界"),
    "accumulator": ("累加", "初始化位置"),
}


def load_cases() -> list[dict]:
    return json.loads((ROOT / "evaluation/cases.json").read_text(encoding="utf-8-sig"))


async def legacy(case: dict, agent: TutorAgent) -> dict:
    async with asyncio.timeout(12):
        result = await agent.diagnose(case["code"], filename=f"{case['id']}.txt", language=case["language"])
    if not result.parsed:
        return {"status": "unavailable", "mode": "live", "raw": None}
    analysis = result.payload["analysis"]
    points = " ".join(analysis["knowledge_points"]).lower()
    recognized = next((key for key, tags in OLD_TAGS.items() if any(tag in points for tag in tags)), None)
    status = "clear" if analysis["status"] == "success" else "confirmed"
    return {"status": status, "mode": "live", "raw": result.payload,
            "evidence": [{"knowledge_id": recognized, "line": None}] if status == "confirmed" else []}


def summarize(rows: list[dict], variant: str) -> dict:
    selected = [row for row in rows if row["variant"] == variant]
    if not selected:
        return {"status": "not-run"}
    eligible = [row for row in selected if row["expected_status"] == "confirmed"]
    clean = [row for row in selected if row["expected_status"] == "clear"]
    positive = [row for row in selected if row["status"] == "confirmed"]
    locations = [row for row in selected if row["expected_line"] is not None]
    citation_count = sum(len(row.get("annotation", {}).get("citations", []))
                         for row in selected if row.get("annotation"))
    retrieval_targets = [row for row in selected if row["expected_source"]]
    times = sorted(row["duration_ms"] for row in selected)
    return {"status": "measured", "cases": len(selected), "mode": selected[0]["mode"],
            "model_accepted": sum(row.get("model_status") == "accepted" for row in selected),
            "confirmed": len(positive), "supported_faults": len(eligible),
            "concept_matches": sum(row["actual_concept"] == row["expected_concept"] for row in eligible),
            "line_targets": len(locations), "line_matches": sum(row["actual_line"] == row["expected_line"]
                                                                 for row in locations),
            "clean_cases": len(clean), "clean_false_positive": sum(row["status"] == "confirmed" for row in clean),
            "abstentions": sum(row["status"] == "uncertain" for row in selected),
            "unavailable": sum(row["status"] == "unavailable" for row in selected),
            "retrieval_targets": len(retrieval_targets),
            "retrieval_expected_hit": sum(row["expected_source"] in [card["id"] for card in row.get("cards", [])]
                                          for row in retrieval_targets),
            "citations_present": citation_count,
            "p50_ms": times[len(times) // 2], "p95_ms": times[max(0, (95 * len(times) + 99) // 100 - 1)]}


async def run(cases: list[dict], *, live: bool) -> dict:
    if live and not get_settings().llm.is_configured:
        raise RuntimeError("请先配置经授权的模型服务，再执行真实评测。")
    model = get_llm_client() if live else None
    baseline = TutorAgent(model) if model else None
    tutors = {variant: Tutor(live=live) for variant in ("B", "C")}
    if live:
        for tutor in tutors.values():
            # Fixed fixture count and one shared owner for the fair single run.
            tutor.daily_limit = min(12, len(cases))
    rows = []
    try:
        for case in cases:
            for variant in ("A", "B", "C"):
                if variant == "A" and baseline is None:
                    continue
                started = perf_counter()
                try:
                    if variant == "A":
                        result = await legacy(case, baseline)
                    else:
                        result = await evaluate(case["code"], case["language"], "evaluation", tutors[variant],
                                                with_retrieval=variant == "C", goal=case["goal"])
                except (TimeoutError, LLMError, OSError, ValueError) as exc:
                    result = {"status": "unavailable", "mode": "live", "failure": type(exc).__name__}
                evidence = (result.get("evidence") or [{}])[0]
                rows.append({**result, "case": case["id"], "variant": variant,
                             "duration_ms": round((perf_counter() - started) * 1000, 3),
                             "expected_status": case["status"], "expected_concept": case["concept"],
                             "expected_line": case["line"], "expected_source": case["source"],
                             "actual_concept": evidence.get("knowledge_id"), "actual_line": evidence.get("line")})
    finally:
        if live:
            await close_llm_clients()

    exercises = [item for items in CURRICULUM.values() for item in items]
    return {"mode": "live" if live else "offline-local", "case_count": len(cases),
            "dataset_distribution": dict(Counter(case["status"] for case in cases)),
            "summary": {variant: summarize(rows, variant) for variant in ("A", "B", "C")},
            "exercise_review": {"templates": len(exercises),
                                "complete": sum(bool(item.answer and all(item.hints) and item.explanation)
                                                for item in exercises),
                                "method": "结构完整性检查。内容复核和学习成效另计。"},
            "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly call the configured provider on synthetic inputs")
    parser.add_argument("--max-provider-calls", type=int, help="Approved maximum number of provider calls")
    parser.add_argument("--limit", type=int, help="Use only the first N fixtures for a smoke test")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/offline-results.json")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.live and args.output == ROOT / "evaluation/offline-results.json":
        parser.error("--live requires a separate --output file")
    cases = load_cases()[:args.limit]
    if args.live:
        matched = sum(analyze(case["code"], case["language"], case["goal"])[0] == "confirmed"
                      for case in cases)
        upper_bound = len(cases) + 2 * matched
        if args.max_provider_calls is None or upper_bound > args.max_provider_calls:
            parser.error(f"this run can call the provider {upper_bound} times; set an approved cap")
        os.environ["LLM__MAX_RETRIES"] = "0"
        get_settings.cache_clear()
    report = asyncio.run(run(cases, live=args.live))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
