"""A deliberately small Python-subset interpreter. No eval, exec, host imports or IO.

Results prove only this interpreter's supported subset and supplied inputs.
"""
import ast
import hashlib
import json

def brief(value,depth=0):
    if type(value) in (int,float,bool,type(None)):return value
    if type(value) is str:return value[:80]
    if type(value) is list:
        if depth>=2:return {'type':'list','length':len(value)}
        return [brief(v,depth+1) for v in value[:8]]
    return {'type':'internal-value'}

class Unsupported(Exception): pass
class Returned(Exception):
    def __init__(self,value): self.value=value

class Machine:
    def __init__(self,files):
        self.files=files;self.modules={};self.trace=[];self.stdout='';self.steps=0;self.depth=0
        self.location={'path':'','line':1}
    def tick(self,node,path):
        self.steps+=1
        if self.steps>2000 or self.depth>25: raise Unsupported('超过受限解释器的步骤或调用深度上限')
        self.location={'path':path,'line':getattr(node,'lineno',1)}
    def bound(self,value):
        if isinstance(value,int) and value.bit_length()>256: raise Unsupported('整数过大')
        if isinstance(value,(str,list,tuple,dict)) and len(value)>1000: raise Unsupported('值过大')
        return value
    def display(self,value,nested=False,depth=0):
        self.steps+=1
        if self.steps>2000 or depth>25:raise Unsupported('输出遍历超过步骤或深度上限')
        if type(value) is list:
            result='['
            for i,v in enumerate(value):
                part=(', ' if i else '')+self.display(v,True,depth+1)
                if len(result)+len(part)>4000:raise Unsupported('输出超过上限')
                result+=part
            return result+']'
        if type(value) not in (int,float,str,bool,type(None)):raise Unsupported('不支持输出内部函数或模块值')
        text=repr(value) if nested else str(value)
        if len(text)>4000:raise Unsupported('输出超过上限')
        return text
    def module(self,name):
        path=name.replace('.','/')+'.py'
        if path not in self.files: raise Unsupported('只能导入项目内提供的 Python 文件')
        if path in self.modules:return self.modules[path]
        env={};self.modules[path]=env
        self.location={'path':path,'line':1}
        tree=ast.parse(self.files[path],filename=path)
        compile(tree,path,'exec')  # Contextual syntax validation only; never execute.
        self.block(tree.body,env,path)
        return env
    def block(self,nodes,env,path):
        for n in nodes:
            self.tick(n,path)
            self.trace.append({**self.location,'event':type(n).__name__})
            if isinstance(n,ast.Import):
                for a in n.names:
                    if '.' in a.name:raise Unsupported('暂不支持包导入')
                    env[a.asname or a.name]=('module',self.module(a.name))
            elif isinstance(n,ast.ImportFrom):
                if n.level or not n.module:raise Unsupported('暂不支持相对导入执行')
                m=self.module(n.module)
                for a in n.names:
                    if a.name not in m:raise Unsupported('导入名称未定义')
                    env[a.asname or a.name]=m[a.name]
            elif isinstance(n,ast.FunctionDef):
                if n.decorator_list or n.args.defaults or n.args.kwonlyargs or n.args.vararg or n.args.kwarg or n.args.posonlyargs:raise Unsupported('暂不支持复杂函数签名')
                if n.returns or any(a.annotation for a in n.args.args) or getattr(n,'type_params',[]):raise Unsupported('暂不支持注解或类型参数')
                forbidden=(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.NamedExpr,ast.Import,ast.ImportFrom,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Global,ast.Nonlocal,ast.Delete)
                if any(isinstance(x,forbidden) for statement in n.body for x in ast.walk(statement)):raise Unsupported('暂不支持函数内的名称重新绑定或嵌套定义')
                env[n.name]=('function',n,env,path)
            elif isinstance(n,ast.If):
                condition=bool(self.expr(n.test,env,path))
                self.trace.append({'path':path,'line':n.lineno,'event':'condition','value':condition})
                self.block(n.body if condition else n.orelse,env,path)
            elif isinstance(n,ast.Return):
                value=self.expr(n.value,env,path) if n.value else None
                self.trace.append({'path':path,'line':n.lineno,'event':'return-value','value':brief(value)})
                raise Returned(value)
            elif isinstance(n,ast.Assign):
                value=self.expr(n.value,env,path)
                for t in n.targets:
                    if not isinstance(t,ast.Name):raise Unsupported('仅支持名称赋值')
                    env[t.id]=value
            elif isinstance(n,ast.Expr):self.expr(n.value,env,path)
            elif isinstance(n,ast.Pass):pass
            else:raise Unsupported('暂不支持 '+type(n).__name__)
    def expr(self,n,env,path):
        self.tick(n,path)
        if isinstance(n,ast.Constant):
            if type(n.value) not in (str,int,float,bool,type(None)):raise Unsupported('不支持此常量')
            return self.bound(n.value)
        if isinstance(n,ast.Name):
            if n.id not in env:raise Unsupported('未定义或不支持的名称：'+n.id)
            return env[n.id]
        if isinstance(n,ast.List):return self.bound([self.expr(v,env,path) for v in n.elts])
        if isinstance(n,ast.Subscript):
            value=self.expr(n.value,env,path);index=self.expr(n.slice,env,path)
            if type(value) not in (list,str) or type(index) is not int:raise Unsupported('只支持列表或字符串的整数索引')
            return value[index]
        if isinstance(n,ast.BinOp):
            a=self.expr(n.left,env,path);b=self.expr(n.right,env,path)
            self.tick(n,path)
            if isinstance(n.op,ast.Add):
                if type(a) not in (int,float,type(None)) or type(b) not in (int,float,type(None)):raise Unsupported('仅支持数值加法')
                return self.bound(a+b)
            if isinstance(n.op,ast.Sub) and type(a) in (int,float) and type(b) in (int,float):return self.bound(a-b)
            raise Unsupported('仅支持数值加减法')
        if isinstance(n,ast.Attribute):
            module=self.expr(n.value,env,path)
            if type(module) is not tuple or module[0]!='module' or n.attr not in module[1]:raise Unsupported('只允许项目模块的公开名称')
            return module[1][n.attr]
        if isinstance(n,ast.Call):
            if n.keywords:raise Unsupported('暂不支持关键字参数')
            args=[self.expr(a,env,path) for a in n.args]
            if isinstance(n.func,ast.Name) and n.func.id=='print' and 'print' not in env:
                if any(type(a) not in (int,float,str,bool,type(None),list) for a in args):raise Unsupported('不支持输出此值')
                text=''
                for i,a in enumerate(args):
                    part=(' ' if i else '')+self.display(a)
                    if len(self.stdout)+len(text)+len(part)+1>4000:raise Unsupported('输出超过上限')
                    text+=part
                self.stdout+=text+'\n'
                return None
            f=self.expr(n.func,env,path)
            if type(f) is not tuple or f[0]!='function':raise Unsupported('只允许调用项目内定义的函数')
            _,fn,scope,source=f
            if len(args)!=len(fn.args.args):raise TypeError('实参数量与形参数量不符')
            parameters={p.arg:v for p,v in zip(fn.args.args,args)}
            local={**scope,**parameters}
            self.trace.append({'path':source,'line':fn.lineno,'event':'call-parameters','values':{k:brief(v) for k,v in parameters.items()}})
            self.depth+=1
            try:self.block(fn.body,local,source)
            except Returned as r:return r.value
            finally:self.depth-=1
            return None
        raise Unsupported('暂不支持表达式 '+type(n).__name__)

def verify(files,path):
    m=Machine(files);status='passed';error=None
    try:
        if not path.endswith('.py'):raise Unsupported('运行验证仅支持 Python 子集')
        m.module(path[:-3].replace('/','.'))
    except Unsupported as e:status='unsupported';error={**m.location,'message':str(e)}
    except SyntaxError as e:
        status='runtime-error';error={'path':e.filename or path,'line':e.lineno or 1,'message':'SyntaxError: '+e.msg}
    except (TypeError,IndexError,KeyError,ValueError,Returned) as e:
        status='runtime-error';error={**m.location,'message':type(e).__name__+': '+str(e)}
    except RecursionError:status='unsupported';error={**m.location,'message':'表达式嵌套超过上限'}
    return {'status':status,'stdout':m.stdout,'error':error,'trace':m.trace[:200],
            'buffer_hash':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),
            'execution_kind':'restricted-ast-interpreter','boundary':'实际执行了受限 Python 子集及当前输入；不等于完整 CPython 或全量测试通过。'}
