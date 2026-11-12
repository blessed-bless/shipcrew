# Subscription runners

ShipCrew never steals provider OAuth tokens into a fake OpenAI client.

## Codex

```bash
codex login
```

Mission field: `engineer_runner: "codex"` or `reviewer_runner: "codex"`.

Uses `codex exec -C <workdir> --json`.

## Claude Code

```bash
claude auth login
```

Uses official `claude -p --output-format json`.

## Cursor

```bash
cd tools/cursor-runner
npm install
node run.mjs login
```

Uses `@cursor/sdk` Agent.create/local cwd.

## OpenRouter

Browser OAuth PKCE in UI. Good default for multi-model LLM roles without installing CLIs.
