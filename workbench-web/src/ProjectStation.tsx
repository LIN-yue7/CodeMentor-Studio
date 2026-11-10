import {lazy,Suspense,useEffect,useState} from 'react'
import {get,post} from './api'
const Editor=lazy(()=>import('./Editor'))
type Project={id:string;name:string;revision:number;files:Record<string,string>}
type Inspection={status:string;summary:string;issues:{line:number|null;message:string}[]}
export function ProjectStation(){
 const [projects,setProjects]=useState<{id:string;name:string}[]>([])
 const [project,setProject]=useState<Project|null>(null)
 const [saved,setSaved]=useState('')
 const [file,setFile]=useState('main.py')
 const [name,setName]=useState('')
 const [path,setPath]=useState('')
 const [ready,setReady]=useState(false)
 const [busy,setBusy]=useState(false)
 const [error,setError]=useState('')
 const [notice,setNotice]=useState('')
 const [inspection,setInspection]=useState<Inspection|null>(null)
 const [checking,setChecking]=useState(false)
 const [line,setLine]=useState<number|null>(null)
 const [jump,setJump]=useState(0)
 const [retry,setRetry]=useState(0)
 const dirty=!!project&&JSON.stringify(project.files)!==saved
 const code=project?.files[file]??''
 useEffect(()=>{let live=true;post('/session').then(()=>get<{items:{id:string;name:string}[]}>('/projects')).then(r=>{if(live){setProjects(r.items);setReady(true)}}).catch(()=>{if(live)setError('项目服务未就绪，请确认已启动新版后端并刷新。')});return()=>{live=false}},[])
 useEffect(()=>{const handler=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',handler);return()=>window.removeEventListener('beforeunload',handler)},[dirty])
 useEffect(()=>{
  setInspection(null);setLine(null)
  if(!project){setChecking(false);return}
  let live=true;const controller=new AbortController();setChecking(true)
  const timer=setTimeout(()=>{post<Inspection>('/code-inspection',{path:file,code},controller.signal).then(r=>{if(live){setInspection(r);setLine(r.issues[0]?.line??null)}}).catch(()=>{if(live)setInspection({status:'failed',issues:[],summary:'检查未完成，继续编辑或点击重新检查。'})}).finally(()=>{if(live)setChecking(false)})},650)
  return()=>{live=false;clearTimeout(timer);controller.abort()}
 },[project?.id,file,code,retry])
 function open(p:Project){setProject(p);setSaved(JSON.stringify(p.files));setFile(Object.keys(p.files)[0]);setError('');setNotice('已读取服务端项目。')}
 async function create(){if(!name.trim()||busy)return;if(dirty){setError('请先保存当前项目，再新建。');return}setBusy(true);try{const p=await post<Project>('/projects',{name:name.trim()});setProjects(v=>[...v,{id:p.id,name:p.name}]);open(p);setName('')}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function choose(id:string){if(dirty){setError('请先保存当前改动，再切换项目。');return}if(!id)return;setBusy(true);try{open(await get<Project>('/projects/'+id))}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function save(){if(!project||busy)return;const snapshot=project;setBusy(true);setError('');try{const p=await post<Project>('/projects/'+snapshot.id,{revision:snapshot.revision,files:snapshot.files});setProject(current=>current?.id===p.id?{...current,revision:p.revision}:current);setSaved(JSON.stringify(snapshot.files));setNotice('已保存到服务端 · 版本 '+p.revision)}catch(e){setError(String(e))}finally{setBusy(false)}}
 function add(){const p=path.trim();if(!project||!p)return;if(!/^[\w./ -]+$/.test(p)||p.length>160||p.split('/').some(s=>!s||s.startsWith('.'))||! /\.(py|js|ts|json|html|css|md|txt)$/.test(p)){setError('请输入安全相对路径，例如 src/helper.py；不支持密钥文件。');return}if(p in project.files){setError('文件已存在。');return}if(Object.keys(project.files).length>=30){setError('当前版本每项目最多 30 个文件。');return}setProject({...project,files:{...project.files,[p]:''}});setFile(p);setPath('');setError('')}
 function exportProject(){if(!project)return;const url=URL.createObjectURL(new Blob([JSON.stringify(project,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='codementor-project.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 return <div className="station"><header className="station-header"><strong>CodeMentor <span>PROJECT STATION</span></strong><a href="?view=lessons" onClick={e=>{if(dirty){e.preventDefault();setError('请先保存，再进入教学实验。')}}}>教学实验 ↗</a></header>
 <div className="station-title"><div><span className="eyebrow">从自己的项目开始</span><h1>项目工作区</h1></div><span className="subtle">本地自动检查 · 不调用付费模型</span></div>
 {error&&<p className="station-error" role="alert">{error}</p>}
 <div className="station-layout"><aside className="station-files"><h2>项目与文件</h2>
 <label>打开项目<select disabled={!ready||busy} value={project?.id??''} onChange={e=>void choose(e.target.value)}><option value="">选择项目</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
 <form onSubmit={e=>{e.preventDefault();void create()}}><label>项目名称<input value={name} maxLength={80} onChange={e=>setName(e.target.value)} placeholder="例如：校园活动工具"/></label><button className="plain" disabled={!ready||busy||!name.trim()}>新建项目</button></form>
 {project&&<><p className="eyebrow">文件 / {Object.keys(project.files).length}</p><nav aria-label="项目文件">{Object.keys(project.files).sort().map(p=><button className={p===file?'file-active':''} key={p} onClick={()=>setFile(p)} aria-current={p===file?'page':undefined}>{p}</button>)}</nav>
 <form onSubmit={e=>{e.preventDefault();add()}}><label>新文件路径<input value={path} onChange={e=>setPath(e.target.value)} placeholder="src/helper.py"/></label><button className="plain" disabled={!path.trim()}>添加文件</button></form></>}
 <p className="subtle">最多 30 个文件 / 50 KB。当前匿名浏览器身份保存项目，请导出备份；跨浏览器与重启恢复尚未完善。</p></aside>
 <main className="station-code">{project?<><div className="station-filebar"><strong>{file}</strong><span>{dirty?'有未保存改动':'已保存'}</span></div><Suspense fallback={<p>加载编辑器…</p>}><Editor key={file} code={code} pythonMode={file.endsWith('.py')} line={line} jump={jump} onChange={value=>setProject(p=>p?{...p,files:{...p.files,[file]:value}}:p)}/></Suspense><div className="station-actions"><button className="primary" disabled={busy||!dirty} onClick={()=>void save()}>{busy?'保存中…':'保存项目'}</button><button className="plain" onClick={exportProject}>导出项目 JSON</button><span role="status">{notice}</span></div></>:<div className="station-empty"><h2>创建项目，编写自己的代码</h2><p>从空白文件开始。支持多个文件与目录路径，Python 文件编辑停止后自动检查语法。</p><p>教学样例已移至独立入口，不再限制项目内容。</p></div>}</main>
 <aside className="station-inspection"><div className="panel-head"><h2>代码检查</h2></div><div className="panel-content"><span className="eyebrow">PYTHON AST · 当前文件</span><p role="status">{!project?'打开文件后开始检查。':checking?'正在检查当前改动…':inspection?.summary}</p>{inspection?.issues.map((issue,i)=><button key={i} className="plain" onClick={()=>{setLine(issue.line);setJump(v=>v+1)}}>第 {issue.line??'?'} 行 · {issue.message}</button>)}{project&&<button className="plain" onClick={()=>setRetry(v=>v+1)}>重新检查</button>}<hr/><h3>检查能力与边界</h3><p>Python 语法检查会自动运行，不执行代码。其他文本文件当前支持编辑和保存。</p><p>项目级 AI 审查、跨文件语义分析、运行与 Web 预览尚未接入此工作区。</p></div></aside></div></div>
}
