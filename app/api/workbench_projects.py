"""Owner-scoped virtual files. Never map supplied paths to host filesystem."""
import ast
import re
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException
from pydantic import Field, field_validator
from sqlalchemy import select, update
from app.api.workbench import Owner, DB
from app.schemas.workbench import Input
from app.models.workbench import Project

router = APIRouter(prefix='/api')

def valid_path(path: str) -> bool:
    return (len(path)<=160 and re.fullmatch(r'[\w./ -]+',path) is not None
            and all(part and not part.startswith('.') for part in path.split('/'))
            and path.rsplit('.',1)[-1] in {'py','js','ts','json','html','css','md','txt'})

class CreateProject(Input):
    name: str = Field(min_length=1,max_length=80)

class SaveProject(Input):
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
    code: str = Field(max_length=16000)

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
    r=await db.execute(update(Project).where(Project.owner==owner,Project.id==str(id),Project.revision==payload.revision).values(files=payload.files,revision=payload.revision+1))
    if r.rowcount!=1:
        await db.rollback(); raise HTTPException(409,'保存版本冲突，请先导出草稿，再重新打开项目。')
    await db.commit()
    return public(await owned(db,owner,id))

@router.post('/code-inspection')
async def inspect_code(payload:InspectCode,owner:Owner):
    if not payload.path.endswith('.py'):
        return {'status':'unsupported','issues':[],'summary':'此文件可编辑保存，暂未接入该语言的自动检查。'}
    try:
        tree=ast.parse(payload.code)
        compile(tree,'submission.py','exec')  # Validate contextual syntax; NEVER execute.
    except SyntaxError as exc:
        return {'status':'syntax-error','issues':[{'line':exc.lineno,'message':exc.msg}],
                'summary':'发现 Python 语法错误；不代表已检查全部逻辑。'}
    except (ValueError,RecursionError):
        return {'status':'uncertain','issues':[],'summary':'代码结构无法安全解析，请缩小文件。'}
    return {'status':'syntax-ok','issues':[],'summary':'Python 语法检查通过。业务逻辑、导入依赖和运行结果尚未验证。'}

class ProjectContext(SaveProject):
    path: str = Field(max_length=160)
    cursor_line: int = Field(default=1,ge=1,le=16001)

@router.post('/projects/{id}/context')
async def project_context(id:UUID,payload:ProjectContext,owner:Owner,db:DB):
    import hashlib
    saved=await owned(db,owner,id)
    if payload.path not in payload.files: raise HTTPException(422,'当前文件不在项目中。')
    code=payload.files[payload.path]
    result=await inspect_code(InspectCode(path=payload.path,code=code),owner)
    function=None
    related=set()
    if result['status']=='syntax-ok':
        tree=ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.lineno<=payload.cursor_line<=node.end_lineno:
                function=node.name
            modules=([node.module] if isinstance(node,ast.ImportFrom) and node.level==0 and node.module else
                     [n.name for n in node.names] if isinstance(node,ast.Import) else [])
            for module in modules:
                path=module.replace('.','/')+'.py'
                if path in payload.files: related.add(path)
    if result['issues']:
        hints=['先检查标记行及上一行：语句是否写完、括号是否配对？',
               '若是函数、条件或循环的头部，检查末尾冒号和下一行缩进。解析器位置不一定就是根本原因。',
               '一次只改一个位置，停止输入后查看检查结果；语法通过后仍需核对业务行为。']
    else:
        hints=['先用自己的话写出当前函数的输入、输出和边界条件。',
               '检查引用模块的返回值约定是否与调用处一致；目前只定位引用，不证明调用正确。',
               '选一个普通输入和一个边界输入，写下预期结果。当前系统没有执行项目测试，不能据此宣布逻辑正确。']
    return {**result,'context':{'path':payload.path,'function':function,'related_files':sorted(related),
            'unsaved':payload.files!=saved.files,'saved_revision':saved.revision,
            'buffer_hash':hashlib.sha256(code.encode()).hexdigest()},
            'mentor':{'source':'local-reviewed-guidance','hints':hints,'attribution':'unconfirmed'}}
