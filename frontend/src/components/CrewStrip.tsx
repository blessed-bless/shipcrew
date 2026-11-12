import type { CrewMember } from '../types'
import { ROLE_LABEL } from '../types'

type Props = {
  crew: CrewMember[]
  activeRole?: string | null
}

export function CrewStrip({ crew, activeRole }: Props) {
  return (
    <section className="crew" aria-label="Состав команды">
      {crew.map((member) => (
        <div key={member.role} className={`crew-slot ${activeRole === member.role ? 'active' : ''}`}>
          <span className="role">{ROLE_LABEL[member.role] || member.role}</span>
          <span className="title">{member.title}</span>
        </div>
      ))}
    </section>
  )
}
