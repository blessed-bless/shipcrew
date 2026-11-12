from __future__ import annotations

from dataclasses import dataclass

from .domain.blackboard import Blackboard
from .domain.templates import playbook_for
from .llm import LLMClient, parse_json_payload
from .models import AgentRole, Mission


@dataclass(frozen=True)
class AgentSpec:
    role: AgentRole
    title: str
    system: str


DEFAULT_AGENTS: dict[AgentRole, AgentSpec] = {
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

# Back-compat alias used across the codebase/UI.
AGENTS = DEFAULT_AGENTS

PIPELINE: list[AgentRole] = [
    AgentRole.pm,
    AgentRole.architect,
    AgentRole.engineer,
    AgentRole.reviewer,
    AgentRole.devops,
]


def resolve_agent(mission: Mission, role: AgentRole) -> AgentSpec:
    pb = playbook_for(mission.template_id, role)
    base = DEFAULT_AGENTS[role]
    if pb is None:
        return base
    schema = ", ".join(f"{k}:{v}" for k, v in pb.output_schema.items()) or "JSON object"
    checklist = "; ".join(pb.checklist) if pb.checklist else "-"
    anti = "; ".join(pb.anti_patterns) if pb.anti_patterns else "-"
    system = (
        f"You are {pb.title} in ShipCrew. Mission focus: {pb.mission}\n"
        f"Checklist: {checklist}\n"
        f"Avoid: {anti}\n"
        f"Reply ONLY with JSON fields: {schema}."
    )
    return AgentSpec(role=role, title=pb.title, system=system)


def _context_blob(mission: Mission, board: Blackboard | None = None) -> str:
    recent = mission.messages[-8:]
    history = "\n\n".join(f"[{m.role.value}] {m.content[:4000]}" for m in recent)
    board_text = board.digest() if board is not None else "(empty)"
    pb = playbook_for(mission.template_id, mission.current_role) if mission.current_role else None
    playbook_bits = ""
    if pb is not None:
        playbook_bits = (
            f"PLAYBOOK_TITLE: {pb.title}\n"
            f"PLAYBOOK_MISSION: {pb.mission}\n"
            f"PLAYBOOK_CHECKLIST: {', '.join(pb.checklist)}\n"
        )
    return (
        f"TITLE: {mission.title}\n"
        f"GOAL: {mission.goal}\n"
        f"CONSTRAINTS: {mission.constraints or '-'}\n"
        f"STACK: {mission.stack_hint}\n"
        f"TEMPLATE: {mission.template_id}\n"
        f"REVIEW_ROUND: {mission.review_round}\n"
        f"{playbook_bits}\n"
        f"BLACKBOARD:\n{board_text}\n\n"
        f"HISTORY:\n{history or '(empty)'}"
    )


async def run_agent(
    llm: LLMClient,
    mission: Mission,
    role: AgentRole,
    board: Blackboard | None = None,
) -> dict:
    spec = resolve_agent(mission, role)
    raw = await llm.complete(spec.system, _context_blob(mission, board), role_name=role.value)
    return parse_json_payload(raw)
