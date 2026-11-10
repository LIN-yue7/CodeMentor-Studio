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
