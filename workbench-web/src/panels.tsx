import { ReflectionPanel } from './ReflectionPanel'
import { useRef } from 'react'
import type { FormEvent } from 'react'
import type { Attempt, Challenge, Diagnosis, Hint, Skill } from './api'
import { Icon } from './icons'

const stageNames: Record<string, string> = {
  analysis: '本地分析', retrieval: '课程检索', model: '模型解释', practice: '选定变式',
}
const statusNames: Record<string, string> = {
  confirmed: '识别到条件性错因', 'syntax-error': '语法需修正', uncertain: '证据不足',
  matched: '已召回', empty: '无匹配', accepted: '校验通过', invalid: '输出未通过校验',
  timeout: '超时 · 已降级', failed: '请求失败 · 已降级', unconfigured: '未配置 · 已降级',
  disabled: '本地模式', limited: '限额 · 已降级', selected: '已选定',
}
const outcomeNames = { incorrect: '需要复练', assisted: '辅助通过', independent: '独立通过' }
const actions = {
  repeat: '接下来围绕同一错因换题复练。',
  transfer: '接下来做一道不同题面的复测。',
  verified: '已积累两道不同题的独立通过证据。',
}

export function DiagnosisPanel({ result, stale, pending, jump }: {
  result: Diagnosis | null; stale: boolean; pending: boolean; jump: () => void
}) {
  const sourceCards = useRef(new Map<string, HTMLDetailsElement>())
  return <section className="evidence" aria-labelledby="evidence-title" aria-busy={pending}>
    <div className="panel-head"><Icon name="scan" /><h2 id="evidence-title" tabIndex={-1}>诊断证据</h2><span className="section-index">02</span></div>
    {!result ? <div className="empty evidence-empty">
      <div className="empty-symbol"><Icon name="scan" /></div>
      <span className="eyebrow">EVIDENCE FIRST</span>
      <strong>{pending ? '正在等待诊断结果' : '理解错误，从证据开始'}</strong>
      <p>{pending ? '结果返回后显示实际完成的步骤。' : '提交左侧代码，查看触发条件、具体反例和修正依据。'}</p>
      <div className="evidence-outline"><span>定位代码</span><Icon name="arrow" /><span>检验反例</span><Icon name="arrow" /><span>关联知识</span></div>
    </div> :
      <div className="panel-content" tabIndex={0} role="region" aria-label="诊断详情，可滚动阅读">
        <div className="result-summary"><span className={`tag ${result.status === 'confirmed' ? 'warm' : ''}`}>{statusNames[result.status]}</span><span className="subtle">{result.evidence.length} 条证据</span></div>
        {pending && <p className="notice">新诊断尚未返回，下方保留上一次结果。</p>}
        {stale && <p className="notice">当前代码已改动，以下证据属于上次提交。</p>}
        {result.status === 'uncertain' && <p className="uncertain">目前无法用已覆盖的规则确认错因。可以选一个示例继续体验，或检查是否保留了完整函数。</p>}
        {result.evidence.map(item => <article className="evidence-card" key={item.id}>
          <div className="evidence-heading"><span className="eyebrow">触发条件</span>{item.line != null && <button className="line-link" onClick={jump} disabled={stale}>第 {item.line} 行<Icon name="arrow" /></button>}</div>
          <p>{item.condition}</p>
          {item.counterexample && <dl className="comparison">
            <div className="counterexample"><dt>反例输入</dt><dd><code>{item.counterexample}</code></dd></div>
            <div className="observed"><dt>按代码推导</dt><dd><code>{item.observed}</code></dd></div>
            <div className="expected"><dt>预期行为</dt><dd><code>{item.expected}</code></dd></div>
          </dl>}
          {item.correction && <div className="correction"><span className="eyebrow">修正依据</span><p>{item.correction}</p></div>}
        </article>)}
        <ReflectionPanel key={result.id} diagnosis={result} />
        {result.annotation && <div className="model-note">
          <span className="eyebrow">模型解释</span><p>{result.annotation.explanation}</p>
          <div className="citation-links">{result.annotation.citations.map((id, index) =>
            <a key={id} href={`#card-${id}`} onClick={() => {
              const source = sourceCards.current.get(id)
              if (source) source.open = true
            }}>证据 {index + 1}</a>)}</div>
        </div>}
        {!!result.cards.length && <p className="eyebrow source-heading"><Icon name="book" />关联课程</p>}
        {result.cards.map(card => <details className="source-card" id={`card-${card.id}`} key={card.id}
          ref={element => { if (element) sourceCards.current.set(card.id, element); else sourceCards.current.delete(card.id) }}>
          <summary>{card.title} <span>v{card.version}</span></summary>
          <p>{card.content}</p><a href={card.source} target="_blank" rel="noreferrer">阅读 Python 文档 ↗</a>
        </details>)}
        <details className="trace"><summary>本次已完成的工作步骤 <span>{result.events.length}</span></summary>
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
  return <section className="practice" aria-labelledby="practice-title">
    <div className="panel-head"><Icon name="terminal" /><h2 id="practice-title" tabIndex={-1}>变式复测</h2>
      <span className="section-meta">{challenge ? '确定性评分' : '诊断后解锁'}</span><span className="section-index">03</span>
    </div>
    {!challenge ? <div className="empty practice-empty"><span className="empty-bracket" aria-hidden="true">[ ? ]</span><div><strong>理解之后，独立试一次。</strong><p>诊断匹配变式练习；作答和提示使用将分别记录。</p></div></div> :
      <div className="panel-content practice-content">
        <div className="exercise-body"><div className="exercise-heading"><span className="eyebrow">TRANSFER CHECK</span><span className="tag">{attempt ? '已评分' : '待作答'}</span></div>
          <h3>{challenge.title}</h3><p className="exercise-prompt">{challenge.prompt}</p>
        </div>
        {!attempt && <form onSubmit={submit}>
          <label htmlFor="answer">填写答案 <span>输入一个整数</span></label>
          <div className="answer-row">
            <input id="answer" value={answer} onChange={event => setAnswer(event.target.value)} inputMode="text" placeholder="你的推导结果" autoComplete="off" maxLength={80} />
            <button className="primary" disabled={!!action || !answer.trim()}>{action === 'answer' ? '正在评分…' : '提交答案'}<Icon name="arrow" /></button>
          </div>
          <button className="hint-button" type="button" disabled={!!action || (hint?.used ?? 0) >= challenge.hint_count} onClick={onHint}>
            <Icon name="book" />{action === 'hint' ? '正在获取提示…' : '查看下一条提示'}<span>{hint?.used ?? 0} / {challenge.hint_count}</span>
          </button>
          <p className="hint-note">查看提示后答对，将记录为“提示后通过”。</p>
        </form>}
        {hint && <ol className="hints">{hint.hints.map((text, index) => <li key={text}><span>提示 {index + 1}</span>{text}</li>)}</ol>}
        {attempt && <div className={`feedback ${attempt.outcome}`} role="status">
          <div className="feedback-heading"><span aria-hidden="true">{attempt.outcome === 'incorrect' ? '↻' : '✓'}</span><strong>{attempt.outcome === 'assisted' && attempt.hints_used > 0 ? '提示后通过' : outcomeNames[attempt.outcome]}</strong></div>
          {attempt.outcome === 'assisted' && attempt.hints_used === 0 && <p>本题答案曾在题面或先前作答中出现，不计作独立掌握证据。</p>}
          <p>{attempt.feedback}</p><p className="next-action">{actions[attempt.recommendation]}</p>
          <button className="primary" disabled={!!action} onClick={onRetry}>{action === 'retry' ? '正在准备…' : '重新挑战'}<Icon name="arrow" /></button>
        </div>}
        {error && <p role="alert" className="error">{error}</p>}
      </div>}
  </section>
}

export function ProfilePanel({ skills, loading, error, onRetry }: {
  skills: Skill[] | null; loading: boolean; error: string; onRetry: () => void
}) {
  const independent = (skills ?? []).reduce((sum, skill) => sum + skill.independent, 0)
  const assisted = (skills ?? []).reduce((sum, skill) => sum + skill.assisted, 0)
  return <section className="profile" aria-labelledby="profile-title">
    <div className="panel-head"><Icon name="chart" /><h2 id="profile-title" tabIndex={-1}>学习记录</h2><span className="section-index">04</span></div>
    {loading && <p className="profile-loading" role="status">{skills ? '正在刷新学习记录…' : '正在加载学习记录…'}</p>}
    {error && <div className="profile-error"><p className="error" role="alert">{error}{skills && '下方保留上次成功读取的记录。'}</p><button className="plain" disabled={loading} onClick={onRetry}>重试加载</button></div>}
    {skills !== null && <><div className="profile-overview"><div><strong>{independent.toString().padStart(2, '0')}</strong><span>独立作答通过</span></div><div><strong>{assisted.toString().padStart(2, '0')}</strong><span>辅助通过</span></div><p>一次答对<br />≠ 完全掌握</p></div>
    {!skills.length ? <div className="empty compact">还没有学习记录。完成诊断和复测后，这里会显示你的掌握证据。</div> :
      <div className="skill-grid">{skills.map(skill => <article key={skill.knowledge_id}>
        <div className="skill-heading"><strong>{skill.label}</strong><span>{Math.min(2, skill.distinct_independent)} / 2 题</span></div>
        <div className="meter" role="img" aria-label={`${Math.min(2, skill.distinct_independent)} 道不同题独立通过，复测目标 2 道`}>
          {[0, 1].map(index => <span className={skill.distinct_independent > index ? 'filled' : ''} key={index} />)}
        </div>
        <p><span>{skill.independent} 次独立通过</span><span>{skill.assisted} 次辅助通过</span><span>{skill.incorrect} 次未通过</span></p>
      </article>)}<p className="profile-note">每个知识点以两道不同题的独立通过作为复测目标。辅助通过包含使用提示或已见过答案的情况。</p></div>}</>}
  </section>
}
