import { useEffect, useState } from 'react'
import { get, post } from './api'
import { SelfCheck } from './SelfCheck'
import type { Diagnosis } from './api'
const labels = { typing: '敲错或漏写', concept: '概念记得不牢', approach: '解题思路偏差', requirement: '题意或输入假设偏差', unsure: '暂时不确定' }
type Reason = keyof typeof labels
type Memory = { diagnosis_id: string; knowledge_id: string | null; reflection: {reason:Reason; explanation:string; updated_at:string} }

export function ReflectionPanel({ diagnosis }: { diagnosis: Diagnosis }) {
  const [reason, setReason] = useState<Reason>('unsure')
  const [explanation, setExplanation] = useState('')
  const [items, setItems] = useState<Memory[] | null>(null)
  const [editing, setEditing] = useState(diagnosis.id)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function refresh() { setItems((await get<{items:Memory[]}>('/learning-memory')).items) }
  useEffect(() => { let live=true; get<{items:Memory[]}>('/learning-memory').then(data => {if(live)setItems(data.items)}).catch(() => {if(live)setError('学习记忆暂时无法读取，请重试。')}); return () => {live=false} }, [])
  async function save(forget?: string) {
    if(busy) return
    setBusy(true); setError(''); setMessage('')
    try {
      await post('/diagnoses/' + (forget || editing) + '/reflection' + (forget ? '/forget' : ''), forget ? undefined : {reason, explanation})
      setMessage(forget ? '已删除这条自述。' : '已保存你的自述；下一次诊断会参考它。')
      if(forget === editing) {setEditing(diagnosis.id);setReason('unsure');setExplanation('')}
      await refresh()
    } catch { setError('操作未完成，请重试；输入已保留。') }
    finally {setBusy(false)}
  }
  const guide = diagnosis.coaching
  return <div className="reflection-panel">
    {guide && <><h3>这次为什么出错？</h3><p>{guide.why}</p><h4>建议怎样改</h4><p>{guide.fix}</p>
      <h4>先问自己一个问题</h4><p className="self-check">{guide.question}</p><p>{guide.next_action}</p>
      <small>依据：本地审核指导 · 同知识点 {guide.history.count} 条自述。{guide.caution}</small></>}
    {guide?.self_check_available && <SelfCheck key={diagnosis.id} id={diagnosis.id} />}
    <details className="reflection-form"><summary>记录我的原因与思路</summary>
      <p>只记录学习相关信息，请勿填写姓名、联系方式或密钥。自述不等于已证实的错因。</p>
      <label>我认为更接近哪种原因<select value={reason} onChange={e=>setReason(e.target.value as Reason)}>{Object.entries(labels).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
      <label>当时的思路与下次提醒<textarea value={explanation} maxLength={600} rows={3} onChange={e=>setExplanation(e.target.value)} placeholder="例如：我以为 stop 包含在范围内，下次先手算最后一个下标。" /></label>
      <button className="primary" disabled={busy} onClick={()=>void save()}>{busy?'正在保存…':editing === diagnosis.id?'保存本次复盘':'更新这条复盘'}</button>
      {editing !== diagnosis.id && <button className="plain" onClick={()=>{setEditing(diagnosis.id);setReason('unsure');setExplanation('')}}>返回本次诊断</button>}
    </details>
    {message && <p role="status">{message}</p>}{error && <p role="alert" className="error">{error}<button className="plain" onClick={()=>void refresh().then(()=>setError('')).catch(()=>setError('仍无法读取，请稍后重试。'))}>重试读取</button></p>}
    <details><summary>查看学习记忆（{items === null ? '读取中' : items.length}）</summary><p className="subtle">当前浏览器身份下保存；清除身份或服务重启后可能无法找回。不会据此推断性格或智力。</p>
      {items?.map(item=><article className="memory-item" key={item.diagnosis_id}><strong>{labels[item.reflection.reason]}</strong><small>{item.knowledge_id ?? '待确认知识点'} · 学习者自述</small><p>{item.reflection.explanation || '未填写具体说明'}</p>
        <button className="plain" disabled={busy} onClick={()=>{setEditing(item.diagnosis_id);setReason(item.reflection.reason);setExplanation(item.reflection.explanation); const panel=document.querySelector<HTMLDetailsElement>('.reflection-form'); if(panel)panel.open=true}}>纠正这条记录</button>
        <button className="plain" disabled={busy} onClick={()=>void save(item.diagnosis_id)}>删除这条自述</button></article>)}
    </details>
  </div>
}
