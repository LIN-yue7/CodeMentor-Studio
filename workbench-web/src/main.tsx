
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { get, post } from './api'
import type { Attempt, Challenge, Diagnosis, Hint, Mode, Skill } from './api'
import { examples } from './examples'
import { DiagnosisPanel, PracticePanel, ProfilePanel } from './panels'
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
  const [skills, setSkills] = useState<Skill[]>([])
  const [jump, setJump] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [profileError, setProfileError] = useState('')
  const [practiceError, setPracticeError] = useState('')
  const [pending, setPending] = useState(false)
  const [action, setAction] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const diagnosisKey = useRef<{ value: string; id: string } | null>(null)
  const attemptKey = useRef<{ value: string; id: string } | null>(null)
  const busyPractice = useRef(false)
  const stale = diagnosis !== null && (submittedCode !== code || submittedGoal !== goal)
  const currentFingerprint = JSON.stringify([goal, code])

  async function loadProfile() {
    try {
      setSkills((await get<{ skills: Skill[] }>('/profile')).skills)
      setProfileError('')
    } catch {
      setProfileError('学习记录暂时无法刷新。')
    }
  }

  useEffect(() => {
    let cancelled = false
    async function openSession() {
      try {
        await post('/session')
        const capabilities = await get<{ mode: Mode }>('/capabilities')
        if (!cancelled) {
          setMode(capabilities.mode)
          await loadProfile()
        }
      } catch {
        if (!cancelled) setError('工作台暂时无法连接。可重新加载页面，或直接重试诊断。')
      }
    }
    void openSession()
    return () => { cancelled = true; request.current?.abort() }
  }, [])

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
      await post('/session', undefined, controller.signal)
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
      if (type === 'hint') setHint(await post<Hint>(path))
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
    <header className="site-header"><div className="site-header-inner">
      <a href="/" className="brand"><span className="brand-icon" aria-hidden="true">›_</span>CodeMentor <span>AI 2.0</span></a>
      <span className="mode"><span aria-hidden="true" />{mode ? modeNames[mode] : '连接工作台'}</span>
    </div></header>
    <main>
      <div className="intro"><div>
        <p className="eyebrow">PYTHON LAB <span> / </span> 01</p>
        <h1>编程复测工作台</h1>
        <p>沿着具体反例找到错因，再用一道变式检验自己的理解。</p>
      </div><a className="profile-link" href="#profile-title">查看学习记录 ↓</a></div>
      <div className="workspace">
        <section className="panel code-panel" aria-labelledby="code-title">
          <div className="panel-head"><span className="step">01</span><div>
            <h2 id="code-title">代码实验台</h2><p>编辑 Python 函数或选一个练习样例</p>
          </div></div>
          <div className="panel-content">
            <div className="examples" aria-label="实验样例">{examples.map(example =>
              <button className={code === example.code ? 'example selected' : 'example'} key={example.id}
                onClick={() => { setCode(example.code); setGoal(example.goal) }}>{example.name}</button>)}</div>
            <label className="task-contract">题目要求
              <select value={goal} onChange={event => setGoal(event.target.value as Goal)}>
                <option value="sum-all">返回全部整数元素的和</option>
                <option value="first-or-empty">返回首项，并处理空输入</option>
                <option value="">只检查语法，暂不指定要求</option>
              </select>
            </label>
            <div className="editor-shell">
              <div className="editor-bar"><span>submission.py</span><span>Python</span></div>
              <Suspense fallback={<label className="editor-fallback">正在加载编辑器…</label>}>
                <Editor code={code} onChange={setCode} line={stale ? null : diagnosis?.evidence[0]?.line ?? null} jump={jump} />
              </Suspense>
            </div>
            <div className="toolbar">
              <button className="primary" disabled={pending || !!action || !code.trim() || code.length > 16000} onClick={() => void diagnose()}>
                {pending ? '等待诊断…' : diagnosisKey.current?.value === currentFingerprint ? '重试诊断' : '开始诊断'}
              </button>
              {pending && <button className="plain" onClick={cancel}>取消等待</button>}
              <small>{code.length.toLocaleString()} / 16,000 字符</small>
            </div>
            <p className="status" role="status">{status}</p>
            {error && <p className="error" role="alert">{error}</p>}
            {mode === 'live' && <p className="notice">真实模型模式可能把匹配样例的代码片段发送给配置的模型服务。请避免提交个人信息或密钥。</p>}
          </div>
        </section>
        <DiagnosisPanel result={diagnosis} stale={stale} jump={() => setJump(value => value + 1)} />
        <PracticePanel challenge={challenge} hint={hint} attempt={attempt} answer={answer} setAnswer={setAnswer}
          action={pending ? 'diagnosis' : action} onHint={() => void practice('hint')}
          onSubmit={() => void practice('answer')} onRetry={() => void practice('retry')} error={practiceError} />
        <ProfilePanel skills={skills} />
      </div>
      {profileError && <p className="error" role="status">{profileError}</p>}
      <footer><span>CodeMentor AI · Python 入门实验</span><span>静态检查 · 受控知识检索 · 确定性评分</span></footer>
    </main>
  </>
}

createRoot(document.getElementById('root')!).render(<App />)
