import { parseMessage } from '../api'
import type { Mission } from '../types'
import { ROLE_LABEL } from '../types'

type Props = {
  mission: Mission | null
  statusText: string
  running: boolean
  selectedArtifact: { path: string; content: string } | null
  onCancel: () => void
  onRerun: () => void
  onViewArtifact: (path: string) => void
  onCloseArtifact: () => void
}

export function MissionFeed({
  mission,
  statusText,
  running,
  selectedArtifact,
  onCancel,
  onRerun,
  onViewArtifact,
  onCloseArtifact,
}: Props) {
  return (
    <section className="panel feed">
      <div className="feed-head">
        <div>
          <h2>{mission?.title || 'Лента'}</h2>
          <p>{statusText}</p>
        </div>
        <div className="row-actions">
          {running ? (
            <button type="button" className="ghost danger" onClick={onCancel}>
              Остановить
            </button>
          ) : null}
          {mission && !running ? (
            <button type="button" className="ghost" onClick={onRerun}>
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
        <p className="empty">Здесь появится переписка агентов и blackboard-решения.</p>
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
                        <button key={p} type="button" className="ghost tiny" onClick={() => onViewArtifact(p)}>
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
                  <button key={a.path} type="button" className="ghost tiny" onClick={() => onViewArtifact(a.path)}>
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
                <button type="button" className="ghost tiny" onClick={onCloseArtifact}>
                  Закрыть
                </button>
              </div>
              <pre>{selectedArtifact.content}</pre>
            </div>
          ) : null}
        </>
      )}
    </section>
  )
}
