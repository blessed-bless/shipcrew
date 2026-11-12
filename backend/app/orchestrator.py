from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from .agents import PIPELINE, run_agent
from .config import Settings
from .connections import ConnectionStore
from .llm import LLMClient, LLMError
from .models import AgentMessage, AgentRole, Mission, MissionStatus
from .runners import RunnerService
from .runners.types import RunnerId
from .storage import MissionStore

EventCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


class Orchestrator:
    def __init__(
        self,
        store: MissionStore,
        settings: Settings,
        connections: ConnectionStore | None = None,
        runners: RunnerService | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.connections = connections
        self.runners = runners or RunnerService()
        self.llm = self._build_llm()
        self._tasks: dict[str, asyncio.Task] = {}
        self._listeners: dict[str, list[EventCallback]] = {}

    def _build_llm(self) -> LLMClient:
        active = self.connections.get_active() if self.connections else None
        if active:
            return LLMClient(
                self.settings,
                api_key=active.api_key,
                base_url=active.base_url,
                model=active.model,
                provider=active.provider.value,
                force_live=True,
            )
        return LLMClient(self.settings)

    def refresh_llm(self) -> None:
        self.llm = self._build_llm()

    def subscribe(self, mission_id: str, callback: EventCallback) -> None:
        self._listeners.setdefault(mission_id, []).append(callback)

    def unsubscribe(self, mission_id: str, callback: EventCallback) -> None:
        listeners = self._listeners.get(mission_id, [])
        if callback in listeners:
            listeners.remove(callback)

    async def _emit(self, mission_id: str, event_type: str, payload: dict[str, Any]) -> None:
        for cb in list(self._listeners.get(mission_id, [])):
            result = cb(event_type, payload)
            if asyncio.iscoroutine(result):
                await result

    def start(self, mission: Mission) -> Mission:
        if mission.id in self._tasks and not self._tasks[mission.id].done():
            return mission
        self.refresh_llm()
        mission.status = MissionStatus.running
        mission.error = None
        self.store.save(mission)
        self._tasks[mission.id] = asyncio.create_task(self._run(mission.id))
        return mission

    async def _run(self, mission_id: str) -> None:
        mission = self.store.get(mission_id)
        if mission is None:
            return
        try:
            await self._emit(mission_id, "mission_started", {"status": mission.status.value})
            idx = 0
            while idx < len(PIPELINE):
                role = PIPELINE[idx]
                mission = self.store.get(mission_id) or mission
                mission.current_role = role
                mission.status = MissionStatus.running
                self.store.save(mission)
                await self._emit(mission_id, "agent_started", {"role": role.value})

                payload = await self._run_role(mission, role)
                artifacts = self._materialize_files(mission, role, payload)
                message = AgentMessage(
                    role=role,
                    content=json.dumps(payload, ensure_ascii=False, indent=2),
                    artifact_paths=[a.path for a in artifacts],
                )
                mission.messages.append(message)
                mission.artifacts.extend(artifacts)
                self.store.save(mission)
                await self._emit(
                    mission_id,
                    "agent_finished",
                    {
                        "role": role.value,
                        "message_id": message.id,
                        "artifact_paths": message.artifact_paths,
                        "summary": payload.get("summary", ""),
                    },
                )

                if role == AgentRole.reviewer:
                    approved = bool(payload.get("approved", True))
                    fixes = payload.get("required_fixes") or []
                    if not approved and fixes and mission.review_round < self.settings.max_review_rounds:
                        mission.review_round += 1
                        self.store.save(mission)
                        idx = PIPELINE.index(AgentRole.engineer)
                        continue

                if role == AgentRole.devops:
                    mission.status = MissionStatus.shipping
                    mission.ship_bundle = str(self.store.artifact_root(mission.id))
                    self.store.save(mission)
                    await self._emit(mission_id, "shipping", {"bundle": mission.ship_bundle})

                idx += 1

            mission = self.store.get(mission_id) or mission
            mission.status = MissionStatus.done
            mission.current_role = None
            self.store.save(mission)
            await self._emit(mission_id, "mission_done", {"status": "done", "bundle": mission.ship_bundle})
        except LLMError as exc:
            await self._fail(mission_id, str(exc))
        except Exception as exc:  # noqa: BLE001
            await self._fail(mission_id, f"Orchestrator crash: {exc}")

    async def _run_role(self, mission: Mission, role: AgentRole) -> dict[str, Any]:
        runner_name = "llm"
        if role == AgentRole.engineer:
            runner_name = (mission.engineer_runner or "llm").strip().lower()
        elif role == AgentRole.reviewer:
            runner_name = (mission.reviewer_runner or "llm").strip().lower()

        if runner_name in {r.value for r in RunnerId}:
            workdir = self.store.artifact_root(mission.id) / "workspace"
            workdir.mkdir(parents=True, exist_ok=True)
            return await self.runners.run_role(
                RunnerId(runner_name),
                mission,
                role,
                workdir,
                timeout_s=self.settings.runner_timeout_s,
            )
        return await run_agent(self.llm, mission, role)

    async def _fail(self, mission_id: str, error: str) -> None:
        mission = self.store.get(mission_id)
        if mission is None:
            return
        mission.status = MissionStatus.failed
        mission.error = error
        mission.current_role = None
        self.store.save(mission)
        await self._emit(mission_id, "mission_failed", {"error": error})

    def _materialize_files(self, mission: Mission, role: AgentRole, payload: dict[str, Any]) -> list:
        files = payload.get("files")
        if not isinstance(files, dict):
            # Persist the agent JSON as a report artifact so every step leaves a trail.
            report_name = f"reports/{role.value}-{len(mission.messages) + 1:02d}.json"
            art = self.store.write_artifact(
                mission.id,
                report_name,
                json.dumps(payload, ensure_ascii=False, indent=2),
                kind="report",
                created_by=role,
            )
            return [art]

        created = []
        for path, content in files.items():
            if not isinstance(path, str):
                continue
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2)
            kind = "code"
            lower = path.lower()
            if lower.endswith((".md", ".txt")):
                kind = "doc"
            elif "docker" in lower or lower.endswith((".yml", ".yaml")):
                kind = "infra"
            art = self.store.write_artifact(mission.id, path, text, kind=kind, created_by=role)
            created.append(art)
        return created
