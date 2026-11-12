import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type CrewMember = { role: string; title: string }

type ProviderInfo = {
  id: string
  name: string
  auth_methods: string[]
  oauth_label: string | null
  description: string
  default_base_url: string
  default_model: string
  supports_oauth: boolean
  blocked_oauth_reason?: string
}

type Connection = {
  id: string
  provider: string
  label: string
  auth_method: string
  base_url: string
  model: string
  key_preview: string
  active: boolean
}

type RunnerInfo = {
  id: string
  name: string
  binary: string | null
  installed: boolean
  logged_in: boolean
  auth_label: string
  login_command: string
  notes: string
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
  stack_hint: string
  status: string
  current_role: string | null
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
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `HTTP ${resp.status}`)
  }
  return resp.json() as Promise<T>
}

function summarize(content: string): string {
  try {
    const data = JSON.parse(content) as { summary?: string }
    if (data.summary) return data.summary
  } catch {
    /* plain text */
  }
  return content.slice(0, 220)
}

export default function App() {
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [runners, setRunners] = useState<RunnerInfo[]>([])
  const [mission, setMission] = useState<Mission | null>(null)
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
    ok: boolean
    demo_mode: boolean
    model: string
    active_provider: string | null
    active_auth: string | null
  } | null>(null)

  const [keyProvider, setKeyProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [keyModel, setKeyModel] = useState('')

  async function refreshConnections() {
    const list = await api<Connection[]>('/api/connections')
    setConnections(list)
  }

  async function refreshRunners() {
    const list = await api<RunnerInfo[]>('/api/runners')
    setRunners(list)
  }

  async function refreshHealth() {
    const h = await api<{
      ok: boolean
      demo_mode: boolean
      model: string
      active_provider: string | null
      active_auth: string | null
    }>('/api/health')
    setHealth(h)
  }

  useEffect(() => {
    void api<CrewMember[]>('/api/crew').then(setCrew).catch(() => setCrew([]))
    void api<ProviderInfo[]>('/api/providers').then(setProviders).catch(() => setProviders([]))
    void refreshConnections().catch(() => setConnections([]))
    void refreshRunners().catch(() => setRunners([]))
    void refreshHealth().catch(() => setHealth(null))

    const params = new URLSearchParams(window.location.search)
    const oauth = params.get('oauth')
    if (oauth === 'ok') {
      setNotice('Вход через браузер прошёл. Подключение активно — миссии пойдут через твой аккаунт.')
      void refreshConnections()
      void refreshHealth()
      window.history.replaceState({}, '', window.location.pathname)
    } else if (oauth === 'error') {
      setError(params.get('reason') || 'OAuth не удался')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  useEffect(() => {
    if (!mission?.id) return
    if (mission.status === 'done' || mission.status === 'failed') return

    const timer = window.setInterval(() => {
      void api<Mission>(`/api/missions/${mission.id}`)
        .then(setMission)
        .catch((err: Error) => setError(err.message))
    }, 800)

    return () => window.clearInterval(timer)
  }, [mission?.id, mission?.status])

  const activeRole = mission?.current_role
  const statusText = useMemo(() => {
    if (!mission) return 'Команда ждёт задачу'
    if (mission.status === 'running' && activeRole) {
      return `${ROLE_LABEL[activeRole] || activeRole} работает...`
    }
    if (mission.status === 'shipping') return 'Собираем ship-бандл...'
    if (mission.status === 'done') return 'Довели до прода: бандл готов'
    if (mission.status === 'failed') return mission.error || 'Миссия упала'
    return mission.status
  }, [mission, activeRole])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить миссию')
    } finally {
      setBusy(false)
    }
  }

  async function loginRunner(id: string) {
    setRunnerBusy(id)
    setError(null)
    setNotice(`Открываем вход ${id}. Заверши авторизацию в браузере/CLI...`)
    try {
      const result = await api<{ ok: boolean; message: string }>(`/api/runners/${id}/login`, {
        method: 'POST',
      })
      setNotice(result.ok ? `${id}: вход ок. ${result.message}` : `${id}: ${result.message}`)
      await refreshRunners()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось открыть login runner')
    } finally {
      setRunnerBusy(null)
    }
  }

  async function loginOpenRouter() {
    setConnBusy(true)
    setError(null)
    try {
      const started = await api<{ auth_url: string }>('/api/connections/oauth/openrouter/start', {
        method: 'POST',
      })
      window.location.href = started.auth_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось начать OAuth')
      setConnBusy(false)
    }
  }

  async function saveApiKey(e: FormEvent) {
    e.preventDefault()
    setConnBusy(true)
    setError(null)
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
      setNotice('API-ключ сохранён и активирован.')
      await refreshConnections()
      await refreshHealth()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить ключ')
    } finally {
      setConnBusy(false)
    }
  }

  async function activate(id: string) {
    await api(`/api/connections/${id}/activate`, { method: 'POST' })
    await refreshConnections()
    await refreshHealth()
  }

  async function removeConnection(id: string) {
    await api(`/api/connections/${id}`, { method: 'DELETE' })
    await refreshConnections()
    await refreshHealth()
  }

  const openrouter = providers.find((p) => p.id === 'openrouter')
  const anthropic = providers.find((p) => p.id === 'anthropic')

  return (
    <div className="page">
      <header className="top">
        <div>
          <p className="brand">ShipCrew</p>
          <h1>ИИ-команда доводит задачу до прода</h1>
          <p className="lead">
            Подключи модель через браузер (OpenRouter) или API-ключ — затем запускай команду агентов.
          </p>
        </div>
        <div className="meta">
          <span className={`pill ${health?.demo_mode ? 'demo' : 'live'}`}>
            {health?.demo_mode ? 'demo mode' : 'LLM live'}
          </span>
          <span className="pill soft">
            {health?.active_provider
              ? `${health.active_provider} · ${health.active_auth || 'api'}`
              : health?.model || 'нет подключения'}
          </span>
        </div>
      </header>

      <section className="panel connections">
        <h2>Подключения к моделям</h2>
        <p className="hint">
          Браузерный вход работает официально через OpenRouter: тебя перекинет на их сайт, ты дашь доступ ShipCrew,
          списание пойдёт с твоего аккаунта/кредитов. Claude Code OAuth в сторонние приложения Anthropic запрещает —
          для Claude бери Console API key или те же модели через OpenRouter.
        </p>

        <div className="conn-actions">
          <button type="button" className="secondary" disabled={connBusy || !openrouter} onClick={() => void loginOpenRouter()}>
            {connBusy ? 'Открываем OpenRouter...' : openrouter?.oauth_label || 'Войти через OpenRouter'}
          </button>
        </div>

        {anthropic?.blocked_oauth_reason ? <p className="warn">{anthropic.blocked_oauth_reason}</p> : null}

        <form className="key-form" onSubmit={(e) => void saveApiKey(e)}>
          <label>
            Провайдер (API-ключ)
            <select
              value={keyProvider}
              onChange={(e) => {
                setKeyProvider(e.target.value)
                const p = providers.find((x) => x.id === e.target.value)
                setKeyModel(p?.default_model || '')
              }}
            >
              {providers
                .filter((p) => p.auth_methods.includes('api_key') || p.auth_methods.includes('local'))
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            API-ключ
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={keyProvider === 'ollama' ? 'можно пусто' : 'sk-...'}
              required={keyProvider !== 'ollama'}
            />
          </label>
          <label>
            Модель
            <input value={keyModel} onChange={(e) => setKeyModel(e.target.value)} placeholder="model id" />
          </label>
          <button type="submit" disabled={connBusy}>
            Сохранить ключ
          </button>
        </form>

        {connections.length === 0 ? (
          <p className="empty">Пока нет подключений. Войди через OpenRouter или добавь ключ.</p>
        ) : (
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
                    <button type="button" className="ghost" onClick={() => void activate(c.id)}>
                      Сделать активным
                    </button>
                  ) : (
                    <span className="pill live">active</span>
                  )}
                  <button type="button" className="ghost danger" onClick={() => void removeConnection(c.id)}>
                    Удалить
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {notice ? <p className="notice">{notice}</p> : null}
      </section>

      <section className="panel connections">
        <h2>Подписки через официальные CLI/SDK</h2>
        <p className="hint">
          Codex / Claude Code / Cursor Agent — без ручного API-ключа: логин в браузере у самого клиента, ShipCrew
          только запускает их как инженера/ревьюера.
        </p>
        <ul className="conn-list">
          {runners.map((r) => (
            <li key={r.id} className={r.logged_in ? 'active' : ''}>
              <div>
                <strong>{r.name}</strong>
                <span>
                  {r.installed ? 'installed' : 'not installed'} · {r.auth_label}
                  {r.binary ? ` · ${r.binary}` : ''}
                </span>
                <span>{r.notes}</span>
              </div>
              <div className="row-actions">
                <button
                  type="button"
                  className="ghost"
                  disabled={!r.installed || runnerBusy === r.id}
                  onClick={() => void loginRunner(r.id)}
                >
                  {runnerBusy === r.id ? 'Ждём вход...' : 'Войти через браузер'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="crew" aria-label="Состав команды">
        {crew.map((member) => {
          const isActive = activeRole === member.role
          return (
            <div key={member.role} className={`crew-slot ${isActive ? 'active' : ''}`}>
              <span className="role">{ROLE_LABEL[member.role] || member.role}</span>
              <span className="title">{member.title}</span>
            </div>
          )
        })}
      </section>

      <div className="grid">
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
            <textarea value={constraints} onChange={(e) => setConstraints(e.target.value)} rows={3} />
          </label>
          <label>
            Engineer backend
            <select value={engineerRunner} onChange={(e) => setEngineerRunner(e.target.value)}>
              <option value="llm">LLM (OpenRouter/API)</option>
              <option value="codex">Codex (ChatGPT sub)</option>
              <option value="claude">Claude Code (sub)</option>
              <option value="cursor">Cursor Agent SDK</option>
            </select>
          </label>
          <label>
            Reviewer backend
            <select value={reviewerRunner} onChange={(e) => setReviewerRunner(e.target.value)}>
              <option value="llm">LLM (OpenRouter/API)</option>
              <option value="codex">Codex (ChatGPT sub)</option>
              <option value="claude">Claude Code (sub)</option>
              <option value="cursor">Cursor Agent SDK</option>
            </select>
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Запускаем команду...' : 'Запустить команду'}
          </button>
          {error ? <p className="error">{error}</p> : null}
        </form>

        <section className="panel feed">
          <div className="feed-head">
            <h2>Лента агентов</h2>
            <p>{statusText}</p>
          </div>

          {!mission ? (
            <p className="empty">Здесь пока тихо. Запусти миссию — агенты начнут писать друг другу.</p>
          ) : (
            <ul className="messages">
              {mission.messages.map((msg) => (
                <li key={msg.id}>
                  <div className="msg-top">
                    <strong>{ROLE_LABEL[msg.role] || msg.role}</strong>
                    <time>{new Date(msg.created_at).toLocaleTimeString()}</time>
                  </div>
                  <p>{summarize(msg.content)}</p>
                  {msg.artifact_paths.length > 0 ? (
                    <p className="arts">файлы: {msg.artifact_paths.join(', ')}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}

          {mission?.status === 'done' && mission.ship_bundle ? (
            <div className="ship">
              <h3>Ship bundle</h3>
              <code>{mission.ship_bundle}</code>
              <p>Артефактов: {mission.artifacts.length}</p>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  )
}
