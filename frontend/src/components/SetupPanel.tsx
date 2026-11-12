import type { FormEvent } from 'react'
import type { Connection, ProviderInfo, RunnerInfo } from '../types'

type Props = {
  providers: ProviderInfo[]
  connections: Connection[]
  runners: RunnerInfo[]
  keyProvider: string
  apiKey: string
  keyModel: string
  connBusy: boolean
  runnerBusy: string | null
  onKeyProvider: (v: string) => void
  onApiKey: (v: string) => void
  onKeyModel: (v: string) => void
  onSaveKey: (e: FormEvent) => void
  onOpenRouter: () => void
  onActivate: (id: string) => void
  onDeleteConnection: (id: string) => void
  onLoginRunner: (id: string) => void
}

export function SetupPanel(props: Props) {
  const openrouter = props.providers.find((p) => p.id === 'openrouter')
  const anthropic = props.providers.find((p) => p.id === 'anthropic')

  return (
    <div className="setup">
      <section className="panel">
        <h2>Модели (OpenRouter / API)</h2>
        <div className="conn-actions">
          <button
            type="button"
            className="secondary"
            disabled={props.connBusy || !openrouter}
            onClick={props.onOpenRouter}
          >
            {props.connBusy ? 'Открываем OpenRouter…' : openrouter?.oauth_label || 'Войти через OpenRouter'}
          </button>
        </div>
        {anthropic?.blocked_oauth_reason ? <p className="warn">{anthropic.blocked_oauth_reason}</p> : null}
        <form className="key-form" onSubmit={props.onSaveKey}>
          <label>
            Провайдер
            <select
              value={props.keyProvider}
              onChange={(e) => {
                props.onKeyProvider(e.target.value)
                props.onKeyModel(props.providers.find((x) => x.id === e.target.value)?.default_model || '')
              }}
            >
              {props.providers.map((p) => (
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
              value={props.apiKey}
              onChange={(e) => props.onApiKey(e.target.value)}
              required={props.keyProvider !== 'ollama'}
            />
          </label>
          <label>
            Модель
            <input value={props.keyModel} onChange={(e) => props.onKeyModel(e.target.value)} />
          </label>
          <button type="submit" disabled={props.connBusy}>
            Сохранить ключ
          </button>
        </form>
        <ul className="conn-list">
          {props.connections.map((c) => (
            <li key={c.id} className={c.active ? 'active' : ''}>
              <div>
                <strong>{c.label}</strong>
                <span>
                  {c.provider} · {c.auth_method} · {c.key_preview} · {c.model}
                </span>
              </div>
              <div className="row-actions">
                {!c.active ? (
                  <button type="button" className="ghost" onClick={() => props.onActivate(c.id)}>
                    Активировать
                  </button>
                ) : (
                  <span className="pill live">active</span>
                )}
                <button type="button" className="ghost danger" onClick={() => props.onDeleteConnection(c.id)}>
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
          {props.runners.map((r) => (
            <li key={r.id} className={r.logged_in ? 'active' : ''}>
              <div>
                <strong>{r.name}</strong>
                <span>
                  {r.installed ? 'installed' : 'missing'} · {r.auth_label}
                </span>
                <span>{r.notes}</span>
              </div>
              <button
                type="button"
                className="ghost"
                disabled={!r.installed || props.runnerBusy === r.id}
                onClick={() => props.onLoginRunner(r.id)}
              >
                {props.runnerBusy === r.id ? 'Ждём браузер…' : 'Войти'}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
