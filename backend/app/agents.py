from __future__ import annotations

from dataclasses import dataclass

from .llm import LLMClient, parse_json_payload
from .models import AgentRole, Mission


@dataclass(frozen=True)
class AgentSpec:
    role: AgentRole
    title: str
    system: str


AGENTS: dict[AgentRole, AgentSpec] = {
    AgentRole.pm: AgentSpec(
        role=AgentRole.pm,
        title="Product Manager",
        system=(
            "You are the PM of an AI shipping crew. "
            "Turn the goal into milestones and acceptance criteria. "
            "Reply ONLY with JSON: summary, milestones[], acceptance[], risks[]."
        ),
    ),
    AgentRole.architect: AgentSpec(
        role=AgentRole.architect,
        title="Architect",
        system=(
            "You are the Architect. Design a minimal production-ready structure. "
            "Reply ONLY with JSON: summary, components[], data_flow, interfaces{}, files[]."
        ),
    ),
    AgentRole.engineer: AgentSpec(
        role=AgentRole.engineer,
        title="Engineer",
        system=(
            "You are the Engineer. Produce concrete file contents for the MVP. "
            "Reply ONLY with JSON: summary, files{path:content}, notes[]. "
            "Keep files small but runnable."
        ),
    ),
    AgentRole.reviewer: AgentSpec(
        role=AgentRole.reviewer,
        title="Reviewer",
        system=(
            "You are the Reviewer. Check the plan and code for ship blockers. "
            "Reply ONLY with JSON: summary, approved(bool), findings[], required_fixes[]. "
            "Approve unless there is a hard blocker."
        ),
    ),
    AgentRole.devops: AgentSpec(
        role=AgentRole.devops,
        title="DevOps",
        system=(
            "You are DevOps. Package the work for production-like run. "
            "Reply ONLY with JSON: summary, files{path:content}, ship_notes[]. "
            "Include docker-compose and a short SHIP checklist."
        ),
    ),
}


PIPELINE: list[AgentRole] = [
    AgentRole.pm,
    AgentRole.architect,
    AgentRole.engineer,
    AgentRole.reviewer,
    AgentRole.devops,
]


def _context_blob(mission: Mission) -> str:
    recent = mission.messages[-8:]
    history = "\n\n".join(f"[{m.role.value}] {m.content[:4000]}" for m in recent)
    return (
        f"TITLE: {mission.title}\n"
        f"GOAL: {mission.goal}\n"
        f"CONSTRAINTS: {mission.constraints or '-'}\n"
        f"STACK: {mission.stack_hint}\n"
        f"REVIEW_ROUND: {mission.review_round}\n\n"
        f"HISTORY:\n{history or '(empty)'}"
    )


async def run_agent(llm: LLMClient, mission: Mission, role: AgentRole) -> dict:
    spec = AGENTS[role]
    raw = await llm.complete(spec.system, _context_blob(mission), role_name=role.value)
    return parse_json_payload(raw)
