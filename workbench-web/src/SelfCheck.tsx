import { useEffect, useState } from 'react'
import { get, post } from './api'
type Result = {choice:string; correct:boolean; feedback:string}
type Question = {available:boolean; prompt?:string; options?:{id:string;label:string}[]; result?:Result|null}
export function SelfCheck({id}:{id:string}) {
  const [question,setQuestion]=useState<Question|null>(null)
  const [choice,setChoice]=useState('')
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const path='/diagnoses/'+id+'/self-check'
  async function load(){setError('');try{setQuestion(await get<Question>(path))}catch{setError('自查暂时无法读取。')}}
  useEffect(()=>{let live=true;get<Question>(path).then(q=>{if(live)setQuestion(q)}).catch(()=>{if(live)setError('自查暂时无法读取。')});return()=>{live=false}},[path])
  async function submit(){if(busy||!choice)return;setBusy(true);setError('');try{
    const result=await post<Result>(path,{choice});setQuestion(q=>q?{...q,result}:q)
  }catch{setError('自查未提交成功，请重试；可重新读取核对是否已保存。')}finally{setBusy(false)}}
  if(question?.available===false)return null
  return <details className="selfcheck"><summary>用一道自查核对理解</summary>
    <p className="subtle">这是看过讲解后的自查，不计为独立掌握。每次诊断只保留首次答案，后续练习请进入变式复测。</p>
    {error&&<p role="alert">{error}<button className="plain" disabled={busy} onClick={()=>void load()}>重新读取自查</button></p>}
    {!question&&!error&&<p role="status">正在读取自查题…</p>}
    {question?.available&&<><fieldset disabled={busy||!!question.result}><legend>{question.prompt}</legend>
      {question.options?.map(option=><label key={option.id}><input type="radio" name={'selfcheck-'+id} value={option.id} checked={(question.result?.choice??choice)===option.id} onChange={()=>setChoice(option.id)}/>{option.label}</label>)}
    </fieldset>
    {!question.result&&<button className="primary" disabled={busy||!choice} onClick={()=>void submit()}>{busy?'正在核对…':'提交概念自查'}</button>}
    {question.result&&<p role="status" className="selfcheck-result">{question.result.feedback}</p>}</>}
  </details>
}
