from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Settings
from ..connections import ConnectionStore
from ..oauth import OAuthManager
from ..orchestrator import Orchestrator
from ..persistence.project_store import ProjectStore
from ..persistence.sqlite import SqliteIndex
from ..runners import RunnerService
from ..services.event_log import EventLog
from ..storage import MissionStore


@dataclass
class AppState:
    settings: Settings
    data_dir: Path
    store: MissionStore
    projects: ProjectStore
    connections: ConnectionStore
    oauth: OAuthManager
    runners: RunnerService
    orchestrator: Orchestrator
    events: EventLog
    sqlite: SqliteIndex | None = None
    login_jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
