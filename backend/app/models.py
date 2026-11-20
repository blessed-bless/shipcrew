from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid4().hex


class MissionStatus(str, Enum):
    queued = "queued"
    running = "running"
    needs_human = "needs_human"
    shipping = "shipping"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class AgentRole(str, Enum):
    pm = "pm"
    architect = "architect"
    engineer = "engineer"
    reviewer = "reviewer"
    devops = "devops"


class AgentMessage(BaseModel):
    id: str = Field(default_factory=new_id)
    role: AgentRole
    content: str
    artifact_paths: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class Artifact(BaseModel):
    path: str
    kind: str
    summary: str = ""
    created_by: AgentRole
    created_at: datetime = Field(default_factory=utc_now)


class MissionCreate(BaseModel):
    title: str
    goal: str
    constraints: str = ""
    stack_hint: str = "Python FastAPI + React"
    # llm | codex | claude | cursor — subscription CLI/SDK instead of HTTP API
    engineer_runner: str = "llm"
    reviewer_runner: str = "llm"
    template_id: str = "greenfield-saas"
    project_id: str | None = None


class Mission(BaseModel):
    id: str = Field(default_factory=new_id)
    title: str
    goal: str
    constraints: str = ""
    stack_hint: str = "Python FastAPI + React"
    engineer_runner: str = "llm"
    reviewer_runner: str = "llm"
    template_id: str = "greenfield-saas"
    project_id: str | None = None
    status: MissionStatus = MissionStatus.queued
    current_role: AgentRole | None = None
    review_round: int = 0
    messages: list[AgentMessage] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    blackboard: dict[str, Any] = Field(default_factory=dict)
    ship_bundle: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class MissionSummary(BaseModel):
    id: str
    title: str
    status: MissionStatus
    current_role: AgentRole | None
    artifact_count: int
    created_at: datetime
    updated_at: datetime


class MissionEvent(BaseModel):
    type: str
    mission_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
