export type CrewMember = { role: string; title: string }

export type ProviderInfo = {
  id: string
  name: string
  auth_methods: string[]
  oauth_label: string | null
  default_base_url: string
  default_model: string
  blocked_oauth_reason?: string
}

export type Connection = {
  id: string
  provider: string
  label: string
  auth_method: string
  model: string
  key_preview: string
  active: boolean
}

export type RunnerInfo = {
  id: string
  name: string
  installed: boolean
  logged_in: boolean
  auth_label: string
  notes: string
  login_job?: { status: string; ok: boolean | null; message: string } | null
}

export type MissionSummary = {
  id: string
  title: string
  status: string
  current_role: string | null
  artifact_count: number
  updated_at: string
}

export type AgentMessage = {
  id: string
  role: string
  content: string
  artifact_paths: string[]
  created_at: string
}

export type Mission = {
  id: string
  title: string
  goal: string
  constraints: string
  status: string
  current_role: string | null
  engineer_runner: string
  reviewer_runner: string
  template_id: string
  project_id: string | null
  messages: AgentMessage[]
  artifacts: { path: string; kind: string; created_by: string }[]
  blackboard?: Record<string, unknown>
  ship_bundle: string | null
  error: string | null
}

export type CrewTemplate = {
  id: string
  name: string
  description: string
  tags: string[]
  default_stack: string
  recommended_engineer: string
  recommended_reviewer: string
  starter_goals: string[]
}

export type ProjectSummary = {
  id: string
  name: string
  description: string
  default_template_id: string
  mission_count: number
  updated_at: string
}

export type Metrics = {
  mission_count: number
  status_counts: Record<string, number>
  engineer_runner_counts: Record<string, number>
  artifact_count: number
  message_count: number
  avg_duration_seconds: number
  success_rate: number
}

export const ROLE_LABEL: Record<string, string> = {
  pm: 'PM',
  architect: 'Architect',
  engineer: 'Engineer',
  reviewer: 'Reviewer',
  devops: 'DevOps',
}
