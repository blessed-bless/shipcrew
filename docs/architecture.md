# ShipCrew architecture

## Layers

1. **API** (`backend/app/api/`) — routers v1 (`health`, `missions`, `connections`, `runners`, `projects`, `templates`, `index`), собираются в `factory.create_app`.
2. **Runtime** (`runtime/state.py`) — единый `AppState` на lifespan.
3. **Orchestration** (`orchestrator.py`) — pipeline, cancel, coerce schema, event log + SQLite sync.
4. **Domain** (`domain/`) — templates/playbooks, blackboard, projects, capabilities, validators.
5. **Adapters** — LLM client, OpenRouter OAuth, subscription runners (Codex/Claude/Cursor).
6. **Persistence** — JSON mission bodies + `shipcrew.db` (SQLite index) + event JSONL under `SHIPCREW_DATA_DIR`.
7. **UI** (`frontend/src`) — React Router pages: `/`, `/missions/:id`, `/setup`, `/insights`.

## HTTP stack

```
RequestContextMiddleware → CORS → /api|/api/v1 → routers → AppState
```

Каждый запрос получает `X-Request-ID` и пишется в лог `shipcrew.http`.

## Mission lifecycle

```
create → run → [pm → architect → engineer → reviewer → devops] → done
                     ↑_______________rework_________________|
cancel can interrupt between roles
```

После каждого шага payload прогоняется через `normalize_payload` + `coerce_role_payload` (Pydantic schemas в `schemas/agent_outputs.py`). Issues валидации уходят в SSE `agent_finished.schema_issues`.

## Blackboard

Each agent turn can contribute:

- facts
- decisions
- open questions
- blockers

The digest is injected into the next role prompt (LLM and CLI runners).

## Templates

Templates are not just labels. Each role gets a playbook:

- mission focus
- checklist
- anti-patterns
- output schema hints

## Runners

| Backend | Mechanism | Billing |
|---|---|---|
| `llm` | OpenAI-compatible HTTP | OpenRouter/API key |
| `codex` | `codex exec` | ChatGPT subscription |
| `claude` | `claude -p` | Claude subscription via official CLI |
| `cursor` | `@cursor/sdk` | Cursor subscription via SDK login |
