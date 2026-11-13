"""Owner-scoped virtual files. Never map supplied paths to host filesystem."""
import ast
import re
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Request
from pydantic import Field, field_validator
from sqlalchemy import select, update
from app.api.workbench import Owner, DB
from app.schemas.workbench import Input
from app.models.workbench import Project, ProjectPrivacy
from app.services import project_review, project_learning
from app.services.project_retrieval import retrieve_project
from app.services.project_diagnostics import inspect_python
from typing import Literal

router = APIRouter(prefix='/api')

def valid_path(path: str) -> bool:
    return (len(path)<=160 and re.fullmatch(r'[\w./ -]+',path) is not None
            and all(part and not part.startswith('.') for part in path.split('/'))
            and path.rsplit('.',1)[-1] in {'py','js','ts','json','html','css','md','txt'})

class CreateProject(Input):
    name: str = Field(min_length=1,max_length=80)

class SaveProject(Input):
    name: str | None = Field(default=None,min_length=1,max_length=80)
    revision: int = Field(ge=0,strict=True)
    files: dict[str,str]
    @field_validator('files')
    @classmethod
    def bounded_files(cls, files):
        if not 1 <= len(files) <= 30 or any(not valid_path(p) for p in files):
            raise ValueError('支持 1–30 个安全相对路径文件。')
        if sum(len(v.encode('utf-8')) for v in files.values()) > 50000:
            raise ValueError('项目总内容不能超过 50 KB。')
        return files

class InspectCode(Input):
    path: str = Field(min_length=1,max_length=160)
    code: str = Field(max_length=50000)

def public(p):
    return {'id':p.id,'name':p.name,'revision':p.revision,'files':p.files}

async def owned(db,owner,id):
    row=await db.get(Project,(owner,str(id)))
    if row is None: raise HTTPException(404,'项目不存在。')
    return row

@router.get('/projects')
async def list_projects(owner:Owner,db:DB):
    rows=(await db.scalars(select(Project).where(Project.owner==owner))).all()
    return {'items':[{'id':p.id,'name':p.name} for p in rows]}

@router.post('/projects')
async def create_project(payload:CreateProject,owner:Owner,db:DB):
    p=Project(owner=owner,id=str(uuid4()),name=payload.name.strip() or '未命名项目',revision=0,files={'main.py':''})
    db.add(p); await db.commit(); return public(p)

@router.get('/projects/{id}')
async def get_project(id:UUID,owner:Owner,db:DB):
    return public(await owned(db,owner,id))

@router.post('/projects/{id}')
async def save_project(id:UUID,payload:SaveProject,owner:Owner,db:DB):
    await owned(db,owner,id)
    values = {'files':payload.files,'revision':payload.revision+1}
    if payload.name is not None:
        values['name'] = payload.name.strip() or '未命名项目'
    r=await db.execute(update(Project).where(Project.owner==owner,Project.id==str(id),Project.revision==payload.revision).values(**values))
    if r.rowcount!=1:
        await db.rollback(); raise HTTPException(409,'保存版本冲突，请先导出草稿，再重新打开项目。')
    results = {path:inspect_python(path,code) for path,code in payload.files.items()}
    await project_learning.observe(db,owner,str(id),payload.files,results,payload.revision+1,saved=True)
    await db.commit()
    return public(await owned(db,owner,id))

@router.post('/code-inspection')
async def inspect_code(payload:InspectCode,owner:Owner):
    return inspect_python(payload.path,payload.code)

class ProjectContext(SaveProject):
    path: str = Field(max_length=160)
    cursor_line: int = Field(default=1,ge=1,le=16001)
    language: Literal['auto','python','text']='auto'

def inspect_project(files, path, language):
    results = {}
    for candidate, code in files.items():
        if candidate == path and language == 'text':
            results[candidate] = {'status':'unsupported','issues':[],
                                  'summary':'当前文件按纯文本处理，未进行 Python 语法检查。'}
        elif candidate == path and language == 'python':
            result = inspect_python('current.py',code)
            for issue in result['issues']:
                issue['path'] = candidate
            results[candidate] = result
        else:
            results[candidate] = inspect_python(candidate,code)
    return results


async def build_context(id, payload, owner, db, *, record):
    saved=await owned(db,owner,id)
    if payload.path not in payload.files: raise HTTPException(422,'当前文件不在项目中。')
    code=payload.files[payload.path]
    results=inspect_project(payload.files,payload.path,payload.language)
    result=results[payload.path]
    function=None
    if result['status']=='syntax-ok':
        tree=ast.parse(code)
        functions=[node for node in ast.walk(tree)
                   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
                   and node.lineno<=payload.cursor_line<=node.end_lineno]
        if functions:
            function=min(functions,key=lambda n:n.end_lineno-n.lineno).name
    retrieval=retrieve_project(payload.files,payload.path,payload.cursor_line,
                               getattr(payload,'request',''),payload.language,result['issues'])
    if record:
        # Requests with stale saved revisions must not add obsolete observations.
        if payload.revision == saved.revision:
            await project_learning.observe(db,owner,str(id),payload.files,results,payload.revision)
            await db.commit()
    learning=await project_learning.read_learning(db,owner,str(id))
    if result['issues']:
        hints=['先检查标记行及上一行：语句是否写完、括号是否配对？',
               '若是函数、条件或循环的头部，检查末尾冒号和下一行缩进。解析器位置不一定就是根本原因。',
               '一次只改一个位置，停止输入后查看检查结果；保存后才记录版本间的语法修复复查，语法通过仍需核对业务行为。']
    else:
        hints=['先用自己的话写出当前函数的输入、输出和边界条件。',
               '检查引用模块的返回值约定是否与调用处一致；静态检索不证明调用正确。',
               '选一个普通输入和一个边界输入，写下预期结果。未执行项目测试；保存后才记录版本间的语法修复复查。']
    return {**result,'context':{'path':payload.path,'function':function,
            'related_files':retrieval['related_files'],
            'unsaved':payload.files!=saved.files,'saved_revision':saved.revision,
            'buffer_hash':project_learning.code_hash(code)},
            'project_issues':{path:r['issues'] for path,r in results.items()},
            'retrieval':retrieval,'learning':learning,
            'mentor':{'source':'local-reviewed-guidance','hints':hints,'attribution':'unconfirmed'}}


@router.post('/projects/{id}/context')
async def project_context(id:UUID,payload:ProjectContext,owner:Owner,db:DB):
    return await build_context(id,payload,owner,db,record=True)


@router.get('/projects/{id}/learning')
async def learning_read(id:UUID,owner:Owner,db:DB):
    await owned(db,owner,id)
    return await project_learning.read_learning(db,owner,str(id))


class LearningAction(Input):
    path: str = Field(min_length=1,max_length=160)
    action: Literal['hint-viewed']
    code: str | None = Field(default=None,max_length=50000)


@router.post('/projects/{id}/learning-action')
async def learning_action(id:UUID,payload:LearningAction,owner:Owner,db:DB):
    project=await owned(db,owner,id)
    if payload.path not in project.files: raise HTTPException(422,'当前文件不在已保存项目中。')
    await project_learning.hint_viewed(db,owner,project,payload.path,payload.code)
    await db.commit()
    return await project_learning.read_learning(db,owner,str(id))


class PrivacyInput(Input):
    allow_external: bool = Field(strict=True)

class ReviewInput(ProjectContext):
    mode: Literal['mentor','collaborate','engineering']='mentor'
    request: str = Field(default='',max_length=1000)

@router.get('/projects/{id}/privacy')
async def privacy_read(id:UUID,owner:Owner,db:DB):
    await owned(db,owner,id)
    row=await db.get(ProjectPrivacy,(owner,str(id)))
    return {'allow_external':bool(row and row.allow_external)}

@router.post('/projects/{id}/privacy')
async def privacy_write(id:UUID,payload:PrivacyInput,owner:Owner,db:DB):
    await owned(db,owner,id)
    await db.merge(ProjectPrivacy(owner=owner,project_id=str(id),allow_external=payload.allow_external))
    await db.commit()
    return {'allow_external':payload.allow_external}

@router.post('/projects/{id}/review-preview')
async def review_preview(id:UUID,payload:ReviewInput,owner:Owner,db:DB):
    context=await build_context(id,payload,owner,db,record=False)
    return project_review.bundle(payload,context)

@router.post('/projects/{id}/review')
async def project_ai_review(id:UUID,payload:ReviewInput,request:Request,owner:Owner,db:DB):
    permissions=await privacy_read(id,owner,db)
    if not permissions['allow_external']: raise HTTPException(403,'项目未授权向外部模型发送代码。')
    context=await build_context(id,payload,owner,db,record=False)
    data=project_review.bundle(payload,context)
    return await project_review.review(request.app.state.tutor,owner,data,payload.mode)

@router.post('/projects/{id}/verify')
async def project_verify(id:UUID,payload:ProjectContext,owner:Owner,db:DB):
    await owned(db,owner,id)
    if payload.path not in payload.files: raise HTTPException(422,'当前文件不在项目中。')
    from app.services.project_verification import verify
    result=verify(payload.files,payload.path)
    await project_learning._event(db,owner,str(id),payload.path,'execution-'+result['status'],'restricted-execution',
        '受限 Python 执行：'+result['status']+'；'+result['boundary'],result['buffer_hash'],payload.revision,source='restricted-ast-interpreter')
    await db.commit()
    return result
