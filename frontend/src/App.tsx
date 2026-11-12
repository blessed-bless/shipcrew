import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from './api'
import { CrewStrip } from './components/CrewStrip'
import { Header } from './components/Header'
import { InsightsPanel } from './components/InsightsPanel'
import { MissionFeed } from './components/MissionFeed'
import { SetupPanel } from './components/SetupPanel'
import { Tabs } from './components/Tabs'
import type {
  Connection,
  CrewMember,
  CrewTemplate,
  Metrics,
  Mission,
  MissionSummary,
  ProjectSummary,
  ProviderInfo,
  RunnerInfo,
} from './types'
import { ROLE_LABEL } from './types'
import './App.css'

export default function App() {
  const [tab, setTab] = useState<'mission' | 'setup' | 'insights'>('mission')
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [runners, setRunners] = useState<RunnerInfo[]>([])
  const [templates, setTemplates] = useState<CrewTemplate[]>([])
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [history, setHistory] = useState<MissionSummary[]>([])
  const [mission, setMission] = useState<Mission | null>(null)
  const [selectedArtifact, setSelectedArtifact] = useState<{ path: string; content: string } | null>(null)
  const [title, setTitle] = useState('Notes API')
  const [goal, setGoal] = useState('Сделать сервис заметок с health-check и docker-compose до локального прода')
  const [constraints, setConstraints] = useState('Без auth в MVP, Python FastAPI')
  const [templateId, setTemplateId] = useState('greenfield-saas')
  const [projectId, setProjectId] = useState('')
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
  const [projectName, setProjectName] = useState('')
  const [projectDesc, setProjectDesc] = useState('')

  async function refreshAll() {
    const [c, r, h, m, t, p, met] = await Promise.all([
      api<Connection[]>('/api/connections'),
      api<RunnerInfo[]>('/api/runners'),
      api<{ demo_mode: boolean; model: string; active_provider: string | null; active_auth: string | null }>(
        '/api/health',
      ),
      api<MissionSummary[]>('/api/missions'),
      api<CrewTemplate[]>('/api/templates'),
      api<ProjectSummary[]>('/api/projects'),
      api<Metrics>('/api/metrics'),
    ])
    setConnections(c)
    setRunners(r)
    setHealth(h)
    setHistory(m)
    setTemplates(t)
    setProjects(p)
    setMetrics(met)
  }

  useEffect(() => {
    void api<CrewMember[]>('/api/crew').then(setCrew).catch(() => setCrew([]))
    void api<ProviderInfo[]>('/api/providers').then(setProviders).catch(() => setProviders([]))
    void refreshAll().catch(() => undefined)
    const params = new URLSearchParams(window.location.search)
    if (params.get('oauth') === 'ok') {
      setNotice('OpenRouter подключён.')
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
            setNotice(job.ok ? `${runnerBusy}: вход ок` : `${runnerBusy}: ${job.message || 'fail'}`)
            setRunnerBusy(null)
            void refreshAll()
          }
        },
      )
    }, 1500)
    return () => window.clearInterval(timer)
  }, [runnerBusy])

  useEffect(() => {
    const t = templates.find((x) => x.id === templateId)
    if (!t) return
    setEngineerRunner(t.recommended_engineer)
    setReviewerRunner(t.recommended_reviewer)
    if (t.starter_goals[0] && goal.startsWith('Сделать сервис заметок')) {
      setGoal(t.starter_goals[0])
    }
  }, [templateId, templates])

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
          stack_hint: templates.find((t) => t.id === templateId)?.default_stack || 'Python FastAPI + React',
          engineer_runner: engineerRunner,
          reviewer_runner: reviewerRunner,
          template_id: templateId,
          project_id: projectId || null,
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

  const running = mission?.status === 'running' || mission?.status === 'shipping'

  return (
    <div className="page">
      <Header
        demoMode={health?.demo_mode}
        activeProvider={health?.active_provider}
        activeAuth={health?.active_auth}
        model={health?.model}
      />
      <Tabs tab={tab} onChange={setTab} />
      {error ? <p className="error banner">{error}</p> : null}
      {notice ? <p className="notice banner">{notice}</p> : null}

      {tab === 'setup' ? (
        <SetupPanel
          providers={providers}
          connections={connections}
          runners={runners}
          keyProvider={keyProvider}
          apiKey={apiKey}
          keyModel={keyModel}
          connBusy={connBusy}
          runnerBusy={runnerBusy}
          onKeyProvider={setKeyProvider}
          onApiKey={setApiKey}
          onKeyModel={setKeyModel}
          onSaveKey={(e) => {
            e.preventDefault()
            setConnBusy(true)
            const provider = providers.find((p) => p.id === keyProvider)
            void api('/api/connections', {
              method: 'POST',
              body: JSON.stringify({
                provider: keyProvider,
                api_key: apiKey,
                model: keyModel || provider?.default_model || '',
                base_url: provider?.default_base_url || '',
                make_active: true,
              }),
            })
              .then(async () => {
                setApiKey('')
                setNotice('Ключ сохранён.')
                await refreshAll()
              })
              .catch((err: Error) => setError(err.message))
              .finally(() => setConnBusy(false))
          }}
          onOpenRouter={() => {
            setConnBusy(true)
            void api<{ auth_url: string }>('/api/connections/oauth/openrouter/start', { method: 'POST' })
              .then((started) => {
                window.location.href = started.auth_url
              })
              .catch((err: Error) => {
                setError(err.message)
                setConnBusy(false)
              })
          }}
          onActivate={(id) => void api(`/api/connections/${id}/activate`, { method: 'POST' }).then(refreshAll)}
          onDeleteConnection={(id) => void api(`/api/connections/${id}`, { method: 'DELETE' }).then(refreshAll)}
          onLoginRunner={(id) => {
            setRunnerBusy(id)
            void api(`/api/runners/${id}/login`, { method: 'POST' }).catch((err: Error) => {
              setError(err.message)
              setRunnerBusy(null)
            })
          }}
        />
      ) : null}

      {tab === 'insights' ? (
        <InsightsPanel
          metrics={metrics}
          templates={templates}
          projects={projects}
          projectName={projectName}
          projectDesc={projectDesc}
          onProjectName={setProjectName}
          onProjectDesc={setProjectDesc}
          onCreateProject={() => {
            void api('/api/projects', {
              method: 'POST',
              body: JSON.stringify({
                name: projectName,
                description: projectDesc,
                default_template_id: templateId,
              }),
            })
              .then(async () => {
                setProjectName('')
                setProjectDesc('')
                await refreshAll()
              })
              .catch((err: Error) => setError(err.message))
          }}
          onDeleteProject={(id) => void api(`/api/projects/${id}`, { method: 'DELETE' }).then(refreshAll)}
        />
      ) : null}

      {tab === 'mission' ? (
        <>
          <CrewStrip crew={crew} activeRole={mission?.current_role} />
          <div className="workspace">
            <aside className="panel history">
              <h2>История</h2>
              {history.length === 0 ? (
                <p className="empty">Пока пусто.</p>
              ) : (
                <ul>
                  {history.map((item) => (
                    <li key={item.id} className={mission?.id === item.id ? 'active' : ''}>
                      <button
                        type="button"
                        className="hist-btn"
                        onClick={() =>
                          void api<Mission>(`/api/missions/${item.id}`).then((m) => {
                            setMission(m)
                            setSelectedArtifact(null)
                          })
                        }
                      >
                        <strong>{item.title}</strong>
                        <span>
                          {item.status} · {item.artifact_count} files
                        </span>
                      </button>
                      <button
                        type="button"
                        className="ghost danger tiny"
                        onClick={() =>
                          void api(`/api/missions/${item.id}`, { method: 'DELETE' }).then(async () => {
                            if (mission?.id === item.id) {
                              setMission(null)
                              setSelectedArtifact(null)
                            }
                            await refreshAll()
                          })
                        }
                      >
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
                Шаблон команды
                <select value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Проект
                <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                  <option value="">Без проекта</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
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

            <MissionFeed
              mission={mission}
              statusText={statusText}
              running={running}
              selectedArtifact={selectedArtifact}
              onCancel={() =>
                mission &&
                void api<Mission>(`/api/missions/${mission.id}/cancel`, { method: 'POST' }).then(setMission)
              }
              onRerun={() =>
                mission &&
                void api<Mission>(`/api/missions/${mission.id}/run`, { method: 'POST' }).then((m) => {
                  setMission(m)
                  void refreshAll()
                })
              }
              onViewArtifact={(path) => {
                if (!mission) return
                const safe = path
                  .split('/')
                  .map((part) => encodeURIComponent(part))
                  .join('/')
                void api<{ path: string; content: string }>(`/api/missions/${mission.id}/artifacts/${safe}`).then(
                  setSelectedArtifact,
                )
              }}
              onCloseArtifact={() => setSelectedArtifact(null)}
            />
          </div>
        </>
      ) : null}
    </div>
  )
}
