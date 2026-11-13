import {useEffect,useRef,useState} from 'react'
import {get,post} from './api'
import {streamReview,type WorkflowEvent} from './review-stream'
import {applyReviewedPatches,undoReviewedPatch,requestFingerprint,type AppliedPatch} from './review-state'

type Payload={files:Record<string,string>;revision:number;path:string;cursor_line:number;language?:'auto'|'python'|'text'}
type Preview={snippets:{path:string;line:number;quote:string}[];buffer_hash:string;status?:string;reason?:string}
type Patch={path:string;line:number;before:string;after:string;reason:string}
type Teaching={summary:string;root_cause:string;mechanism:string;example:string;alternatives:string[];prevention:string;uncertainty:string}
type Result={status:string;mode:string;reason?:string;failure_kind?:string;workflow_mode?:string;cache_hit?:boolean;tool_trace?:{name:string;status:string}[];review?:{teaching?:Teaching|null;patches?:Patch[];explanation:string;hints:string[];citations:{path:string;line:number;quote:string}[]}|null}
const messages:Record<string,string>={disabled:'模型功能未启用：当前仅提供本地静态分析。',limited:'已达到调用限额，请稍后手动重试。',timeout:'模型响应超时，自动分析已暂停；可重新预览后重试。',failed:'模型结果未通过校验或服务异常，没有生成可用建议。',blocked:'检测到疑似敏感内容，已阻止发送。'}

export function ProjectReview({id,payload,onApplyFiles}:{id:string;payload:Payload;onApplyFiles?:(files:Record<string,string>)=>void}){
 const [allowed,setAllowed]=useState(false),[ready,setReady]=useState(false),[busy,setBusy]=useState(false)
 const [automatic,setAutomatic]=useState(false),[queued,setQueued]=useState(false)
 const [preview,setPreview]=useState<Preview|null>(null),[result,setResult]=useState<Result|null>(null)
 const [error,setError]=useState(''),[question,setQuestion]=useState('')
 const [phase,setPhase]=useState(''),[applied,setApplied]=useState<AppliedPatch|null>(null)
 const resultFingerprint=useRef('')
 const request=useRef<AbortController|null>(null)
 const previewPayload=useRef<(Payload&{request:string})|null>(null)
 const latest=useRef({...payload,request:question})
 latest.current={...payload,request:question}
 // Cursor movement and saving the identical buffer do not create a new code version.
 const fingerprint=requestFingerprint({id,files:payload.files,path:payload.path,language:payload.language,question})
 const currentFingerprint=useRef(fingerprint);currentFingerprint.current=fingerprint
 const attempted=useRef(new Set<string>()),lastCall=useRef(0)

 useEffect(()=>{let live=true;get<{allow_external:boolean}>('/projects/'+id+'/privacy').then(r=>{if(live){setAllowed(r.allow_external);setReady(true)}}).catch(()=>{if(live)setError('无法读取项目隐私设置。')});return()=>{live=false}},[id])
 useEffect(()=>{
  request.current?.abort();setPreview(null);previewPayload.current=null;setResult(null);setError('');setBusy(false)
  return()=>request.current?.abort()
 },[fingerprint])
 function stop(){request.current?.abort();setBusy(false);setAutomatic(false);setQueued(false)}
 async function privacy(value:boolean){
  stop();setPreview(null);setResult(null);setReady(false)
  try{await post('/projects/'+id+'/privacy',{allow_external:value});setAllowed(value);setError('')}
  catch{setError('隐私设置未保存，请重试。')}
  finally{setReady(true)}
 }
 async function run(send:boolean,auto=false,useTools=true){
  const body=send&&!auto?previewPayload.current:latest.current
  if(!body)return
  request.current?.abort()
  const token=currentFingerprint.current
  const controller=new AbortController();request.current=controller;setBusy(true);setQueued(false);setError('');setPhase('准备授权代码快照…')
  if(send){lastCall.current=Date.now();attempted.current.add(token);if(attempted.current.size>50)attempted.current.delete(attempted.current.values().next().value!)}
  try{
   const onEvent=(event:WorkflowEvent)=>{if(controller.signal.aborted||currentFingerprint.current!==token)return;const d=event.data;setPhase(event.event==='model-turn'?`模型分析 · 第 ${d.turn} 轮`:event.event==='tool-start'?`正在读取项目证据 · ${d.name}`:event.event==='tool-result'?`工具返回 · ${d.name} · ${d.status}`:event.event==='cache-hit'?'复用当前代码版本的已校验结果':event.event==='completed'?'分析完成':'已接收当前代码快照')}
   const data=send?await streamReview<Preview&Result>(id,{...body,mode:'collaborate',use_tools:useTools},controller.signal,onEvent):await post<Preview&Result>('/projects/'+id+'/review-preview',{...body,mode:'collaborate'},controller.signal)
   if(controller.signal.aborted||currentFingerprint.current!==token)return
   if(send){resultFingerprint.current=token;setResult(data);if(data.status!=='accepted')setAutomatic(false)}
   else {setPreview(data);previewPayload.current=body}
  }catch(e){if(!controller.signal.aborted&&currentFingerprint.current===token){setError(String(e));setAutomatic(false)}}
  finally{if(!controller.signal.aborted&&currentFingerprint.current===token)setBusy(false)}
 }
 useEffect(()=>{
  if(!ready||!allowed||!automatic||attempted.current.has(fingerprint)||!payload.files[payload.path]?.trim()){setQueued(false);return}
  setQueued(true)
  const timer=setTimeout(()=>{if(!attempted.current.has(fingerprint))void run(true,true)},Math.max(1800,30000-(Date.now()-lastCall.current)))
  return()=>{clearTimeout(timer)}
 },[fingerprint,allowed,automatic,ready])

 function applyPatches(){if(resultFingerprint.current!==currentFingerprint.current){setError('代码已变化，请重新分析。');return}const patches=result?.review?.patches;if(!patches?.length)return;try{const files=applyReviewedPatches(payload.files,patches);setApplied({before:{...payload.files},after:files});onApplyFiles?.(files);setResult(null)}catch(e){setError(String(e))}}
 function undo(){if(!applied)return;try{onApplyFiles?.(undoReviewedPatch(payload.files,applied));setApplied(null)}catch(e){setError(String(e))}}
 return <section className="project-review" aria-label="模型分析">
  <div className="review-heading"><h3>深入分析</h3><span className="subtle">项目上下文 · AI</span></div>
  <label className="question-label">想进一步了解什么？<textarea maxLength={1000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="例如：详细解释参数与返回值，或请简洁说明修改方法" rows={2}/></label>
  <div className="depth-actions">{['讲详细一点','给个例子','深入分析'].map(q=><button key={q} onClick={()=>setQuestion(q+'：请结合当前文件与关联文件说明，并区分推断和实际执行。')}>{q}</button>)}</div>
  <details className="privacy-settings"><summary>模型权限与自动分析 <span>{allowed?'已授权':'未授权'}</span></summary>
   <p>授权范围：当前项目代码、你的问题、真实学习记录和匹配当前版本的执行证据。模型可按需读取项目内片段，最多 3 轮分析、6 次只读工具调用；预览展示初始片段。自动分析每次间隔至少 30 秒，可能产生模型费用。</p>
   <label><input type="checkbox" checked={allowed} disabled={!ready} onChange={e=>void privacy(e.target.checked)}/>允许本项目向已配置模型发送所选上下文</label>
   <label><input type="checkbox" checked={automatic} disabled={!ready||!allowed} onChange={e=>{if(!e.target.checked)stop();else setAutomatic(true)}}/>代码稳定后自动分析（本次打开）</label>
   <p className="subtle">敏感内容检测并不完备，请先检查代码。撤销不能收回已发送内容，取消等待不能保证上游停止计费。</p>
  </details>
  <button className="plain" disabled={!ready||busy} onClick={()=>void run(false)}>预览审查上下文</button>
  {queued&&<p role="status">等待代码稳定或调用冷却…</p>}
  {preview&&(preview.status==='blocked'?<p role="alert">{preview.reason}</p>:<details open={!result}><summary>待发送片段 · {preview.snippets.length} 行</summary><pre>{preview.snippets.map(s=>s.path+':'+s.line+' '+s.quote).join('\n')}</pre><button className="primary" disabled={!allowed||busy||!preview.snippets.length} onClick={()=>void run(true)}>确认发送并请求 AI 指导</button></details>)}
  {busy&&<p role="status">{phase}<button className="plain" onClick={stop}>取消等待</button></p>}
  {applied&&<div role="status"><p>修改已应用到草稿，本地检查会自动复查。运行行为请使用“验证当前入口”；尚未运行完整项目测试。</p><button onClick={undo}>撤回上次 AI 修改</button></div>}
  {error&&<p role="alert">{error} 本地编辑和检查仍可继续。</p>}
  {result&&<div className="model-result" role="status"><p className="eyebrow">来源：{result.mode==='simulated'?'模拟模型':result.mode==='live'?'真实模型调用':'本地模式'} · 状态：{result.status}</p>
   {!result.review&&<p>{result.reason??messages[result.status]??messages.failed}</p>}
   {result.failure_kind==='tools-unsupported'&&<><p>当前服务不支持原生工具调用，可使用已有片段进行单轮分析。</p><button disabled={busy} onClick={()=>void run(true,true,false)}>改用单轮分析（重新请求）</button></>}
   {result.workflow_mode&&<p className="subtle">{result.cache_hit?'当前版本缓存 · ':''}{result.workflow_mode==='native-tools'?'原生工具工作流':result.workflow_mode==='text-fallback'?'模型无工具接口 · 单轮降级':'单轮文本分析'}{result.tool_trace?.length?` · 实际工具调用 ${result.tool_trace.length} 次`:''}</p>}
   {result.review?.teaching&&<><p>{result.review.teaching.summary}</p><details onToggle={e=>{if(e.currentTarget.open)void post('/projects/'+id+'/learning-action',{path:payload.path,action:'hint-viewed',code:payload.files[payload.path]}).catch(()=>{})}}><summary>详细解释：为什么这样修改</summary>{([['根因',result.review.teaching.root_cause],['语言机制',result.review.teaching.mechanism],['例子与证据',result.review.teaching.example],['验证与预防',result.review.teaching.prevention],['尚不确定',result.review.teaching.uncertainty]]).map(([title,text])=>text&&<div key={title}><h4>{title}</h4><p className="model-explanation">{text}</p></div>)}{result.review.teaching.alternatives.map((text,i)=><p key={i}>{text}</p>)}</details></>}
   {result.review&&<><p className="subtle">模型建议 · 尚未通过运行验证</p><p className="model-explanation">{result.review.explanation}</p>{result.review.hints.map((h,i)=><details key={i} open={i===0}><summary>{['修改方向','更多建议','进一步验证与提醒'][i]??'进一步说明'}</summary><p className="model-explanation">{h}</p></details>)}{!!result.review.patches?.length&&<details open><summary>审阅建议修改 · 尚未应用</summary>{result.review.patches.map((p,i)=><div key={i}><p>{p.path}:{p.line} · {p.reason}</p><pre className="patch-before">− {p.before}</pre><pre className="patch-after">+ {p.after}</pre></div>)}<button disabled={!onApplyFiles} onClick={applyPatches}>批准并应用到草稿</button></details>}<details><summary>引用的代码证据</summary>{result.review.citations.map((c,i)=><p key={i}>{c.path}:{c.line} <code>{c.quote}</code></p>)}</details></>}
  </div>}
 </section>
}
