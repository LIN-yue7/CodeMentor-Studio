
"""Orchestrate local evidence, course retrieval, and optional model coaching."""

from time import perf_counter

from app.services.workbench_analysis import analyze
from app.services.workbench_knowledge import retrieve
from app.services.workbench_tutor import Tutor


async def evaluate(code: str, language: str, owner: str, tutor: Tutor, *,
                   with_retrieval: bool = True, learning=None) -> dict:
    started = perf_counter()
    events: list[dict] = []

    def event(stage: str, status: str) -> None:
        events.append({"stage": stage, "status": status,
                       "elapsed_ms": round((perf_counter() - started) * 1000, 2)})

    status, evidence = analyze(code, language)
    event("analysis", status)
    cards = []
    annotation = None
    model_status = "skipped"
    if status == "confirmed":
        knowledge_id = evidence[0]["knowledge_id"]
        if with_retrieval:
            cards = retrieve(knowledge_id)
            event("retrieval", "matched" if cards else "empty")
        context = await learning(knowledge_id) if learning is not None else None
        model_status, annotation = await tutor.explain(owner=owner, code=code, evidence=evidence[0],
                                                      cards=cards, learning=context)
        event("model", model_status)
    return {"status": status, "evidence": evidence, "cards": cards, "annotation": annotation,
            "model_status": model_status, "mode": tutor.mode, "events": events}
