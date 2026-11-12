# ShipCrew

Мультиагентная платформа доведения задач до prod-ready бандла.

Роли: **PM → Architect → Engineer → Reviewer → DevOps**  
Фичи: проекты, шаблоны команд, shared blackboard, OpenRouter OAuth, Codex/Claude/Cursor runners, metrics, zip ship bundle.

## Быстрый старт

```powershell
.\scripts\dev.ps1
```

Или Docker:

```bash
docker compose up --build
```

- UI: http://127.0.0.1:5173 (dev) / http://127.0.0.1:8787 (compose)
- API health: http://127.0.0.1:8787/api/health

## Структура

```
backend/app/
  domain/        templates, blackboard, projects, capabilities, validators
  persistence/   project store
  services/      metrics
  runners/       codex/claude/cursor adapters
  ...
frontend/src/
  components/    Header, Tabs, Setup, Insights, Feed...
  api.ts types.ts App.tsx
docs/            architecture, api, runners
```

## Документация

- [Architecture](docs/architecture.md)
- [HTTP API](docs/api.md)
- [Runners](docs/runners.md)

## Проверки

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## Автор

Богдан Щербинин ([blessed-bless](https://github.com/blessed-bless))
