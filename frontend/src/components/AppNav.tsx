import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Миссии', end: true },
  { to: '/setup', label: 'Подключения' },
  { to: '/insights', label: 'Insights' },
]

export function AppNav() {
  return (
    <nav className="tabs" aria-label="Разделы">
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) => (isActive ? 'active' : undefined)}
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}
