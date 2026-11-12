# ShipCrew architecture

## Layers

1. **API** (`backend/app/main.py`) — HTTP surface for missions, connections, runners, projects, templates, metrics.
2. **Orchestration** (`orchestrator.py`) — pipeline loop, cancel, artifact materialization, blackboard updates.
3. **Domain** (`domain/`) — templates/playbooks, blackboard, projects, capabilities catalog.
4. **Adapters** — LLM client, OpenRouter OAuth, subscription runners (Codex/Claude/Cursor).
5. **Persistence** — JSON stores under `SHIPCREW_DATA_DIR` for missions/connections/projects.
6. **UI** (`frontend/src`) — React panels for missions/setup/insights.

## Mission lifecycle

```
create → run → [pm → architect → engineer → reviewer → devops] → done
                     ↑_______________rework_________________|
cancel can interrupt between roles
```

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
