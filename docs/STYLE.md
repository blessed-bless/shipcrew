# Portfolio style standard

Target look: one developer, calm and concrete. Behavior stays the same; style aligns.

## Layout

```
backend/app/       # this monorepo keeps API here (not src/)
frontend/src/      # React UI
tests/             # under backend/
Dockerfile         # multi-stage, non-root
docker-compose.yml
Makefile           # run test lint fmt
.env.example       # commented keys, no secrets
README.md
```

ShipCrew runner names (`codex`, `claude`, `cursor`) are product features — do not rename.

## Python

- Version: **3.12**
- Tooling: **ruff** for lint + format
- Config: **pydantic-settings**
- Logging: stdlib `logging`, one formatter
- Comments: English only, explain *why*

## JS / TS

- Existing tool only (oxlint). Do not add a second stack without asking.

## Infra

- Dockerfile: multi-stage; final image non-root
- Makefile: `run`, `test`, `lint`, `fmt`
- `.env.example`: every runtime variable with a short comment

## README

One sentence · screenshot · 4–6 capabilities · mermaid · stack · run · config table.

## Commits

Conventional Commits, English, short. Sole human author.
