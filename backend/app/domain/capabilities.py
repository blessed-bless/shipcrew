from __future__ import annotations

from pydantic import BaseModel, Field


class Capability(BaseModel):
    id: str
    area: str
    title: str
    description: str
    status: str = "available"
    depends_on: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)


CAPABILITIES: list[Capability] = [
    Capability(
        id="mission-pipeline",
        area="orchestration",
        title="Mission pipeline",
        description="PM→Architect→Engineer→Reviewer→DevOps with cancel/restart.",
        endpoints=["/api/missions", "/api/missions/{id}/run", "/api/missions/{id}/cancel"],
    ),
    Capability(
        id="blackboard",
        area="orchestration",
        title="Shared blackboard",
        description="Facts/decisions/blockers shared across agent turns.",
        depends_on=["mission-pipeline"],
    ),
    Capability(
        id="crew-templates",
        area="orchestration",
        title="Crew templates",
        description="Playbooks for greenfield, bugfix, docs, platform slices.",
        endpoints=["/api/templates"],
    ),
    Capability(
        id="projects",
        area="workspace",
        title="Projects",
        description="Group missions under a product/workspace container.",
        endpoints=["/api/projects"],
    ),
    Capability(
        id="metrics",
        area="insights",
        title="Mission metrics",
        description="Success rate, durations, runner mix, artifact counts.",
        endpoints=["/api/metrics"],
    ),
    Capability(
        id="openrouter-oauth",
        area="auth",
        title="OpenRouter browser OAuth",
        description="PKCE login so usage bills to the user's OpenRouter account.",
        endpoints=["/api/connections/oauth/openrouter/start"],
    ),
    Capability(
        id="api-key-connections",
        area="auth",
        title="API key connections",
        description="OpenAI/Anthropic/Ollama BYOK connections with active selection.",
        endpoints=["/api/connections"],
    ),
    Capability(
        id="codex-runner",
        area="runners",
        title="Codex subscription runner",
        description="Official Codex CLI via ChatGPT subscription login.",
        endpoints=["/api/runners", "/api/runners/codex/login"],
    ),
    Capability(
        id="claude-runner",
        area="runners",
        title="Claude Code subscription runner",
        description="Official claude CLI; no third-party Claude.ai OAuth spoofing.",
        endpoints=["/api/runners/claude/login"],
    ),
    Capability(
        id="cursor-runner",
        area="runners",
        title="Cursor Agent SDK runner",
        description="Browser login via @cursor/sdk, agent harness execution.",
        endpoints=["/api/runners/cursor/login"],
    ),
    Capability(
        id="artifact-browser",
        area="shipping",
        title="Artifact browser",
        description="Read produced files from mission bundle.",
        endpoints=["/api/missions/{id}/artifacts/{path}"],
    ),
    Capability(
        id="bundle-zip",
        area="shipping",
        title="Ship bundle zip",
        description="Download the whole artifact tree as zip.",
        endpoints=["/api/missions/{id}/bundle.zip"],
    ),
    Capability(
        id="demo-mode",
        area="dx",
        title="Deterministic demo mode",
        description="Run the whole crew without external LLM keys.",
    ),
    Capability(
        id="sse-events",
        area="realtime",
        title="Mission SSE stream",
        description="Server-sent events for agent start/finish/ship/fail.",
        endpoints=["/api/missions/{id}/events"],
    ),
]


def list_capabilities() -> list[Capability]:
    return list(CAPABILITIES)


def capabilities_by_area() -> dict[str, list[Capability]]:
    out: dict[str, list[Capability]] = {}
    for item in CAPABILITIES:
        out.setdefault(item.area, []).append(item)
    return out
