
import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { get, post } from './api'
import type { Attempt, Challenge, Diagnosis, Hint, Mode, Skill } from './api'
import { examples } from './examples'
import { DiagnosisPanel, PracticePanel, ProfilePanel } from './panels'
import { Icon } from './icons'
import './styles.css'

const Editor = lazy(() => import('./Editor'))
type Goal = '' | 'sum-all' | 'first-or-empty'
const modeNames = { local: '本地证据模式', live: '已启用真实模型', simulated: '模拟模型模式' }

function App() {
  const [code, setCode] = useState<string>(examples[0].code)
  const [goal, setGoal] = useState<Goal>(examples[0].goal)
  const [submittedGoal, setSubmittedGoal] = useState<Goal>('')
  const [mode, setMode] = useState<Mode | null>(null)
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [submittedCode, setSubmittedCode] = useState('')
  const [challenge, setChallenge] = useState<Challenge | null>(null)
  const [hint, setHint] = useState<Hint | null>(null)
  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [answer, setAnswer] = useState('')
  const [skills, setSkills] = useState<Skill[] | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)
  const [jump, setJump] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [profileError, setProfileError] = useState('')
  const [practiceError, setPracticeError] = useState('')
  const [pending, setPending] = useState(false)
  const [action, setAction] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const session = useRef<Promise<unknown> | null>(null)
  const diagnosisKey = useRef<{ value: string; id: string } | null>(null)
  const attemptKey = useRef<{ value: string; id: string } | null>(null)
  const busyPractice = useRef(false)
  const stale = diagnosis !== null && (submittedCode !== code || submittedGoal !== goal)
  const currentFingerprint = JSON.stringify([goal, code])

  async function loadProfile() {
    setProfileLoading(true)
    try {
      await ensureSession()
      setSkills((await get<{ skills: Skill[] }>('/profile')).skills)
      setProfileError('')
    } catch {
      setProfileError('学习记录暂时无法刷新。')
    } finally {
      setProfileLoading(false)
    }
  }

  function ensureSession() {
    session.current ??= post("/session").catch(error => { session.current = null; throw error })
    return session.current
  }

  useEffect(() => {
    let cancelled = false
    async function openSession() {
      try {
        await ensureSession()
        const capabilities = await get<{ mode: Mode }>('/capabilities')
        if (!cancelled) {
          setMode(capabilities.mode)
          await loadProfile()
        }
      } catch {
        if (!cancelled) {
          setError('工作台暂时无法连接。可重新加载页面，或直接重试诊断。')
          setProfileError('学习记录暂时无法刷新。')
          setProfileLoading(false)
        }
      }
    }
    void openSession()
    return () => { cancelled = true; request.current?.abort() }
  }, [])

  // Preserve a section jump made while its async content was still loading.
  // Only follow the currently focused heading; never pull an editing user away.
  useLayoutEffect(() => {
    const heading = document.activeElement
    if (heading instanceof HTMLElement && ['practice-title', 'evidence-title', 'profile-title'].includes(heading.id)) {
      heading.scrollIntoView({ block: 'start' })
    }
  }, [diagnosis, challenge, skills])

  function resetPractice(next: Challenge | null) {
    setChallenge(next)
    setHint(null)
    setAttempt(null)
    setAnswer('')
    setPracticeError('')
    attemptKey.current = null
  }

  async function diagnose() {
    if (request.current || busyPractice.current || !code.trim()) return
    const snapshot = code
    if (!diagnosisKey.current || diagnosisKey.current.value !== currentFingerprint) {
      diagnosisKey.current = { value: currentFingerprint, id: crypto.randomUUID() }
    }
    const requestId = diagnosisKey.current.id
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setError('')
    setStatus('请求已发送，等待诊断结果。')
    const timer = setTimeout(() => controller.abort('timeout'), 20000)
    try {
      await ensureSession()
      if (request.current !== controller) return
      const result = await post<Diagnosis>('/diagnoses', { code: snapshot, request_id: requestId, goal: goal || null }, controller.signal)
      if (request.current !== controller) return
      diagnosisKey.current = null
      setDiagnosis(result)
      setMode(result.mode)
      setSubmittedCode(snapshot)
      setSubmittedGoal(goal)
      resetPractice(result.challenge)
      setStatus('诊断已返回。')
      void loadProfile()
    } catch (exception) {
      if (request.current !== controller) return
      if (controller.signal.reason === 'timeout') setError('等待超时。代码已保留，可以重试。')
      else setError(exception instanceof Error ? exception.message : '诊断失败，请重试。')
      setStatus('')
    } finally {
      clearTimeout(timer)
      if (request.current === controller) {
        request.current = null
        setPending(false)
      }
    }
  }

  function cancel() {
    request.current?.abort()
    request.current = null
    setPending(false)
    setStatus('已停止等待，代码仍在编辑器中。')
  }

  async function practice(type: 'hint' | 'answer' | 'retry') {
    if (!challenge || busyPractice.current || request.current) return
    busyPractice.current = true
    setAction(type)
    setPracticeError('')
    const path = `/challenges/${challenge.id}/${type}`
    try {
      if (type === 'hint') setHint(await post<Hint>(path, { tier: (hint?.used ?? 0) + 1 }))
      if (type === 'retry') resetPractice(await post<Challenge>(path))
      if (type === 'answer') {
        const value = answer.trim()
        if (!attemptKey.current || attemptKey.current.value !== value) {
          attemptKey.current = { value, id: crypto.randomUUID() }
        }
        setAttempt(await post<Attempt>(path, { answer: value, attempt_id: attemptKey.current.id }))
        void loadProfile()
      }
    } catch (exception) {
      setPracticeError(exception instanceof Error ? exception.message : '操作失败，请重试。')
    } finally {
      busyPractice.current = false
      setAction(null)
    }
  }

  return <>
    <a className="skip-link" href="#code-title">跳到代码编辑器</a>
    <header className="site-header"><div className="site-header-inner">
      <a href="/" className="brand"><span className="brand-icon" aria-hidden="true">c<span>m</span></span>CodeMentor<span className="version">2.0</span></a>
      <div className="workspace-name"><span>学习空间</span><span className="slash">/</span><h1>编程复测工作台</h1></div>
      <span className={`mode ${mode ?? 'connecting'}`}><span aria-hidden="true" />{mode ? modeNames[mode] : '连接工作台'}</span>
    </div></header>
    <main className="app-main">
      <nav className="section-nav" aria-label="工作区导航">
        <span className="lab-label">PYTHON LAB</span>
        <a href="#code-title"><Icon name="code" />代码</a>
        <a href="#evidence-title"><Icon name="scan" />诊断</a>
        <a href="#practice-title"><Icon name="terminal" />复测</a>
        <a href="#profile-title"><Icon name="chart" />记录</a>
        <span className="nav-caption">从具体反例，走到独立解题。</span>
      </nav>
      <div className="workspace">
        <aside className="library" aria-label="实验目录">
          <div className="library-heading"><Icon name="folder" /><span>基础实验</span><span className="count">03</span></div>
          <div className="examples" aria-label="实验样例">{examples.map((example, index) =>
            <button className={code === example.code ? 'example selected' : 'example'} key={example.id}
              aria-pressed={code === example.code}
              onClick={() => { setCode(example.code); setGoal(example.goal) }}>
              <span className="example-number">0{index + 1}</span><span>{example.name}<small>{['Loop boundaries', 'Empty input', 'Accumulator'][index]}</small></span>
              <span className="example-arrow" aria-hidden="true">↗</span>
            </button>)}</div>
          <div className="learning-route"><p className="eyebrow">本轮学习路径</p>
            <ol>
              <li className={!diagnosis ? 'current' : 'done'}><span>{diagnosis ? '✓' : '1'}</span><div>定位错因<small>{pending ? '等待结果' : diagnosis ? '已返回诊断' : '从代码出发'}</small></div></li>
              <li className={challenge ? 'current' : ''}><span>2</span><div>验证理解<small>{attempt ? '已记录作答' : challenge ? '变式已就绪' : '等待匹配练习'}</small></div></li>
              <li className={attempt ? 'current' : ''}><span>3</span><div>积累证据<small>{attempt ? '已更新学习记录' : '区分独立与辅助'}</small></div></li>
            </ol>
          </div>
          <div className="library-note"><Icon name="shield" /><p>在证据范围内学习<small>本地分析不执行你的代码。<br />证据不足时，保留不确定性。</small></p></div>
        </aside>
          <section className="code-panel" aria-labelledby="code-title">
            <div className="editor-title"><div><span className="eyebrow">01 / EXPERIMENT</span><h2 id="code-title" tabIndex={-1}>代码实验台</h2></div><span className="language-badge">Python</span></div>
            <label className="task-contract">题目要求
              <select value={goal} onChange={event => setGoal(event.target.value as Goal)}>
                <option value="sum-all">返回全部整数元素的和</option>
                <option value="first-or-empty">返回首项，并处理空输入</option>
                <option value="">只检查语法，暂不指定要求</option>
              </select>
            </label>
            <div className="editor-shell">
              <div className="editor-bar"><span className="file-tab"><Icon name="code" />submission.py<span className={stale ? 'file-dot changed' : 'file-dot'} title={stale ? '相对上次提交有改动' : '当前编辑文件'} /></span><span className="editor-caption">{stale ? '有未诊断的改动' : '可直接编辑'}</span></div>
              <Suspense fallback={<label className="editor-fallback">正在加载编辑器…</label>}>
                <Editor code={code} onChange={setCode} line={stale ? null : diagnosis?.evidence[0]?.line ?? null} jump={jump} />
              </Suspense>
              <div className="editor-meta"><span>UTF-8 <span className="meta-separator">/</span> {code.split('\n').length} 行</span><span>{code.length.toLocaleString()} / 16,000 字符</span></div>
            </div>
            <div className="toolbar">
              <p className="status" role="status">{status || '修改代码，检查你的思路。'}</p>
              {pending && <button className="plain" onClick={cancel}>取消等待</button>}
              <button className="primary" disabled={pending || !!action || !code.trim() || code.length > 16000} onClick={() => void diagnose()}>
                <Icon name="play" />
                {pending ? '等待诊断…' : diagnosisKey.current?.value === currentFingerprint ? '重试诊断' : '开始诊断'}
              </button>
            </div>
            {error && <p className="error" role="alert">{error}</p>}
            {mode === 'live' && <p className="notice">模型只接收课程标准例子、静态证据和练习计数。请避免在编辑器中粘贴个人信息或密钥。</p>}
          </section>
          <DiagnosisPanel result={diagnosis} stale={stale} pending={pending} jump={() => setJump(value => value + 1)} />
          <PracticePanel challenge={challenge} hint={hint} attempt={attempt} answer={answer} setAnswer={setAnswer}
            action={pending ? 'diagnosis' : action} onHint={() => void practice('hint')}
            onSubmit={() => void practice('answer')} onRetry={() => void practice('retry')} error={practiceError} />
          <ProfilePanel skills={skills} loading={profileLoading} error={profileError} onRetry={() => void loadProfile()} />
      </div>
      <footer><span><span className="footer-dot" /> Python 入门实验 <span className="footer-separator">/</span> CodeMentor AI</span><span>静态证据 · 课程检索 · 变式复测</span></footer>
    </main>
  </>
}

createRoot(document.getElementById('root')!).render(<App />)
