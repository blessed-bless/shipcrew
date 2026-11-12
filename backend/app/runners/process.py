from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path


# Не даём случайно уехать на metered API, если в окружении висят ключи.
STRIP_ENV = {
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_API_KEY",
    "CURSOR_API_KEY",
}


def which(name: str) -> str | None:
    return shutil.which(name)


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in STRIP_ENV:
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


async def run_cmd(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout_s: float = 600.0,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd) if cwd else None,
        env=env or clean_env(),
        stdin=asyncio.subprocess.PIPE if input_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(input=input_text.encode("utf-8") if input_text is not None else None),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "", f"timeout after {timeout_s}s: {' '.join(cmd)}"
    return (
        int(proc.returncode or 0),
        stdout_b.decode("utf-8", errors="replace"),
        stderr_b.decode("utf-8", errors="replace"),
    )


def snapshot_files(root: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not root.exists():
        return out
    for path in root.rglob("*"):
        if path.is_file():
            try:
                out[str(path.relative_to(root)).replace("\\", "/")] = path.stat().st_mtime
            except OSError:
                continue
    return out


def changed_files(before: dict[str, float], after: dict[str, float]) -> list[str]:
    changed = []
    for path, mtime in after.items():
        if path not in before or before[path] < mtime:
            changed.append(path)
    return sorted(changed)
