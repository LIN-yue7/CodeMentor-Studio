
import type { FormEvent } from 'react'
import type { Attempt, Challenge, Diagnosis, Hint, Skill } from './api'

const stageNames: Record<string, string> = {
  analysis: '本地分析', retrieval: '课程检索', model: '模型解释', practice: '选定变式',
}
const statusNames: Record<string, string> = {
  confirmed: '识别到条件性错因', 'syntax-error': '语法需修正', uncertain: '证据不足',
  matched: '已召回', empty: '无匹配', accepted: '校验通过', invalid: '输出未通过校验',
  timeout: '超时 · 已降级', failed: '请求失败 · 已降级', unconfigured: '未配置 · 已降级',
  disabled: '本地模式', limited: '限额 · 已降级', selected: '已选定',
}
const outcomeNames = { incorrect: '需要复练', assisted: '提示后通过', independent: '独立通过' }
const actions = {
  repeat: '接下来围绕同一错因换题复练。',
  transfer: '接下来做一道不同题面的复测。',
  verified: '已积累两道不同题的独立通过证据。',
}

export function DiagnosisPanel({ result, stale, jump }: {
  result: Diagnosis | null; stale: boolean; jump: () => void
}) {
  return <section className="panel evidence" aria-labelledby="evidence-title">
    <div className="panel-head"><span className="step">02</span><div>
      <h2 id="evidence-title">诊断证据</h2><p>从触发条件追到修正依据</p>
    </div></div>
    {!result ? <div className="empty"><strong>证据将在这里出现</strong><p>运行一次诊断查看错误行、反例与课程来源。</p></div> :
      <div className="panel-content">
        <div className={`tag ${result.status === 'confirmed' ? 'warm' : ''}`}>{statusNames[result.status]}</div>
        {stale && <p className="notice">当前代码已改动，以下证据属于上次提交。</p>}
        {result.status === 'uncertain' && <p>目前无法用已覆盖的规则确认错因。可以选一个示例继续体验，或检查是否保留了完整函数。</p>}
        {result.evidence.map(item => <article className="evidence-card" key={item.id}>
          {item.line != null && <button className="line-link" onClick={jump} disabled={stale}>第 {item.line} 行</button>}
          <p>{item.condition}</p>
          {item.counterexample && <dl className="comparison">
            <div><dt>反例输入</dt><dd><code>{item.counterexample}</code></dd></div>
            <div><dt>按代码推导</dt><dd><code>{item.observed}</code></dd></div>
            <div><dt>预期行为</dt><dd><code>{item.expected}</code></dd></div>
          </dl>}
          {item.correction && <p className="correction">{item.correction}</p>}
        </article>)}
        {result.annotation && <div className="model-note">
          <strong>模型解释</strong><p>{result.annotation.explanation}</p>
          <div className="citation-links">{result.annotation.citations.map((id, index) =>
            <a key={id} href={`#card-${id}`}>证据 {index + 1}</a>)}</div>
        </div>}
        {result.cards.map(card => <details className="source-card" id={`card-${card.id}`} key={card.id}>
          <summary>{card.title} <span>课程卡 v{card.version}</span></summary>
          <p>{card.content}</p><a href={card.source} target="_blank" rel="noreferrer">阅读 Python 文档 ↗</a>
        </details>)}
        <details className="trace"><summary>本次已完成的工作步骤</summary>
          <ol>{result.events.map(event => <li key={event.stage}>
            <span>{stageNames[event.stage]}</span><span>{statusNames[event.status] ?? event.status}</span>
            {event.elapsed_ms !== undefined && <small>{Math.round(event.elapsed_ms)} ms</small>}
          </li>)}</ol>
        </details>
      </div>}
  </section>
}

export function PracticePanel({ challenge, hint, attempt, answer, setAnswer, action, onHint, onSubmit, onRetry, error }: {
  challenge: Challenge | null; hint: Hint | null; attempt: Attempt | null; answer: string
  setAnswer: (value: string) => void; action: string | null; onHint: () => void; onSubmit: () => void
  onRetry: () => void; error: string
}) {
  function submit(event: FormEvent) { event.preventDefault(); onSubmit() }
  return <section className="panel practice" aria-labelledby="practice-title">
    <div className="panel-head"><span className="step">03</span><div>
      <h2 id="practice-title">变式复测</h2><p>用作答验证理解，结果计入学习记录</p>
    </div></div>
    {!challenge ? <div className="empty"><strong>等待诊断匹配练习</strong><p>题目由审核过的模板提供，按预设答案判分。</p></div> :
      <div className="panel-content">
        <div className="tag">填写整数</div><h3>{challenge.title}</h3><p>{challenge.prompt}</p>
        {!attempt && <form onSubmit={submit}>
          <label htmlFor="answer">填写答案</label>
          <div className="answer-row">
            <input id="answer" value={answer} onChange={event => setAnswer(event.target.value)} autoComplete="off" maxLength={80} />
            <button className="primary" disabled={!!action || !answer.trim()}>提交答案</button>
          </div>
          <button className="plain" type="button" disabled={!!action || (hint?.used ?? 0) >= challenge.hint_count} onClick={onHint}>
            查看下一条提示 <span>{hint?.used ?? 0}/{challenge.hint_count}</span>
          </button>
        </form>}
        {hint && <ol className="hints">{hint.hints.map(text => <li key={text}>{text}</li>)}</ol>}
        {attempt && <div className="feedback" role="status">
          <strong>{outcomeNames[attempt.outcome]}</strong><p>{attempt.feedback}</p><p>{actions[attempt.recommendation]}</p>
          <button className="primary" disabled={!!action} onClick={onRetry}>重新挑战</button>
        </div>}
        {error && <p role="alert" className="error">{error}</p>}
      </div>}
  </section>
}

export function ProfilePanel({ skills }: { skills: Skill[] }) {
  return <section className="panel profile" aria-labelledby="profile-title">
    <div className="panel-head"><span className="step">04</span><div>
      <h2 id="profile-title">学习记录</h2><p>按知识点累计作答证据</p>
    </div></div>
    {!skills.length ? <div className="empty compact">完成诊断和复测后查看你的记录。</div> :
      <div className="skill-grid">{skills.map(skill => <article key={skill.knowledge_id}>
        <strong>{skill.label}</strong>
        <div className="meter" role="img" aria-label={`${Math.min(2, skill.distinct_independent)} 道不同题独立通过，复测目标 2 道`}>
          {[0, 1].map(index => <span className={skill.distinct_independent > index ? 'filled' : ''} key={index} />)}
        </div>
        <p><span>{skill.independent} 次独立通过</span><span>{skill.assisted} 次提示后通过</span><span>{skill.incorrect} 次未通过</span></p>
      </article>)}</div>}
  </section>
}
