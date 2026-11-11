import {lazy,Suspense,useEffect,useState,useRef} from 'react'
import {get,post} from './api'
import {ProjectReview} from './ProjectReview'
import {DiagnosticCard,TeachingPanel,type Inspection} from './StudioDiagnostics'
import {FileTree} from './FileTree'
const Editor=lazy(()=>import('./Editor'))
type Project={id:string;name:string;revision:number;files:Record<string,string>}
export function ProjectStation(){
 const [projects,setProjects]=useState<{id:string;name:string}[]>([])
 const [project,setProject]=useState<Project|null>(null),[saved,setSaved]=useState('')
 const [file,setFile]=useState('main.py'),[name,setName]=useState(''),[path,setPath]=useState('')
 const [ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('')
 const [inspection,setInspection]=useState<Inspection|null>(null),[checking,setChecking]=useState(false)
 const [line,setLine]=useState<number|null>(null),[jump,setJump]=useState(0),[cursor,setCursor]=useState(1),[retry,setRetry]=useState(0)
 const [mentorWidth,setMentorWidth]=useState(360),[bottomHeight,setBottomHeight]=useState(210)
 const [filesOpen,setFilesOpen]=useState(true),[diagnosisOpen,setDiagnosisOpen]=useState(true),[bottomOpen,setBottomOpen]=useState(true)
 const [mobile,setMobile]=useState('files'),[bottom,setBottom]=useState('问题'),[feedback,setFeedback]=useState('')
 const lastIssue=useRef<Record<string,string>>({}),inspectionRequest=useRef(0)
 const [events,setEvents]=useState<string[]>([]),[selection,setSelection]=useState('')
 const cursorRef=useRef(cursor);cursorRef.current=cursor
 const dirty=!!project&&JSON.stringify(project.files)!==saved
 const code=project?.files[file]??''
 useEffect(()=>{let live=true;post('/session').then(()=>get<{items:{id:string;name:string}[]}>('/projects')).then(r=>{if(live){setProjects(r.items);setReady(true)}}).catch(()=>{if(live)setError('项目服务未就绪，请确认已启动新版后端并刷新。')});return()=>{live=false}},[])
 useEffect(()=>{const handler=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue=''}};window.addEventListener('beforeunload',handler);return()=>window.removeEventListener('beforeunload',handler)},[dirty])
 useEffect(()=>{
  const version=++inspectionRequest.current
  setInspection(null);setLine(null);setFeedback('')
  if(!project){setChecking(false);return}
  let live=true;const controller=new AbortController();setChecking(true)
  const timer=setTimeout(()=>{post<Inspection>('/projects/'+project.id+'/context',{path:file,files:project.files,revision:project.revision,cursor_line:cursorRef.current},controller.signal).then(r=>{
   if(!live||version!==inspectionRequest.current)return
   setInspection(r);setLine(r.issues[0]?.line??null)
   const key=project.id+':'+file
   const issue=r.issues[0]
   if(r.status==='syntax-error'){
    const signature=issue.concept+':'+issue.line+':'+issue.message
    if(lastIssue.current[key]!==signature)setEvents(v=>[file+' · '+issue.title+'（本地证据）',...v].slice(0,30))
    lastIssue.current[key]=signature
   }else if(r.status==='syntax-ok'&&lastIssue.current[key]){
    delete lastIssue.current[key];setFeedback('本次语法问题已通过复查；这不代表逻辑正确或知识点已掌握。')
    setEvents(v=>[file+' · 修改后语法复查通过',...v].slice(0,30))
   }
  }).catch(()=>{if(live)setInspection({status:'failed',issues:[],summary:'检查未完成，请点击重新检查。'})}).finally(()=>{if(live)setChecking(false)})},650)
  return()=>{live=false;clearTimeout(timer);controller.abort()}
 },[project?.id,project?.files,file,retry])
 function open(p:Project){setFeedback('');setEvents([]);lastIssue.current={};setProject(p);setSaved(JSON.stringify(p.files));setFile(Object.keys(p.files)[0]);setCursor(1);setSelection('');setMobile('code');setError('');setNotice('已读取服务端项目。')}
 async function create(){if(!name.trim()||busy)return;if(dirty){setError('请先保存当前项目，再新建。');return}setBusy(true);try{const p=await post<Project>('/projects',{name:name.trim()});setProjects(v=>[...v,{id:p.id,name:p.name}]);open(p);setName('')}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function choose(id:string){if(dirty){setError('请先保存当前改动，再切换项目。');return}if(!id)return;setBusy(true);try{open(await get<Project>('/projects/'+id))}catch(e){setError(String(e))}finally{setBusy(false)}}
 async function save(){if(!project||busy)return;const snapshot=project;setBusy(true);setError('');try{const p=await post<Project>('/projects/'+snapshot.id,{revision:snapshot.revision,files:snapshot.files});setProject(current=>current?.id===p.id?{...current,revision:p.revision}:current);setSaved(JSON.stringify(snapshot.files));setNotice('已保存到服务端 · 版本 '+p.revision)}catch(e){setError(String(e))}finally{setBusy(false)}}
 function selectFile(p:string){setFile(p);setFeedback('');setCursor(1);setSelection('');setMobile('code')}
 function add(){const p=path.trim();if(!project||!p)return;if(!/^[\w./ -]+$/.test(p)||p.length>160||p.split('/').some(s=>!s||s.startsWith('.'))||! /\.(py|js|ts|json|html|css|md|txt)$/.test(p)){setError('请输入安全相对路径，例如 src/helper.py；不支持密钥文件。');return}if(p in project.files){setError('文件已存在。');return}if(Object.keys(project.files).length>=30){setError('当前版本每项目最多 30 个文件。');return}setProject({...project,files:{...project.files,[p]:''}});selectFile(p);setPath('');setError('')}
 function exportProject(){if(!project)return;const url=URL.createObjectURL(new Blob([JSON.stringify(project,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='codementor-project.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 function locate(value:number){setLine(value);setJump(v=>v+1);setMobile('code')}
 const issue=inspection?.issues[0]
 const style={'--mentor-width':mentorWidth+'px','--bottom-height':bottomHeight+'px'} as React.CSSProperties
 return <div className="station studio-r6" data-mobile-panel={mobile} data-files={filesOpen} data-diagnosis={diagnosisOpen} data-bottom={bottomOpen} style={style}>
  <header className="station-header"><strong><span className="studio-logo" aria-hidden="true">⌘</span> CodeMentor Studio</strong><span className="studio-tagline">AI 原生编程学习工作台</span><span className="live-indicator">● 本地自动检查</span><a href="?view=lessons" onClick={e=>{if(dirty){e.preventDefault();setError('请先保存，再进入教学实验。')}}}>教学实验 ↗</a></header>
  <div className="station-title"><div className="layout-tools"><button aria-label={filesOpen?'折叠文件区':'展开文件区'} onClick={()=>setFilesOpen(v=>!v)}>▱</button><h1>{project?.name??'项目工作区'}</h1></div><span className="subtle">{project?Object.keys(project.files).length+' 个文件 · '+(dirty?'未保存':'已保存'):'从真实项目开始学习'}</span><div className="layout-tools"><button aria-label={bottomOpen?'折叠教学区':'展开教学区'} onClick={()=>setBottomOpen(v=>!v)}>▤</button><button aria-label={diagnosisOpen?'折叠诊断区':'展开诊断区'} onClick={()=>setDiagnosisOpen(v=>!v)}>◈</button></div></div>
  {error&&<p className="station-error" role="alert">{error}<button aria-label="关闭提示" onClick={()=>setError('')}>×</button></p>}
  <nav className="mobile-jump" aria-label="工作区面板">{[['files','文件'],['code','代码'],['diagnosis','诊断'],['learning','学习']].map(([id,label])=><button key={id} aria-label={label+'面板'} aria-pressed={mobile===id} onClick={()=>setMobile(id)}>{label}</button>)}</nav>
  <div className="station-layout">
   <aside className="station-files" id="studio-files"><div className="files-heading"><h2>项目导航</h2><span className="eyebrow">EXPLORER</span></div>
    <label>打开项目<select disabled={!ready||busy} value={project?.id??''} onChange={e=>void choose(e.target.value)}><option value="">选择项目</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <details open={!project} className="project-management"><summary>新建项目</summary><form onSubmit={e=>{e.preventDefault();void create()}}><label>项目名称<input value={name} maxLength={80} onChange={e=>setName(e.target.value)} placeholder="例如：校园活动工具"/></label><button className="plain" disabled={!ready||busy||!name.trim()}>新建项目</button></form></details>
    {project&&<><p className="eyebrow">项目文件 / {Object.keys(project.files).length}</p><FileTree paths={Object.keys(project.files)} active={file} onSelect={selectFile}/><details className="new-file"><summary>＋ 添加文件</summary><form onSubmit={e=>{e.preventDefault();add()}}><label>新文件路径<input value={path} onChange={e=>setPath(e.target.value)} placeholder="src/helper.py"/></label><button className="plain" disabled={!path.trim()}>添加文件</button></form></details></>}
    <details className="storage-note"><summary>存储与备份</summary><p>项目保存在服务端，当前浏览器身份有效期 7 天。最多 30 个文件 / 50 KB。请导出备份；跨浏览器恢复和长期账号尚未接入。</p></details>
   </aside>
   <main className="station-code" id="studio-editor">{project?<><div className="station-filebar"><strong><span className="file-icon">{file.endsWith('.py')?'Py':'◇'}</span> {file}</strong><span>{dirty?'● 未保存':'✓ 已保存'}</span></div><div className="editor-breadcrumb">{project.name} <span>›</span> {file}</div><Suspense fallback={<p>加载编辑器…</p>}><Editor key={project.id+':'+file} code={code} onCursor={setCursor} onSelection={setSelection} pythonMode={file.endsWith('.py')} line={line} jump={jump} onChange={value=>setProject(p=>p?{...p,files:{...p.files,[file]:value}}:p)}/></Suspense><div className="station-actions"><button className="primary" disabled={busy||!dirty} onClick={()=>void save()}>{busy?'保存中…':'保存项目'}</button><button className="plain" onClick={exportProject}>导出项目 JSON</button><span role="status">{notice}</span></div></>:<div className="station-empty"><span className="empty-code-symbol">&lt;/&gt;</span><h2>在真实代码中理解编程</h2><p>创建或打开项目，在中央编辑器持续编写代码。错误证据、原因和修改方向会出现在右侧。</p><p>本地检查无需模型授权。需要深入分析时，再预览并开启模型权限。</p></div>}</main>
   <div className="mentor-splitter" role="separator" aria-label="调整导师宽度" aria-orientation="vertical" aria-valuenow={mentorWidth} aria-valuemin={300} aria-valuemax={500} tabIndex={0} onPointerDown={e=>e.currentTarget.setPointerCapture(e.pointerId)} onPointerMove={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))setMentorWidth(Math.max(300,Math.min(500,window.innerWidth-e.clientX)))}} onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();setMentorWidth(w=>Math.max(300,Math.min(500,w+(e.key==='ArrowLeft'?20:-20))))}}}/>
   <aside className="station-inspection" id="studio-mentor"><div className="panel-head"><h2 aria-label="实时诊断">ϟ 实时诊断</h2><span className="subtle">{checking?'检查中':'代码感知'}</span></div><div className="panel-content"><p className="inspection-summary" role="status">{!project?'打开文件后开始检查。':checking?'正在检查当前改动…':inspection?.summary}</p>{issue&&<DiagnosticCard issue={issue} onJump={()=>locate(issue.line)}/>} {feedback&&<p className="review-feedback">{feedback}</p>}{project&&<><button className="plain recheck-button" onClick={()=>setRetry(v=>v+1)}>重新检查</button><ProjectReview key={project.id} id={project.id} payload={{files:project.files,revision:project.revision,path:file,cursor_line:cursor}}/></>}<details className="capability-note"><summary>当前检查范围</summary><p>Python 本地语法检查，不执行代码。其他文件支持编辑保存。模型建议经引用校验仍需验证语义；项目测试、可审阅补丁与长期学习档案尚未接通。</p></details></div></aside>
   <div className="bottom-splitter" role="separator" aria-label="调整教学区高度" aria-orientation="horizontal" aria-valuenow={bottomHeight} aria-valuemin={130} aria-valuemax={360} tabIndex={0} onPointerDown={e=>e.currentTarget.setPointerCapture(e.pointerId)} onPointerMove={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))setBottomHeight(Math.max(130,Math.min(360,window.innerHeight-e.clientY)))}} onKeyDown={e=>{if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();setBottomHeight(h=>Math.max(130,Math.min(360,h+(e.key==='ArrowUp'?20:-20))))}}}/>
   <section className="station-bottom" id="studio-output"><div role="tablist" aria-label="工作台输出">{['问题','易错点','代码解析','学习记录'].map(t=><button key={t} id={'tab-'+t} role="tab" aria-selected={bottom===t} aria-controls="teaching-panel" onClick={()=>setBottom(t)}>{t}{t==='问题'&&issue&&<span className="issue-badge">1</span>}</button>)}</div><div id="teaching-panel" role="tabpanel" aria-labelledby={'tab-'+bottom}><TeachingPanel tab={bottom} inspection={inspection} events={events} selection={selection} file={file} onJump={locate}/></div></section>
  </div>
 </div>
}
