type Props = {
  demoMode?: boolean
  activeProvider?: string | null
  activeAuth?: string | null
  model?: string
}

export function Header({ demoMode, activeProvider, activeAuth, model }: Props) {
  return (
    <header className="top">
      <div>
        <p className="brand">ShipCrew</p>
        <h1>Команда агентов до прода</h1>
        <p className="lead">
          Проекты, шаблоны команд, shared blackboard, runners на подписках и ship-бандл в zip.
        </p>
      </div>
      <div className="meta">
        <span className={`pill ${demoMode ? 'demo' : 'live'}`}>{demoMode ? 'demo' : 'live'}</span>
        <span className="pill soft">
          {activeProvider ? `${activeProvider} · ${activeAuth || 'api'}` : model || 'нет LLM'}
        </span>
      </div>
    </header>
  )
}
