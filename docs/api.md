# ShipCrew HTTP API

Base: `http://127.0.0.1:8787`

## Health & catalog

- `GET /api/health`
- `GET /api/crew`
- `GET /api/providers`
- `GET /api/templates`
- `GET /api/templates/{id}`
- `GET /api/capabilities`
- `GET /api/metrics`

## Projects

- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{id}`
- `DELETE /api/projects/{id}`

## Connections

- `GET /api/connections`
- `POST /api/connections`
- `POST /api/connections/{id}/activate`
- `DELETE /api/connections/{id}`
- `POST /api/connections/oauth/openrouter/start`
- `GET /api/connections/oauth/openrouter/callback`

## Runners

- `GET /api/runners`
- `POST /api/runners/{codex|claude|cursor}/login`
- `GET /api/runners/{id}/login`

## Missions

- `GET /api/missions`
- `POST /api/missions`
- `GET /api/missions/{id}`
- `POST /api/missions/{id}/run`
- `POST /api/missions/{id}/cancel`
- `DELETE /api/missions/{id}`
- `GET /api/missions/{id}/events` (SSE)
- `GET /api/missions/{id}/artifacts/{path}`
- `GET /api/missions/{id}/bundle.zip`

### Create mission body

```json
{
  "title": "Notes API",
  "goal": "Ship a tiny notes service",
  "constraints": "No auth in MVP",
  "stack_hint": "Python FastAPI + React",
  "template_id": "greenfield-saas",
  "project_id": null,
  "engineer_runner": "llm",
  "reviewer_runner": "llm"
}
```
