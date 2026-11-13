"""Persist only parser observations and explicit user actions, never model claims.

Saved revision transitions are serialized by the project's optimistic save update.
Drafts may record rejected syntax but cannot confirm a repair or reset saved state.
"""
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from app.models.workbench import ProjectLearningEvent, ProjectLearningState


def code_hash(code):
    return hashlib.sha256(code.encode()).hexdigest()


async def _event(db, owner, project_id, path, kind, concept, message, fingerprint, revision, **extra):
    key = code_hash(json.dumps([path,kind,concept,fingerprint], ensure_ascii=False))
    data = {'id':key,'path':path,'kind':kind,'concept':concept,'message':message,
            'buffer_hash':fingerprint,'revision':revision,
            'created_at':datetime.now(timezone.utc).isoformat(),**extra}
    insert = postgres_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    await db.execute(insert(ProjectLearningEvent).values(owner=owner,project_id=project_id,key=key,data=data)
                     .on_conflict_do_nothing(index_elements=['owner','project_id','key']))


async def observe(db, owner, project_id, files, results, revision, *, saved=False):
    for path, result in results.items():
        fingerprint = code_hash(files[path])
        issues = result['issues']
        for issue in issues:
            await _event(db,owner,project_id,path,'syntax-error',issue['concept'],issue['title'],
                         fingerprint,revision,line=issue['line'],source='python-parser',
                         observation_scope='saved' if saved else 'draft')
        if not saved:
            continue
        state = await db.get(ProjectLearningState,(owner,project_id,path))
        if state is not None and state.revision >= revision:
            continue
        if state is not None and state.issues and result['status']=='syntax-ok':
            for concept in sorted({issue['concept'] for issue in state.issues}):
                await _event(db,owner,project_id,path,'syntax-rechecked',concept,
                             '保存后的新版本通过语法复查；不代表运行或业务逻辑已验证。',
                             fingerprint + ':' + str(revision),revision,source='python-parser',
                             previous_revision=state.revision,observation_scope='saved')
        # Unsupported/uncertain parsing cannot erase confirmed parser-error state.
        if result['status'] in {'syntax-ok','syntax-error'}:
            if state is None:
                db.add(ProjectLearningState(owner=owner,project_id=project_id,path=path,
                                            revision=revision,issues=issues))
            else:
                state.revision, state.issues = revision, issues
    if saved:
        await db.execute(delete(ProjectLearningState).where(
            ProjectLearningState.owner==owner,ProjectLearningState.project_id==project_id,
            ProjectLearningState.path.not_in(list(files))))


async def hint_viewed(db, owner, project, path, code=None):
    await _event(db,owner,project.id,path,'hint-viewed','review-guidance',
                 '已主动查看本地提示；此事件不表示已理解或掌握。',
                 code_hash(project.files[path] if code is None else code),project.revision,source='user-action')


async def read_learning(db, owner, project_id):
    rows = (await db.scalars(select(ProjectLearningEvent).where(
        ProjectLearningEvent.owner==owner,ProjectLearningEvent.project_id==project_id))).all()
    items = sorted((row.data for row in rows),key=lambda x:(x['created_at'],x['id']),reverse=True)
    return {'items':items[:200],'summary':summarize_learning(items[:200])}

def summarize_learning(items):
    """Describe recorded versions, not inferred ability or unobserved independence."""
    from collections import defaultdict
    groups=defaultdict(list)
    hints={(e.get('path'),e.get('buffer_hash')) for e in items if e.get('kind')=='hint-viewed'}
    for e in items:
        if e.get('kind')=='syntax-error':groups[e['concept']].append(e)
    evidence=[]
    for concept,errors in sorted(groups.items()):
        versions={(e['path'],e['buffer_hash']) for e in errors}
        fixes=sum(e.get('kind')=='syntax-rechecked' and e.get('concept')==concept for e in items)
        evidence.append({'concept':concept,'observed_versions':len(versions),'hint_viewed_versions':len(versions&hints),'saved_syntax_rechecks':fixes})
    repeated=[e for e in evidence if e['observed_versions']>=3]
    if not repeated:
        return {'status':'insufficient','evidence':evidence,'recommendations':['当前记录不足以归纳反复出现的模式或熟练程度。先用普通输入、空输入和边界输入核对当前代码。'],'boundary':'仅统计当前保留的真实事件；未查看提示不等于独立掌握，语法复查不等于运行正确。'}
    return {'status':'observed-pattern','evidence':evidence,'recommendations':[
        f"在已记录的{e['observed_versions']}个不同代码版本中观察到“{e['concept']}”，其中{e['hint_viewed_versions']}个版本记录过查看提示。建议比较出错行与修正行，解释规则后再尝试一个相似例子。" for e in repeated[:3]],
        'boundary':'版本计数不是学习次数；不推断能力等级或未观察的独立完成情况。'}
