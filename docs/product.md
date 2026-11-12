# Product surface

ShipCrew is a local-first control plane for an AI shipping crew.

## Personas

- Solo founder shipping MVPs overnight
- Freelancer who already pays for ChatGPT/Claude/Cursor and wants orchestration
- Small team that wants reproducible mission history + zip artifacts

## Core loop

1. Pick template + optional project
2. Connect LLM (OpenRouter/API) and/or subscription runners
3. Launch mission (`/` or `/missions/:id` in UI)
4. Watch role feed + blackboard decisions (SSE + JSONL event log)
5. Download zip / re-run / cancel
6. Browse SQLite mission index / metrics in Insights

## Non-goals (for now)

- Multi-tenant SaaS billing
- Spoofing Claude.ai / Cursor private model APIs
- Fully autonomous production deploys to customer infra without review
