import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type CrewMember = { role: string; title: string }
type ProviderInfo = {
  id: string
  name: string
  auth_methods: string[]
  oauth_label: string | null
  default_base_url: string
  default_model: string
  blocked_oauth_reason?: string
}
type Connection = {
  id: string
  provider: string
  label: string
  auth_method: string
  model: string
  key_preview: string
  active: boolean
}
type RunnerInfo = {
  id: string
  name: string
  installed: boolean
  logged_in: boolean
  auth_label: string
  notes: string
  login_job?: { status: string; ok: boolean | null; message: string } | null
}
type MissionSummary = {
  id: string
  title: string
  status: string
  current_role: string | null
  artifact_count: number
  updated_at: string
}
type AgentMessage = {
  id: string
  role: string
  content: string
  artifact_paths: string[]
  created_at: string
}
type Mission = {
  id: string
  title: string
  goal: string
  constraints: string
  status: string
  current_role: string | null
  engineer_runner: string
  reviewer_runner: string
  messages: AgentMessage[]
  artifacts: { path: string; kind: string; created_by: string }[]
  ship_bundle: string | null
  error: string | null
}

const ROLE_LABEL: Record<string, string> = {
  pm: 'PM',
  architect: 'Architect',
  engineer: 'Engineer',
  reviewer: 'Reviewer',
  devops: 'DevOps',
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!resp.ok) throw new Error((await resp.text()) || `HTTP ${resp.status}`)
  return resp.json() as Promise<T>
}

function parseMessage(content: string): { summary: string; bullets: string[] } {
  try {
    const data = JSON.parse(content) as Record<string, unknown>
    const summary = String(data.summary || '')
    const bullets: string[] = []
    for (const key of ['milestones', 'acceptance', 'notes', 'ship_notes', 'required_fixes', 'findings']) {
      const val = data[key]
      if (Array.isArray(val)) {
        for (const item of val.slice(0, 6)) {
          if (typeof item === 'string') bullets.push(item)
          else if (item && typeof item === 'object' && 'item' in item) bullets.push(String((item as { item: string }).item))
        }
      }
    }
    const files = data.files
    if (files && typeof files === 'object') {
      bullets.push(`файлы: ${Object.keys(files as object).slice(0, 8).join(', ')}`)
    }
    return { summary: summary || content.slice(0, 220), bullets }
  } catch {
    return { summary: content.slice(0, 220), bullets: [] }
  }
}

export default function App() {
  const [tab, setTab] = useState<'mission' | 'setup'>('mission')
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [runners, setRunners] = useState<RunnerInfo[]>([])
  const [history, setHistory] = useState<MissionSummary[]>([])
  const [mission, setMission] = useState<Mission | null>(null)
  const [selectedArtifact, setSelectedArtifact] = useState<{ path: string; content: string } | null>(null)
  const [title, setTitle] = useState('Notes API')
  const [goal, setGoal] = useState('Сделать сервис заметок с health-check и docker-compose до локального прода')
  const [constraints, setConstraints] = useState('Без auth в MVP, Python FastAPI')
  const [engineerRunner, setEngineerRunner] = useState('llm')
  const [reviewerRunner, setReviewerRunner] = useState('llm')
  const [busy, setBusy] = useState(false)
  const [connBusy, setConnBusy] = useState(false)
  const [runnerBusy, setRunnerBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [health, setHealth] = useState<{
    demo_mode: boolean
    model: string
    active_provider: string | null
    active_auth: string | null
  } | null>(null)
  const [keyProvider, setKeyProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [keyModel, setKeyModel] = useState('')

  async function refreshAll() {
    const [c, r, h, m] = await Promise.all([
      api<Connection[]>('/api/connections'),
      api<RunnerInfo[]>('/api/runners'),
      api<{ demo_mode: boolean; model: string; active_provider: string | null; active_auth: string | null }>('/api/health'),
      api<MissionSummary[]>('/api/missions'),
    ])
    setConnections(c)
    setRunners(r)
    setHealth(h)
    setHistory(m)
  }

  useEffect(() => {
    void api<CrewMember[]>('/api/crew').then(setCrew).catch(() => setCrew([]))
    void api<ProviderInfo[]>('/api/providers').then(setProviders).catch(() => setProviders([]))
    void refreshAll().catch(() => undefined)

    const params = new URLSearchParams(window.location.search)
    if (params.get('oauth') === 'ok') {
      setNotice('OpenRouter подключён. Можно запускать миссии на живых моделях.')
      setTab('mission')
      window.history.replaceState({}, '', window.location.pathname)
    } else if (params.get('oauth') === 'error') {
      setError(params.get('reason') || 'OAuth не удался')
      setTab('setup')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  useEffect(() => {
    if (!mission?.id) return
    if (!['running', 'shipping', 'queued'].includes(mission.status)) {
      void refreshAll().catch(() => undefined)
      return
    }
    const timer = window.setInterval(() => {
      void api<Mission>(`/api/missions/${mission.id}`)
        .then(setMission)
        .catch((err: Error) => setError(err.message))
    }, 900)
    return () => window.clearInterval(timer)
  }, [mission?.id, mission?.status])

  useEffect(() => {
    if (!runnerBusy) return
    const timer = window.setInterval(() => {
      void api<{ status: string; ok: boolean | null; message?: string }>(`/api/runners/${runnerBusy}/login`).then(
        (job) => {
          if (job.status === 'done') {
            setNotice(
              job.ok
                ? `${runnerBusy}: вход прошёл. ${job.message || ''}`
                : `${runnerBusy}: ${job.message || 'вход не удался'}`,
            )
            setRunnerBusy(null)
            void refreshAll()
          }
        },
      )
    }, 1500)
    return () => window.clearInterval(timer)
  }, [runnerBusy])

  const statusText = useMemo(() => {
    if (!mission) return 'Выбери или создай миссию'
    if (mission.status === 'running' && mission.current_role) {
      return `${ROLE_LABEL[mission.current_role] || mission.current_role} работает…`
    }
    if (mission.status === 'shipping') return 'Пакуем ship-бандл…'
    if (mission.status === 'done') return 'Готово к продакшену'
    if (mission.status === 'failed') return mission.error || 'Миссия упала'
    if (mission.status === 'cancelled') return 'Остановлено'
    return mission.status
  }, [mission])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    setSelectedArtifact(null)
    try {
      const created = await api<Mission>('/api/missions', {
        method: 'POST',
        body: JSON.stringify({
          title,
          goal,
          constraints,
          stack_hint: 'Python FastAPI + React',
          engineer_runner: engineerRunner,
          reviewer_runner: reviewerRunner,
        }),
      })
      const started = await api<Mission>(`/api/missions/${created.id}/run`, { method: 'POST' })
      setMission(started)
      await refreshAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить миссию')
    } finally {
      setBusy(false)
    }
  }

  async function openMission(id: string) {
    setError(null)
    setSelectedArtifact(null)
    const m = await api<Mission>(`/api/missions/${id}`)
    setMission(m)
    setTab('mission')
  }

  async function cancelMission() {
    if (!mission) return
    const m = await api<Mission>(`/api/missions/${mission.id}/cancel`, { method: 'POST' })
    setMission(m)
    await refreshAll()
  }

  async function deleteMission(id: string) {
    await api(`/api/missions/${id}`, { method: 'DELETE' })
    if (mission?.id === id) {
      setMission(null)
      setSelectedArtifact(null)
    }
    await refreshAll()
  }

  async function viewArtifact(path: string) {
    if (!mission) return
    const safe = path
      .split('/')
      .map((part) => encodeURIComponent(part))
      .join('/')
    const art = await api<{ path: string; content: string }>(`/api/missions/${mission.id}/artifacts/${safe}`)
    setSelectedArtifact(art)
  }

  async function loginRunner(id: string) {
    setRunnerBusy(id)
    setError(null)
    setNotice(`Запускаем вход ${id}…`)
    try {
      await api(`/api/runners/${id}/login`, { method: 'POST' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'login failed')
      setRunnerBusy(null)
    }
  }

  async function loginOpenRouter() {
    setConnBusy(true)
    try {
      const started = await api<{ auth_url: string }>('/api/connections/oauth/openrouter/start', { method: 'POST' })
      window.location.href = started.auth_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OAuth start failed')
      setConnBusy(false)
    }
  }

  async function saveApiKey(e: FormEvent) {
    e.preventDefault()
    setConnBusy(true)
    try {
      const provider = providers.find((p) => p.id === keyProvider)
      await api('/api/connections', {
        method: 'POST',
        body: JSON.stringify({
          provider: keyProvider,
          api_key: apiKey,
          model: keyModel || provider?.default_model || '',
          base_url: provider?.default_base_url || '',
          make_active: true,
        }),
      })
      setApiKey('')
      setNotice('Ключ сохранён и активирован.')
      await refreshAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить ключ')
    } finally {
      setConnBusy(false)
    }
  }

  const openrouter = providers.find((p) => p.id === 'openrouter')
  const anthropic = providers.find((p) => p.id === 'anthropic')
  const running = mission?.status === 'running' || mission?.status === 'shipping'

  return (
    <div className="page">
      <header className="top">
        <div>
          <p className="brand">ShipCrew</p>
          <h1>Команда агентов до прода</h1>
          <p className="lead">Бриф → пайплайн ролей → артефакты и zip-бандл. LLM, OpenRouter или подписки Codex/Claude/Cursor.</p>
        </div>
        <div className="meta">
          <span className={`pill ${health?.demo_mode ? 'demo' : 'live'}`}>
            {health?.demo_mode ? 'demo' : 'live'}
          </span>
          <span className="pill soft">
            {health?.active_provider
              ? `${health.active_provider} · ${health.active_auth || 'api'}`
              : health?.model || 'нет LLM'}
          </span>
        </div>
      </header>

      <nav className="tabs" aria-label="Разделы">
        <button type="button" className={tab === 'mission' ? 'active' : ''} onClick={() => setTab('mission')}>
          Миссии
        </button>
        <button type="button" className={tab === 'setup' ? 'active' : ''} onClick={() => setTab('setup')}>
          Подключения
        </button>
      </nav>

      {error ? <p className="error banner">{error}</p> : null}
      {notice ? <p className="notice banner">{notice}</p> : null}

      {tab === 'setup' ? (
        <div className="setup">
          <section className="panel">
            <h2>Модели (OpenRouter / API)</h2>
            <div className="conn-actions">
              <button type="button" className="secondary" disabled={connBusy || !openrouter} onClick={() => void loginOpenRouter()}>
                {connBusy ? 'Открываем OpenRouter…' : openrouter?.oauth_label || 'Войти через OpenRouter'}
              </button>
            </div>
            {anthropic?.blocked_oauth_reason ? <p className="warn">{anthropic.blocked_oauth_reason}</p> : null}
            <form className="key-form" onSubmit={(e) => void saveApiKey(e)}>
              <label>
                Провайдер
                <select
                  value={keyProvider}
                  onChange={(e) => {
                    setKeyProvider(e.target.value)
                    setKeyModel(providers.find((x) => x.id === e.target.value)?.default_model || '')
                  }}
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                API-ключ
                <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} required={keyProvider !== 'ollama'} />
              </label>
              <label>
                Модель
                <input value={keyModel} onChange={(e) => setKeyModel(e.target.value)} />
              </label>
              <button type="submit" disabled={connBusy}>
                Сохранить ключ
              </button>
            </form>
            <ul className="conn-list">
              {connections.map((c) => (
                <li key={c.id} className={c.active ? 'active' : ''}>
                  <div>
                    <strong>{c.label}</strong>
                    <span>
                      {c.provider} · {c.auth_method} · {c.key_preview} · {c.model}
                    </span>
                  </div>
                  <div className="row-actions">
                    {!c.active ? (
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => void api(`/api/connections/${c.id}/activate`, { method: 'POST' }).then(refreshAll)}
                      >
                        Активировать
                      </button>
                    ) : (
                      <span className="pill live">active</span>
                    )}
                    <button
                      type="button"
                      className="ghost danger"
                      onClick={() => void api(`/api/connections/${c.id}`, { method: 'DELETE' }).then(refreshAll)}
                    >
                      Удалить
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel">
            <h2>Подписки CLI/SDK</h2>
            <ul className="conn-list">
              {runners.map((r) => (
                <li key={r.id} className={r.logged_in ? 'active' : ''}>
                  <div>
                    <strong>{r.name}</strong>
                    <span>
                      {r.installed ? 'installed' : 'missing'} · {r.auth_label}
                    </span>
                    <span>{r.notes}</span>
                  </div>
                  <button type="button" className="ghost" disabled={!r.installed || runnerBusy === r.id} onClick={() => void loginRunner(r.id)}>
                    {runnerBusy === r.id ? 'Ждём браузер…' : 'Войти'}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : (
        <>
          <section className="crew" aria-label="Состав команды">
            {crew.map((member) => (
              <div key={member.role} className={`crew-slot ${mission?.current_role === member.role ? 'active' : ''}`}>
                <span className="role">{ROLE_LABEL[member.role] || member.role}</span>
                <span className="title">{member.title}</span>
              </div>
            ))}
          </section>

          <div className="workspace">
            <aside className="panel history">
              <h2>История</h2>
              {history.length === 0 ? (
                <p className="empty">Пока пусто. Запусти первую миссию.</p>
              ) : (
                <ul>
                  {history.map((item) => (
                    <li key={item.id} className={mission?.id === item.id ? 'active' : ''}>
                      <button type="button" className="hist-btn" onClick={() => void openMission(item.id)}>
                        <strong>{item.title}</strong>
                        <span>
                          {item.status} · {item.artifact_count} files
                        </span>
                      </button>
                      <button type="button" className="ghost danger tiny" onClick={() => void deleteMission(item.id)}>
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </aside>

            <form className="panel form" onSubmit={(e) => void onSubmit(e)}>
              <h2>Новая миссия</h2>
              <label>
                Название
                <input value={title} onChange={(e) => setTitle(e.target.value)} required />
              </label>
              <label>
                Задача
                <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={5} required />
              </label>
              <label>
                Ограничения
                <textarea value={constraints} onChange={(e) => setConstraints(e.target.value)} rows={2} />
              </label>
              <div className="two">
                <label>
                  Engineer
                  <select value={engineerRunner} onChange={(e) => setEngineerRunner(e.target.value)}>
                    <option value="llm">LLM</option>
                    <option value="codex">Codex</option>
                    <option value="claude">Claude</option>
                    <option value="cursor">Cursor</option>
                  </select>
                </label>
                <label>
                  Reviewer
                  <select value={reviewerRunner} onChange={(e) => setReviewerRunner(e.target.value)}>
                    <option value="llm">LLM</option>
                    <option value="codex">Codex</option>
                    <option value="claude">Claude</option>
                    <option value="cursor">Cursor</option>
                  </select>
                </label>
              </div>
              <button type="submit" disabled={busy}>
                {busy ? 'Запускаем…' : 'Запустить команду'}
              </button>
            </form>

            <section className="panel feed">
              <div className="feed-head">
                <div>
                  <h2>{mission?.title || 'Лента'}</h2>
                  <p>{statusText}</p>
                </div>
                <div className="row-actions">
                  {running ? (
                    <button type="button" className="ghost danger" onClick={() => void cancelMission()}>
                      Остановить
                    </button>
                  ) : null}
                  {mission && !running ? (
                    <button
                      type="button"
                      className="ghost"
                      onClick={() =>
                        void api<Mission>(`/api/missions/${mission.id}/run`, { method: 'POST' }).then((m) => {
                          setMission(m)
                          void refreshAll()
                        })
                      }
                    >
                      Перезапустить
                    </button>
                  ) : null}
                  {mission && (mission.status === 'done' || mission.artifacts.length > 0) ? (
                    <a className="ghost linkbtn" href={`/api/missions/${mission.id}/bundle.zip`}>
                      Скачать zip
                    </a>
                  ) : null}
                </div>
              </div>

              {!mission ? (
                <p className="empty">Здесь появится переписка агентов.</p>
              ) : (
                <>
                  <ul className="messages">
                    {mission.messages.map((msg) => {
                      const parsed = parseMessage(msg.content)
                      return (
                        <li key={msg.id}>
                          <div className="msg-top">
                            <strong>{ROLE_LABEL[msg.role] || msg.role}</strong>
                            <time>{new Date(msg.created_at).toLocaleTimeString()}</time>
                          </div>
                          <p>{parsed.summary}</p>
                          {parsed.bullets.length > 0 ? (
                            <ul className="bullets">
                              {parsed.bullets.map((b) => (
                                <li key={b}>{b}</li>
                              ))}
                            </ul>
                          ) : null}
                          {msg.artifact_paths.length > 0 ? (
                            <div className="art-links">
                              {msg.artifact_paths.map((p) => (
                                <button key={p} type="button" className="ghost tiny" onClick={() => void viewArtifact(p)}>
                                  {p}
                                </button>
                              ))}
                            </div>
                          ) : null}
                        </li>
                      )
                    })}
                  </ul>

                  {mission.artifacts.length > 0 ? (
                    <div className="artifacts">
                      <h3>Артефакты ({mission.artifacts.length})</h3>
                      <div className="art-links">
                        {mission.artifacts.map((a) => (
                          <button key={a.path} type="button" className="ghost tiny" onClick={() => void viewArtifact(a.path)}>
                            {a.path}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {selectedArtifact ? (
                    <div className="preview">
                      <div className="feed-head">
                        <h3>{selectedArtifact.path}</h3>
                        <button type="button" className="ghost tiny" onClick={() => setSelectedArtifact(null)}>
                          Закрыть
                        </button>
                      </div>
                      <pre>{selectedArtifact.content}</pre>
                    </div>
                  ) : null}
                </>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  )
}
