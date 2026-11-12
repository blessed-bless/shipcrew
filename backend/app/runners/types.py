from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RunnerId(str, Enum):
    codex = "codex"
    claude = "claude"
    cursor = "cursor"


class RunnerStatus(BaseModel):
    id: RunnerId
    name: str
    binary: str | None
    installed: bool
    logged_in: bool
    auth_label: str
    login_command: str
    run_command_hint: str
    notes: str = ""
    detail: str = ""


class RunnerLoginResult(BaseModel):
    ok: bool
    runner: RunnerId
    message: str
    opened_browser_flow: bool = False
    command: list[str] = Field(default_factory=list)


class RunnerExecResult(BaseModel):
    ok: bool
    runner: RunnerId
    summary: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    files_written: list[str] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)
