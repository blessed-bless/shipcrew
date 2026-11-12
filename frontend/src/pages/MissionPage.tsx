import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { CrewStrip } from '../components/CrewStrip'
import { MissionFeed } from '../components/MissionFeed'
import { usePolling } from '../hooks/usePolling'
import type { useShipCrewData } from '../hooks/useShipCrewData'
import type { Mission } from '../types'
import { ROLE_LABEL } from '../types'

type Data = ReturnType<typeof useShipCrewData>

type Props = {
  data: Data
}

export function MissionPage({ data }: Props) {
  const { missionId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const {
    crew,
    templates,
    projects,
    history,
    refreshAll,
    setError,
    setNotice,
  } = data

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

  useEffect(() => {
    if (searchParams.get('oauth') === 'ok') {
      setNotice('OpenRouter подключён.')
      window.history.replaceState({}, '', window.location.pathname)
    } else if (searchParams.get('oauth') === 'error') {
      setError(searchParams.get('reason') || 'OAuth не удался')
    }
  }, [searchParams, setError, setNotice])

  useEffect(() => {
    if (!missionId) {
      setMission(null)
      return
    }
    void api<Mission>(`/api/missions/${missionId}`)
      .then((m) => {
        setMission(m)
        setSelectedArtifact(null)
      })
      .catch((err: Error) => setError(err.message))
  }, [missionId, setError])

  const running = mission?.status === 'running' || mission?.status === 'shipping' || mission?.status === 'queued'
  usePolling(Boolean(mission?.id && running), 900, () => {
    if (!mission?.id) return
    void api<Mission>(`/api/missions/${mission.id}`)
      .then(setMission)
      .catch((err: Error) => setError(err.message))
  })

  useEffect(() => {
    const t = templates.find((x) => x.id === templateId)
    if (!t) return
    setEngineerRunner(t.recommended_engineer)
    setReviewerRunner(t.recommended_reviewer)
    if (t.starter_goals[0] && goal.startsWith('Сделать сервис заметок')) {
      setGoal(t.starter_goals[0])
    }
  }, [templateId, templates, goal])

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
      navigate(`/missions/${started.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить миссию')
    } finally {
      setBusy(false)
    }
  }

  return (
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
                    onClick={() => navigate(`/missions/${item.id}`)}
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
                          navigate('/')
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
          running={Boolean(running)}
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
  )
}
