"""Deterministic checks after guidance; never evidence of independent mastery."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workbench import Diagnosis

# Reviewed v1 items. Answers stay server-side until the first submission.
ITEMS = {
    'loop-boundary': ('range(2, 5) 产生哪些数？', {'exclusive':'2, 3, 4', 'inclusive':'2, 3, 4, 5', 'start-zero':'0, 1, 2, 3, 4'}, 'exclusive', '起点 2 被包含，停止值 5 不被包含。'),
    'empty-list': ('取首项前，哪项检查能区分 [] 和 [0]？', {'length':'检查列表长度是否为 0', 'first':'检查首项是否等于 0', 'none':'无需检查'}, 'length', '空列表没有首项；[0] 是包含一个合法元素的列表。'),
    'accumulator': ('total = 0 放在循环前，依次加上 4、-1，两轮结束后的 total 分别是多少？', {'running':'4、3', 'reset':'4、-1', 'final-only':'3、3'}, 'running', '累加器保留上一轮结果，因此第二轮为 4 + (-1) = 3。'),
}

async def owned(db: AsyncSession, owner: str, diagnosis_id: str) -> Diagnosis:
    row = await db.get(Diagnosis, (owner, diagnosis_id))
    if row is None:
        raise HTTPException(404, '找不到该诊断。')
    return row

async def question(db: AsyncSession, owner: str, diagnosis_id: str) -> dict:
    row = await owned(db, owner, diagnosis_id)
    item = ITEMS.get(row.knowledge_id)
    if item is None:
        return {'available': False}
    return {'available': True, 'version': 1, 'prompt': item[0],
            'options': [{'id': k, 'label': v} for k, v in item[1].items()],
            'result': row.result.get('self_check')}

async def grade(db: AsyncSession, owner: str, diagnosis_id: str, choice: str) -> dict:
    row = await owned(db, owner, diagnosis_id)
    item = ITEMS.get(row.knowledge_id)
    if item is None:
        raise HTTPException(409, '该诊断尚无审核过的自查题。')
    if choice not in item[1]:
        raise HTTPException(422, '请选择本题提供的选项。')
    previous = row.result.get('self_check')
    if previous:
        if previous['choice'] != choice:
            raise HTTPException(409, '首次自查已记录，不能覆盖；请进入变式复测。')
        return previous
    correct = choice == item[2]
    result = {'choice': choice, 'correct': correct, 'version': 1,
              'context': 'after-guidance', 'attribution': 'unconfirmed',
              'feedback': ('讲解后自查通过。' if correct else '讲解后自查未通过，建议先复核规则。') + item[3] + '这一次作答不能证明只是敲错，也不能证明已经掌握；请继续完成不同题面的复测。',
              'updated_at': datetime.now(timezone.utc).isoformat()}
    row.result = {**row.result, 'self_check': result}
    await db.commit()
    return result

async def latest(db: AsyncSession, owner: str, concept: str | None) -> dict | None:
    if concept is None:
        return None
    rows = (await db.scalars(select(Diagnosis).where(Diagnosis.owner == owner, Diagnosis.knowledge_id == concept))).all()
    checks = [r.result['self_check'] for r in rows if r.result.get('self_check')]
    return max(checks, key=lambda x: x['updated_at']) if checks else None
