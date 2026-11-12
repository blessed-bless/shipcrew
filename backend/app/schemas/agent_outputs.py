from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PmOutput(BaseModel):
    summary: str
    milestones: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ArchitectOutput(BaseModel):
    summary: str
    components: list[str] = Field(default_factory=list)
    data_flow: str = ""
    interfaces: dict[str, Any] = Field(default_factory=dict)
    files: list[str] = Field(default_factory=list)


class EngineerOutput(BaseModel):
    summary: str
    files: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    severity: str = "info"
    item: str


class ReviewerOutput(BaseModel):
    summary: str
    approved: bool = True
    findings: list[Finding] = Field(default_factory=list)
    required_fixes: list[str] = Field(default_factory=list)


class DevopsOutput(BaseModel):
    summary: str
    files: dict[str, str] = Field(default_factory=dict)
    ship_notes: list[str] = Field(default_factory=list)


ROLE_MODELS: dict[str, type[BaseModel]] = {
    "pm": PmOutput,
    "architect": ArchitectOutput,
    "engineer": EngineerOutput,
    "reviewer": ReviewerOutput,
    "devops": DevopsOutput,
}


def coerce_role_payload(role: str, payload: dict[str, Any]) -> dict[str, Any]:
    model = ROLE_MODELS.get(role)
    if model is None:
        return payload
    try:
        return model.model_validate(payload).model_dump()
    except Exception:  # noqa: BLE001 — keep pipeline moving with raw payload
        return payload
