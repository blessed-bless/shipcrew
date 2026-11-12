import type { CrewTemplate, Metrics, ProjectSummary } from '../types'

type Props = {
  metrics: Metrics | null
  templates: CrewTemplate[]
  projects: ProjectSummary[]
  projectName: string
  projectDesc: string
  onProjectName: (v: string) => void
  onProjectDesc: (v: string) => void
  onCreateProject: () => void
  onDeleteProject: (id: string) => void
}

export function InsightsPanel({
  metrics,
  templates,
  projects,
  projectName,
  projectDesc,
  onProjectName,
  onProjectDesc,
  onCreateProject,
  onDeleteProject,
}: Props) {
  return (
    <div className="setup">
      <section className="panel">
        <h2>Метрики</h2>
        {!metrics ? (
          <p className="empty">Пока нет данных.</p>
        ) : (
          <div className="metrics-grid">
            <div>
              <strong>{metrics.mission_count}</strong>
              <span>миссий</span>
            </div>
            <div>
              <strong>{Math.round(metrics.success_rate * 100)}%</strong>
              <span>success</span>
            </div>
            <div>
              <strong>{metrics.artifact_count}</strong>
              <span>артефактов</span>
            </div>
            <div>
              <strong>{metrics.avg_duration_seconds}s</strong>
              <span>avg duration</span>
            </div>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Шаблоны команд</h2>
        <ul className="conn-list">
          {templates.map((t) => (
            <li key={t.id}>
              <div>
                <strong>{t.name}</strong>
                <span>{t.description}</span>
                <span>
                  {t.tags.join(' · ')} · eng:{t.recommended_engineer} · rev:{t.recommended_reviewer}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Проекты</h2>
        <div className="two">
          <label>
            Название
            <input value={projectName} onChange={(e) => onProjectName(e.target.value)} />
          </label>
          <label>
            Описание
            <input value={projectDesc} onChange={(e) => onProjectDesc(e.target.value)} />
          </label>
        </div>
        <button type="button" onClick={onCreateProject} style={{ marginTop: '0.75rem' }}>
          Создать проект
        </button>
        <ul className="conn-list" style={{ marginTop: '1rem' }}>
          {projects.map((p) => (
            <li key={p.id}>
              <div>
                <strong>{p.name}</strong>
                <span>
                  {p.description || 'без описания'} · template {p.default_template_id} · missions{' '}
                  {p.mission_count}
                </span>
              </div>
              <button type="button" className="ghost danger" onClick={() => onDeleteProject(p.id)}>
                Удалить
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
