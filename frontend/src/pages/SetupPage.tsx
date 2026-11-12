import { useEffect, useState } from 'react'
import { api } from '../api'
import { SetupPanel } from '../components/SetupPanel'
import type { useShipCrewData } from '../hooks/useShipCrewData'

type Props = {
  data: ReturnType<typeof useShipCrewData>
}

export function SetupPage({ data }: Props) {
  const {
    providers,
    connections,
    runners,
    refreshAll,
    setError,
    setNotice,
  } = data
  const [keyProvider, setKeyProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [keyModel, setKeyModel] = useState('')
  const [connBusy, setConnBusy] = useState(false)
  const [runnerBusy, setRunnerBusy] = useState<string | null>(null)

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
  }, [runnerBusy, refreshAll, setNotice])

  return (
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
  )
}
