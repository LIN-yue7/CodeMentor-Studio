
"""Persistence and deterministic teaching decisions for the workbench."""

import hashlib
from collections import Counter
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workbench import Attempt, Challenge, Diagnosis
from app.services.workbench_curriculum import CURRICULUM, EXERCISES, LABELS


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_challenge(owner: str, knowledge_id: str, index: int, challenge_id: str | None = None) -> Challenge:
    template = CURRICULUM[knowledge_id][index % len(CURRICULUM[knowledge_id])]
    return Challenge(id=challenge_id or str(uuid4()), owner=owner, knowledge_id=knowledge_id,
                     template_id=template.id, hints_used=0, closed=False)


def challenge_view(challenge: Challenge) -> dict:
    template = EXERCISES[challenge.template_id]
    return {"id": challenge.id, "knowledge_id": challenge.knowledge_id, "template_id": template.id,
            "title": template.title, "prompt": template.prompt, "hint_count": len(template.hints)}


async def owned_challenge(db: AsyncSession, owner: str, challenge_id: str) -> Challenge:
    row = await db.get(Challenge, challenge_id)
    if row is None or row.owner != owner:
        raise HTTPException(404, "找不到该练习。")
    return row


async def history(db: AsyncSession, owner: str, knowledge_id: str | None = None) -> list:
    query = select(Challenge.knowledge_id, Challenge.template_id, Attempt.outcome).join(Attempt).where(
        Challenge.owner == owner
    )
    if knowledge_id is not None:
        query = query.where(Challenge.knowledge_id == knowledge_id)
    return list((await db.execute(query)).all())


async def profile(db: AsyncSession, owner: str) -> dict:
    attempts = await history(db, owner)
    concepts = list((await db.scalars(select(Diagnosis.knowledge_id).where(
        Diagnosis.owner == owner, Diagnosis.knowledge_id.is_not(None)
    ))).all())
    diagnosis_counts = Counter(concepts)
    skills = []
    for knowledge_id in CURRICULUM:
        matching = [row for row in attempts if row.knowledge_id == knowledge_id]
        if not matching and knowledge_id not in diagnosis_counts:
            continue
        counts = Counter(row.outcome for row in matching)
        independent_templates = {row.template_id for row in matching if row.outcome == "independent"}
        skills.append({"knowledge_id": knowledge_id, "label": LABELS[knowledge_id],
                       "diagnoses": diagnosis_counts[knowledge_id], "independent": counts["independent"],
                       "assisted": counts["assisted"], "incorrect": counts["incorrect"],
                       "distinct_independent": len(independent_templates)})
    return {"skills": skills}


async def plan_initial(db: AsyncSession, owner: str, knowledge_id: str) -> Challenge:
    attempts = await history(db, owner, knowledge_id)
    completed = {row.template_id for row in attempts if row.outcome == "independent"}
    templates = CURRICULUM[knowledge_id]
    index = next((i for i, item in enumerate(templates) if item.id not in completed), 0)
    return new_challenge(owner, knowledge_id, index)


async def save_diagnosis(db: AsyncSession, owner: str, request_id: str, fingerprint: str,
                         result: dict, challenge: Challenge | None) -> dict:
    db.add(Diagnosis(owner=owner, id=request_id, fingerprint=fingerprint,
                     knowledge_id=challenge.knowledge_id if challenge else None, result=result))
    if challenge:
        db.add(challenge)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        previous = await read_diagnosis(db, owner, request_id, fingerprint)
        if previous is None:
            raise
        return previous
    return result


async def read_diagnosis(db: AsyncSession, owner: str, request_id: str, fingerprint: str) -> dict | None:
    row = await db.get(Diagnosis, (owner, request_id))
    if row is None:
        return None
    if row.fingerprint != fingerprint:
        raise HTTPException(409, "该请求编号已对应另一份代码。")
    return row.result


async def reveal_hint(db: AsyncSession, challenge: Challenge) -> dict:
    template = EXERCISES[challenge.template_id]
    count = await db.scalar(update(Challenge).where(
        Challenge.id == challenge.id, Challenge.owner == challenge.owner, Challenge.closed.is_(False),
        Challenge.hints_used < len(template.hints),
    ).values(hints_used=Challenge.hints_used + 1).returning(Challenge.hints_used))
    if count is None:
        await db.refresh(challenge)
        if challenge.closed:
            raise HTTPException(409, "作答已结束。")
        count = challenge.hints_used
    await db.commit()
    return {"used": count, "hints": list(template.hints[:count])}


async def grade(db: AsyncSession, challenge: Challenge, request_id: str, answer: str) -> dict:
    normalized = answer.strip()
    answer_hash = digest(normalized)
    hints_used = await db.scalar(update(Challenge).where(
        Challenge.id == challenge.id, Challenge.owner == challenge.owner, Challenge.closed.is_(False),
    ).values(closed=True).returning(Challenge.hints_used))
    if hints_used is None:
        previous = await db.get(Attempt, challenge.id)
        if previous and previous.request_id == request_id and previous.answer_hash == answer_hash:
            return previous.result
        raise HTTPException(409, "此题已提交，请重新挑战。")

    template = EXERCISES[challenge.template_id]
    correct = normalized == template.answer
    outcome = "incorrect" if not correct else "assisted" if hints_used else "independent"
    prior = await history(db, challenge.owner, challenge.knowledge_id)
    independent = {row.template_id for row in prior if row.outcome == "independent"}
    if outcome == "independent":
        independent.add(template.id)
    recommendation = "repeat"
    if outcome == "independent":
        recommendation = "verified" if len(independent) >= 2 else "transfer"
    result = {"outcome": outcome, "hints_used": hints_used, "recommendation": recommendation,
              "distinct_independent": len(independent), "feedback": template.explanation}
    db.add(Attempt(challenge_id=challenge.id, request_id=request_id, answer_hash=answer_hash,
                   outcome=outcome, result=result))
    await db.commit()
    return result


async def retry(db: AsyncSession, challenge: Challenge) -> dict:
    if not challenge.closed:
        raise HTTPException(409, "请先提交本题。")
    next_id = str(uuid5(NAMESPACE_URL, f"codementor:retry:{challenge.id}"))
    existing = await db.get(Challenge, next_id)
    if existing:
        return challenge_view(existing)
    variants = CURRICULUM[challenge.knowledge_id]
    previous = EXERCISES[challenge.template_id]
    current_index = variants.index(previous)
    attempts = await history(db, challenge.owner, challenge.knowledge_id)
    completed = {row.template_id for row in attempts if row.outcome == "independent"}
    offsets = list(range(1, len(variants)))
    offset = next((i for i in offsets if variants[(current_index + i) % len(variants)].id not in completed), 1)
    new = new_challenge(challenge.owner, challenge.knowledge_id, current_index + offset, next_id)
    db.add(new)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        new = await db.get(Challenge, next_id)
        if new is None:
            raise
    return challenge_view(new)
