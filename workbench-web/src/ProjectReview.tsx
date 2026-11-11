import {useEffect,useRef,useState} from 'react'
import {get,post} from './api'
type Payload={files:Record<string,string>;revision:number;path:string;cursor_line:number}
type Preview={snippets:{path:string;line:number;quote:string}[];buffer_hash:string}
type Result={status:string;mode:string;review?:{explanation:string;hints:string[];citations:{path:string;line:number;quote:string}[]}|null}
export function ProjectReview({id,payload}:{id:string;payload:Payload}){
 const [allowed,setAllowed]=useState(false),[ready,setReady]=useState(false),[busy,setBusy]=useState(false)
 const [preview,setPreview]=useState<Preview|null>(null),[result,setResult]=useState<Result|null>(null)
 const [error,setError]=useState(''),[mode,setMode]=useState('mentor')
 const request=useRef<AbortController|null>(null)
 const fingerprint=JSON.stringify(payload)
 useEffect(()=>{let live=true;get<{allow_external:boolean}>('/projects/'+id+'/privacy').then(r=>{if(live){setAllowed(r.allow_external);setReady(true)}}).catch(()=>{if(live)setError('无法读取项目隐私设置。')});return()=>{live=false}},[id])
 useEffect(()=>{request.current?.abort();setPreview(null);setResult(null);setBusy(false);return()=>request.current?.abort()},[fingerprint,mode])
 async function privacy(value:boolean){request.current?.abort();setPreview(null);setResult(null);setBusy(false);setReady(false);try{await post('/projects/'+id+'/privacy',{allow_external:value});setAllowed(value)}catch{setError('隐私设置未保存。')}finally{setReady(true)}}
 async function run(send:boolean){if(busy)return;const controller=new AbortController();request.current=controller;setBusy(true);setError('');try{
  const data=await post<Preview&Result>('/projects/'+id+(send?'/review':'/review-preview'),{...payload,mode},controller.signal)
  if(!controller.signal.aborted){if(send)setResult(data);else setPreview(data)}
 }catch{if(!controller.signal.aborted)setError('请求未完成，本地编辑和检查仍可继续。')}finally{if(!controller.signal.aborted)setBusy(false)}}
 return <section className="project-review"><h3>项目 AI 导师</h3><label>指导模式<select value={mode} onChange={e=>setMode(e.target.value)}><option value="mentor">导师：提问与提示</option><option value="collaborate">协作：解释修改方向</option><option value="engineering">工程：审查与验证建议</option></select></label>
 <p>只在你确认后发送下方片段。可能产生模型费用；当前不自动应用修改。代码和注释也可能包含秘密，请先检查预览。</p>
 <label><input type="checkbox" checked={allowed} disabled={!ready} onChange={e=>void privacy(e.target.checked)}/>允许本项目向已配置模型发送所选上下文</label>
 <button className="plain" disabled={!ready||busy} onClick={()=>void run(false)}>预览审查上下文</button>
 {preview&&<details open><summary>待发送片段 · {preview.snippets.length} 行</summary><pre>{preview.snippets.map(s=>s.path+':'+s.line+' '+s.quote).join('\n')}</pre><button className="primary" disabled={!allowed||busy} onClick={()=>void run(true)}>确认发送并请求 AI 指导</button></details>}
 {busy&&<p role="status">请求处理中…<button className="plain" onClick={()=>{request.current?.abort();setBusy(false)}}>取消等待</button></p>}
 {error&&<p role="alert">{error}</p>}
 {result&&<div role="status"><p>来源：{result.mode==='simulated'?'模拟模型':result.mode==='live'?'真实模型调用':'本地模式'} · 状态：{result.status}</p>{result.review&&<><p>模型建议 · 尚未通过运行验证</p><p>{result.review.explanation}</p>{result.review.hints.map((h,i)=><details key={i}><summary>提示 {i+1}</summary><p>{h}</p></details>)}{result.review.citations.map((c,i)=><p key={i}>{c.path}:{c.line} <code>{c.quote}</code></p>)}</>}</div>}
 </section>
}
