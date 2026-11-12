import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type {
  Connection,
  CrewMember,
  CrewTemplate,
  Metrics,
  MissionSummary,
  ProjectSummary,
  ProviderInfo,
  RunnerInfo,
} from '../types'

export type HealthInfo = {
  demo_mode: boolean
  model: string
  active_provider: string | null
  active_auth: string | null
  api?: string
}

export function useShipCrewData() {
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [runners, setRunners] = useState<RunnerInfo[]>([])
  const [templates, setTemplates] = useState<CrewTemplate[]>([])
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [history, setHistory] = useState<MissionSummary[]>([])
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const refreshAll = useCallback(async () => {
    const [c, r, h, m, t, p, met] = await Promise.all([
      api<Connection[]>('/api/connections'),
      api<RunnerInfo[]>('/api/runners'),
      api<HealthInfo>('/api/health'),
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
  }, [])

  useEffect(() => {
    void api<CrewMember[]>('/api/crew').then(setCrew).catch(() => setCrew([]))
    void api<ProviderInfo[]>('/api/providers').then(setProviders).catch(() => setProviders([]))
    void refreshAll().catch(() => undefined)
  }, [refreshAll])

  return {
    crew,
    providers,
    connections,
    runners,
    templates,
    projects,
    metrics,
    history,
    health,
    error,
    notice,
    setError,
    setNotice,
    refreshAll,
  }
}
