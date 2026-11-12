type Tab = 'mission' | 'setup' | 'insights'

type Props = {
  tab: Tab
  onChange: (tab: Tab) => void
}

export function Tabs({ tab, onChange }: Props) {
  return (
    <nav className="tabs" aria-label="Разделы">
      <button type="button" className={tab === 'mission' ? 'active' : ''} onClick={() => onChange('mission')}>
        Миссии
      </button>
      <button type="button" className={tab === 'setup' ? 'active' : ''} onClick={() => onChange('setup')}>
        Подключения
      </button>
      <button type="button" className={tab === 'insights' ? 'active' : ''} onClick={() => onChange('insights')}>
        Insights
      </button>
    </nav>
  )
}
