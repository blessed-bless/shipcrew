import { useState } from 'react'
import { api } from '../api'
import { InsightsPanel } from '../components/InsightsPanel'
import type { useShipCrewData } from '../hooks/useShipCrewData'

type Props = {
  data: ReturnType<typeof useShipCrewData>
  templateId?: string
}

export function InsightsPage({ data, templateId = 'greenfield-saas' }: Props) {
  const { metrics, templates, projects, refreshAll, setError } = data
  const [projectName, setProjectName] = useState('')
  const [projectDesc, setProjectDesc] = useState('')

  return (
    <InsightsPanel
      metrics={metrics}
      templates={templates}
      projects={projects}
      projectName={projectName}
      projectDesc={projectDesc}
      onProjectName={setProjectName}
      onProjectDesc={setProjectDesc}
      onCreateProject={() => {
        void api('/api/projects', {
          method: 'POST',
          body: JSON.stringify({
            name: projectName,
            description: projectDesc,
            default_template_id: templateId,
          }),
        })
          .then(async () => {
            setProjectName('')
            setProjectDesc('')
            await refreshAll()
          })
          .catch((err: Error) => setError(err.message))
      }}
      onDeleteProject={(id) => void api(`/api/projects/${id}`, { method: 'DELETE' }).then(refreshAll)}
    />
  )
}
