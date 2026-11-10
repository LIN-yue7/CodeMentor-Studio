"""Reviewed coaching and explicit learner self-report; never infer personality."""
from collections import Counter
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.models.workbench import Diagnosis
from app.services.workbench_selfcheck import latest as latest_check

GUIDES = {
 'loop-boundary': ('循环结束条件', 'range 的停止值不参与遍历。减一后，最后一个元素还没被访问，循环就结束了。', '先列出长度为 1 和 2 的列表对应下标，再把上界改为 len(xs)，或直接遍历元素。修改后手算 []、[5]、[-2, 3]，检查结果分别为 0、5、1。不要只用最后一项为 0 的列表验证，它可能掩盖漏算。', '不看提示：range(3) 会产生哪些数？你原本希望最后一次访问哪个下标？'),
 'empty-list': ('输入前提与边界条件', '访问第一个元素隐含了列表非空这个前提。空列表没有下标 0，所以这条路径无法返回结果。', '先写清空输入时应返回什么，再在取首项之前处理空列表；不要随意猜一个默认值。分别检查 []、[0]、[7, 8]：非空时应返回首项，0 也是合法元素，不能把它当成没有数据。', '你写代码时是否假定输入一定非空？这个假定是题目给的，还是自己补充的？'),
 'accumulator': ('变量生命周期与状态累积', '循环内部的初始化会在每轮覆盖前面的累计值，最终留下的不是完整历史。', '把初始化移到循环前，在循环内只更新。用 [2, 3] 手算每轮前后状态，应从 0 到 2 再到 5；再检查 [] 返回 0。只用一个元素验证，可能看不出每轮重置的问题。', '处理第二个元素之前，你认为累加变量应保存什么？原代码是否保留了它？'),
}

async def memories(db, owner):
    rows = list((await db.scalars(select(Diagnosis).where(Diagnosis.owner == owner))).all())
    items = [{'diagnosis_id': r.id, 'knowledge_id': r.knowledge_id, 'reflection': r.result['reflection']}
             for r in rows if r.result.get('reflection')]
    return sorted(items, key=lambda x: x['reflection']['updated_at'], reverse=True)

async def coaching(db, owner, result):
    concept = result['evidence'][0].get('knowledge_id') if result['evidence'] else None
    items = [x for x in await memories(db, owner) if x['knowledge_id'] == concept]
    counts = dict(Counter(x['reflection']['reason'] for x in items))
    if concept in GUIDES:
        topic, why, fix, question = GUIDES[concept]
    else:
        topic, why, fix, question = ('待确认', '现有证据不足以判断逻辑错因；语法位置也不等于个人学习原因。', '先确认题目要求、预期输出与实际表现，再用最小输入定位。', '你原本想实现什么？哪一步的结果与你预期不同？')
    action = '先独立回答自查问题，再做一道不同题面的变式。'
    if counts:
        latest = items[0]['reflection']['reason']
        action = {'typing': '你上次自述偏向输入失误：这次先逐行核对，再独立复测，确认是否只是书写偏差。',
                  'concept': '你上次自述概念不稳：这次先用自己的话说明规则，再用边界例子检查理解。',
                  'approach': '你上次自述思路偏差：这次先写每一步应保持的条件，再比较程序状态。',
                  'requirement': '你上次自述题意理解偏差：先明确输入范围和预期行为，再检查代码。',
                  'unsure': action}[latest]
    check = await latest_check(db, owner, concept)
    if check:
        action += ' 最近一次讲解后自查' + ('通过：继续完成不同题面的复测，尚不能确定个人错因。' if check['correct'] else '未通过：优先回到规则和反例，再检查原先的原因判断。')
    return {'self_check_available': concept in GUIDES, 'source': 'reviewed-local-guidance', 'attribution': 'unconfirmed', 'topic': topic,
            'why': why, 'fix': fix, 'question': question, 'next_action': action,
            'history': {'self_reports': counts, 'count': len(items)},
            'caution': '敲错、概念不稳、思路或题意偏差都只是待确认原因。自述是你的判断，不是系统对能力或性格的定论。'}

async def save_reflection(db, owner, diagnosis_id, payload):
    row = await db.get(Diagnosis, (owner, diagnosis_id))
    if row is None:
        raise HTTPException(404, '找不到该诊断。')
    value = dict(row.result)
    if payload is None:
        value.pop('reflection', None)
    else:
        value['reflection'] = {**payload.model_dump(), 'source': 'learner-self-report',
                               'updated_at': datetime.now(timezone.utc).isoformat()}
    row.result = value
    await db.commit()
    return {'saved': payload is not None}
