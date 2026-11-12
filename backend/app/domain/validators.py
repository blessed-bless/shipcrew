from __future__ import annotations

from typing import Any


REQUIRED_BY_ROLE: dict[str, set[str]] = {
    "pm": {"summary", "milestones", "acceptance"},
    "architect": {"summary", "components", "files"},
    "engineer": {"summary", "files"},
    "reviewer": {"summary", "approved"},
    "devops": {"summary", "files"},
}


def validate_agent_payload(role: str, payload: dict[str, Any]) -> list[str]:
    """Return human-readable issues; empty list means good enough to continue."""
    issues: list[str] = []
    required = REQUIRED_BY_ROLE.get(role, {"summary"})
    for key in required:
        if key not in payload:
            issues.append(f"missing field `{key}`")
    if "files" in payload and not isinstance(payload["files"], dict):
        issues.append("`files` must be an object of path→content")
    if "approved" in payload and not isinstance(payload["approved"], bool):
        issues.append("`approved` must be boolean")
    if "milestones" in payload and not isinstance(payload.get("milestones"), list):
        issues.append("`milestones` must be a list")
    summary = payload.get("summary")
    if isinstance(summary, str) and len(summary.strip()) < 8:
        issues.append("summary too short")
    return issues


def normalize_payload(role: str, payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.setdefault("summary", f"{role} completed")
    if role in {"engineer", "devops", "architect"}:
        files = out.get("files")
        if not isinstance(files, dict):
            out["files"] = {}
    if role == "reviewer":
        out.setdefault("approved", True)
        out.setdefault("findings", [])
        out.setdefault("required_fixes", [])
    if role == "pm":
        out.setdefault("milestones", [])
        out.setdefault("acceptance", [])
        out.setdefault("risks", [])
    return out
