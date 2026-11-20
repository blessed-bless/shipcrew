from __future__ import annotations

from pathlib import Path

from ..agents import resolve_agent
from ..domain.blackboard import Blackboard
from ..llm import parse_json_payload
from ..models import AgentRole, Mission
from . import claude_runner, codex_runner, cursor_runner
from .types import RunnerExecResult, RunnerId, RunnerLoginResult, RunnerStatus


class RunnerService:
    def list_status(self) -> list[RunnerStatus]:
        return [codex_runner.status(), claude_runner.status(), cursor_runner.status()]

    def get_status(self, runner_id: RunnerId) -> RunnerStatus:
        mapping = {
            RunnerId.codex: codex_runner.status,
            RunnerId.claude: claude_runner.status,
            RunnerId.cursor: cursor_runner.status,
        }
        return mapping[runner_id]()

    async def login(self, runner_id: RunnerId) -> RunnerLoginResult:
        mapping = {
            RunnerId.codex: codex_runner.login,
            RunnerId.claude: claude_runner.login,
            RunnerId.cursor: cursor_runner.login,
        }
        return await mapping[runner_id]()

    async def run_role(
        self,
        runner_id: RunnerId,
        mission: Mission,
        role: AgentRole,
        workdir: Path,
        *,
        timeout_s: float = 600.0,
    ) -> dict:
        spec = resolve_agent(mission, role)
        board = (
            Blackboard.model_validate(mission.blackboard)
            if mission.blackboard
            else Blackboard(mission_id=mission.id)
        )
        prompt = (
            f"{spec.system}\n\n"
            f"TITLE: {mission.title}\n"
            f"GOAL: {mission.goal}\n"
            f"CONSTRAINTS: {mission.constraints or '-'}\n"
            f"STACK: {mission.stack_hint}\n"
            f"TEMPLATE: {mission.template_id}\n"
            f"WORKDIR: {workdir}\n\n"
            f"BLACKBOARD:\n{board.digest()}\n\n"
            "Write any files into the working directory. "
            "Prefer a short final answer. If possible end with JSON matching the role schema."
        )
        result = await self._exec(runner_id, prompt, workdir, timeout_s=timeout_s)
        payload = parse_json_payload(result.summary)
        if (
            "summary" not in payload
            or payload.get("summary") == result.summary
            and "raw" in payload
        ):
            payload = {
                "summary": result.summary[:2000] or f"{runner_id.value} finished",
                "runner": runner_id.value,
                "ok": result.ok,
                "exit_code": result.exit_code,
                "files_touched": result.files_written,
                "stderr_tail": result.stderr[-1000:],
            }
        else:
            payload.setdefault("runner", runner_id.value)
            payload.setdefault("files_touched", result.files_written)
            payload.setdefault("ok", result.ok)

        # Pull files the CLI wrote to disk when JSON files{} is empty.
        files = payload.get("files")
        if not isinstance(files, dict):
            files = {}
        for rel in result.files_written:
            if rel in files:
                continue
            path = workdir / rel
            if path.is_file() and path.stat().st_size < 400_000:
                try:
                    files[rel] = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
        if files:
            payload["files"] = files
        if not result.ok and not payload.get("summary"):
            payload["summary"] = (
                f"{runner_id.value} failed: {result.stderr[-500:] or result.stdout[-500:]}"
            )
        return payload

    async def _exec(
        self, runner_id: RunnerId, prompt: str, workdir: Path, *, timeout_s: float
    ) -> RunnerExecResult:
        if runner_id == RunnerId.codex:
            return await codex_runner.run(prompt, workdir, timeout_s=timeout_s)
        if runner_id == RunnerId.claude:
            return await claude_runner.run(prompt, workdir, timeout_s=timeout_s)
        if runner_id == RunnerId.cursor:
            return await cursor_runner.run(prompt, workdir, timeout_s=timeout_s)
        raise ValueError(f"unknown runner: {runner_id}")
