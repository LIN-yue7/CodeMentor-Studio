
export type Mode = 'local' | 'live' | 'simulated'
export type Evidence = {
  id: string
  knowledge_id?: string
  line: number | null
  condition: string
  counterexample?: string
  observed?: string
  expected?: string
  correction?: string
}
export type Card = { id: string; title: string; content: string; source: string; version: number }
export type Challenge = {
  id: string; knowledge_id: string; template_id: string; title: string; prompt: string; hint_count: number
}
export type Diagnosis = {
  id: string
  status: 'confirmed' | 'syntax-error' | 'uncertain'
  mode: Mode
  evidence: Evidence[]
  cards: Card[]
  model_status: string
  annotation: { explanation: string; citations: string[] } | null
  challenge: Challenge | null
  events: { stage: string; status: string; elapsed_ms?: number }[]
}
export type Attempt = {
  outcome: 'assisted' | 'independent' | 'incorrect'
  recommendation: 'repeat' | 'transfer' | 'verified'
  hints_used: number
  distinct_independent: number
  feedback: string
}
export type Skill = {
  knowledge_id: string; label: string; diagnoses: number; independent: number; assisted: number
  incorrect: number; distinct_independent: number
}
export type Hint = { used: number; hints: string[] }

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, {
    ...options,
    credentials: 'same-origin',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string' ? error.detail : `请求失败（${response.status}）。`)
  }
  return response.json() as Promise<T>
}

export const get = <T>(path: string) => request<T>(path, {})
export const post = <T>(path: string, body?: object, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined, signal })
