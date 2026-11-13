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
    return {'items':items[:200]}
