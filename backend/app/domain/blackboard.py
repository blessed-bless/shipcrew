from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class BlackboardEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    key: str
    role: str
    value: Any
    created_at: datetime = Field(default_factory=utc_now)


class Blackboard(BaseModel):
    """Shared working memory for the crew during a mission."""

    mission_id: str
    entries: list[BlackboardEntry] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    def put(self, key: str, role: str, value: Any) -> BlackboardEntry:
        entry = BlackboardEntry(key=key, role=role, value=value)
        self.entries.append(entry)
        self.facts[key] = value
        return entry

    def ask(self, question: str) -> None:
        if question and question not in self.open_questions:
            self.open_questions.append(question)

    def decide(self, decision: str) -> None:
        if decision and decision not in self.decisions:
            self.decisions.append(decision)

    def block(self, blocker: str) -> None:
        if blocker and blocker not in self.blockers:
            self.blockers.append(blocker)

    def resolve_blocker(self, blocker: str) -> None:
        self.blockers = [b for b in self.blockers if b != blocker]

    def digest(self, *, max_chars: int = 3500) -> str:
        lines = [
            f"FACTS ({len(self.facts)}):",
            *[f"- {k}: {_short(v)}" for k, v in list(self.facts.items())[-12:]],
            f"DECISIONS ({len(self.decisions)}):",
            *[f"- {d}" for d in self.decisions[-8:]],
            f"OPEN QUESTIONS ({len(self.open_questions)}):",
            *[f"- {q}" for q in self.open_questions[-8:]],
            f"BLOCKERS ({len(self.blockers)}):",
            *[f"- {b}" for b in self.blockers[-8:]],
        ]
        text = "\n".join(lines)
        return text[:max_chars]


def _short(value: Any, limit: int = 180) -> str:
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def ingest_agent_payload(board: Blackboard, role: str, payload: dict[str, Any]) -> None:
    """Pull structured leftovers from an agent JSON into shared memory."""
    summary = payload.get("summary")
    if isinstance(summary, str) and summary.strip():
        board.put(f"{role}.summary", role, summary.strip())
        board.decide(f"{role}: {summary.strip()[:240]}")

    for key in ("milestones", "acceptance", "components", "notes", "ship_notes"):
        val = payload.get(key)
        if isinstance(val, list) and val:
            board.put(f"{role}.{key}", role, val)

    risks = payload.get("risks") or payload.get("required_fixes") or []
    if isinstance(risks, list):
        for item in risks[:8]:
            text = item if isinstance(item, str) else str(item)
            board.block(f"{role}: {text}")

    findings = payload.get("findings")
    if isinstance(findings, list):
        for item in findings[:8]:
            if isinstance(item, dict):
                board.ask(str(item.get("item") or item))
            else:
                board.ask(str(item))

    if payload.get("approved") is True:
        board.resolve_blocker(f"{role}: rejected")
        board.decide(f"{role} approved current draft")
