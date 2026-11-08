
"""HTTP contract for the independent learning workspace."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.workbench_security import require_owner
from app.schemas.workbench import AnswerRequest, DiagnosisRequest
from app.services import workbench_learning as learning
from app.services.workbench_analysis import analyze

router = APIRouter(prefix="/api")
Owner = Annotated[str, Depends(require_owner)]
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/diagnoses")
async def diagnose(payload: DiagnosisRequest, owner: Owner, db: DB):
    request_id = str(payload.request_id)
    fingerprint = learning.digest(f"{payload.language}\n{payload.code}")
    previous = await learning.read_diagnosis(db, owner, request_id, fingerprint)
    if previous is not None:
        return previous
    status, evidence = analyze(payload.code, payload.language)
    challenge = None
    if status == "confirmed":
        challenge = await learning.plan_initial(db, owner, evidence[0]["knowledge_id"])
    result = {"id": request_id, "status": status, "evidence": evidence, "mode": "local",
              "challenge": learning.challenge_view(challenge) if challenge else None}
    return await learning.save_diagnosis(db, owner, request_id, fingerprint, result, challenge)


@router.get("/profile")
async def profile(owner: Owner, db: DB):
    return await learning.profile(db, owner)


@router.post("/challenges/{challenge_id}/hint")
async def hint(challenge_id: UUID, owner: Owner, db: DB):
    challenge = await learning.owned_challenge(db, owner, str(challenge_id))
    return await learning.reveal_hint(db, challenge)


@router.post("/challenges/{challenge_id}/answer")
async def answer(challenge_id: UUID, payload: AnswerRequest, owner: Owner, db: DB):
    challenge = await learning.owned_challenge(db, owner, str(challenge_id))
    return await learning.grade(db, challenge, str(payload.attempt_id), payload.answer)


@router.post("/challenges/{challenge_id}/retry")
async def retry(challenge_id: UUID, owner: Owner, db: DB):
    challenge = await learning.owned_challenge(db, owner, str(challenge_id))
    return await learning.retry(db, challenge)
