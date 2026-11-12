from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ..models import Mission, MissionStatus


def mission_metrics(missions: list[Mission]) -> dict[str, Any]:
    statuses = Counter(m.status.value for m in missions)
    runners = Counter(m.engineer_runner for m in missions)
    total_artifacts = sum(len(m.artifacts) for m in missions)
    total_messages = sum(len(m.messages) for m in missions)
    done = [m for m in missions if m.status == MissionStatus.done]
    failed = [m for m in missions if m.status == MissionStatus.failed]
    durations = []
    for m in done + failed:
        try:
            durations.append((m.updated_at - m.created_at).total_seconds())
        except Exception:  # noqa: BLE001
            continue
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission_count": len(missions),
        "status_counts": dict(statuses),
        "engineer_runner_counts": dict(runners),
        "artifact_count": total_artifacts,
        "message_count": total_messages,
        "avg_duration_seconds": round(avg_duration, 2),
        "success_rate": round(len(done) / len(missions), 3) if missions else 0.0,
    }
