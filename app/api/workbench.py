
"""HTTP contract for the independent learning workspace."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.workbench_security import require_owner
from app.schemas.workbench import AnswerRequest, DiagnosisRequest, HintRequest, ReflectionRequest, SelfCheckRequest
from app.services import workbench_learning as learning
from app.services.workbench_diagnosis import evaluate
from app.services import workbench_reflection as reflection
from app.services import workbench_selfcheck as selfcheck

router = APIRouter(prefix="/api")
Owner = Annotated[str, Depends(require_owner)]
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/capabilities")
async def capabilities(request: Request):
    return {"mode": request.app.state.tutor.mode, "tool_calling": False}


@router.post("/diagnoses")
async def diagnose(payload: DiagnosisRequest, request: Request, owner: Owner, db: DB):
    request_id = str(payload.request_id)
    fingerprint = learning.digest(f"{payload.language}\n{payload.goal}\n{payload.code}")
    lock = request.app.state.diagnosis_locks[hash((owner, request_id)) % 32]
    async with lock:
        previous = await learning.read_diagnosis(db, owner, request_id, fingerprint)
        if previous is not None:
            return previous

        async def learning_context(knowledge_id: str):
            rows = await learning.history(db, owner, knowledge_id)
            return {status: sum(row.outcome == status for row in rows)
                    for status in ("independent", "assisted", "incorrect")}

        result = await evaluate(payload.code, payload.language, owner, request.app.state.tutor,
                                goal=payload.goal, learning=learning_context)
        result["coaching"] = await reflection.coaching(db, owner, result)
        challenge = None
        if result["status"] == "confirmed":
            challenge = await learning.plan_initial(db, owner, result["evidence"][0]["knowledge_id"])
            result["events"].append({"stage": "practice", "status": "selected"})
        result.update(id=request_id, challenge=learning.challenge_view(challenge) if challenge else None)
        return await learning.save_diagnosis(db, owner, request_id, fingerprint, result, challenge)

@router.get("/profile")
async def profile(owner: Owner, db: DB):
    return await learning.profile(db, owner)


@router.post("/challenges/{challenge_id}/hint")
async def hint(challenge_id: UUID, payload: HintRequest, owner: Owner, db: DB):
    challenge = await learning.owned_challenge(db, owner, str(challenge_id))
    return await learning.reveal_hint(db, challenge, payload.tier)


@router.post("/challenges/{challenge_id}/answer")
async def answer(challenge_id: UUID, payload: AnswerRequest, owner: Owner, db: DB):
    challenge = await learning.owned_challenge(db, owner, str(challenge_id))
    return await learning.grade(db, challenge, str(payload.attempt_id), payload.answer)


@router.post("/challenges/{challenge_id}/retry")
async def retry(challenge_id: UUID, owner: Owner, db: DB):
    challenge = await learning.owned_challenge(db, owner, str(challenge_id))
    return await learning.retry(db, challenge)


@router.get('/learning-memory')
async def learning_memory(owner: Owner, db: DB):
    return {'items': await reflection.memories(db, owner)}

@router.post('/diagnoses/{diagnosis_id}/reflection')
async def reflect(diagnosis_id: UUID, payload: ReflectionRequest, request: Request, owner: Owner, db: DB):
    async with request.app.state.diagnosis_locks[hash((owner, str(diagnosis_id))) % 32]:
        return await reflection.save_reflection(db, owner, str(diagnosis_id), payload)

@router.post('/diagnoses/{diagnosis_id}/reflection/forget')
async def forget_reflection(diagnosis_id: UUID, request: Request, owner: Owner, db: DB):
    async with request.app.state.diagnosis_locks[hash((owner, str(diagnosis_id))) % 32]:
        return await reflection.save_reflection(db, owner, str(diagnosis_id), None)


@router.get('/diagnoses/{diagnosis_id}/self-check')
async def self_check_question(diagnosis_id: UUID, owner: Owner, db: DB):
    return await selfcheck.question(db, owner, str(diagnosis_id))

@router.post('/diagnoses/{diagnosis_id}/self-check')
async def self_check_answer(diagnosis_id: UUID, payload: SelfCheckRequest, request: Request, owner: Owner, db: DB):
    async with request.app.state.diagnosis_locks[hash((owner, str(diagnosis_id))) % 32]:
        return await selfcheck.grade(db, owner, str(diagnosis_id), payload.choice)
