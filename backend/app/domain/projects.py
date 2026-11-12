from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    default_template_id: str = "greenfield-saas"
    default_stack: str = "Python FastAPI + React"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    description: str = ""
    default_template_id: str = "greenfield-saas"
    default_stack: str = "Python FastAPI + React"
    mission_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class ProjectSummary(BaseModel):
    id: str
    name: str
    description: str
    default_template_id: str
    mission_count: int
    updated_at: datetime
