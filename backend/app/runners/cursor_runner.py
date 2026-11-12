from __future__ import annotations

import json
from pathlib import Path

from .process import changed_files, clean_env, run_cmd, snapshot_files, which
from .types import RunnerExecResult, RunnerId, RunnerLoginResult, RunnerStatus

NAME = "Cursor Agent SDK (subscription)"


def _script_path() -> Path:
    # backend/app/runners -> repo root
    return Path(__file__).resolve().parents[3] / "tools" / "cursor-runner" / "run.mjs"


def _node() -> str | None:
    return which("node")


def status() -> RunnerStatus:
    node = _node()
    script = _script_path()
    installed = bool(node) and script.exists()
    logged_in = False
    auth_label = "not installed"
    detail = ""
    if installed:
        # SDK package may be missing until npm install
        sdk_dir = script.parent / "node_modules" / "@cursor" / "sdk"
        if not sdk_dir.exists():
            auth_label = "sdk missing (npm install)"
            detail = str(script.parent)
        else:
            code, out, err = _probe([node, str(script), "status"])
            detail = (out or err)[:500]
            try:
                data = json.loads(out.strip().splitlines()[-1])
                if data.get("status") == "logged-in":
                    auth_label = data.get("email") or "logged in"
                    logged_in = True
                elif data.get("status") == "logged-out":
                    auth_label = "logged out"
                    logged_in = False
                else:
                    auth_label = data.get("error") or "unknown"
                    logged_in = False
            except Exception:  # noqa: BLE001
                auth_label = "status parse error"
    return RunnerStatus(
        id=RunnerId.cursor,
        name=NAME,
        binary=str(script) if installed else None,
        installed=installed and (script.parent / "node_modules" / "@cursor" / "sdk").exists(),
        logged_in=logged_in,
        auth_label=auth_label,
        login_command="node tools/cursor-runner/run.mjs login",
        run_command_hint="node tools/cursor-runner/run.mjs run --cwd <dir> --prompt ...",
        notes="Официальный @cursor/sdk: браузерный login минтит user key. Это агент Cursor, не raw LLM proxy.",
        detail=detail,
    )


async def login() -> RunnerLoginResult:
    node = _node()
    script = _script_path()
    if not node or not script.exists():
        return RunnerLoginResult(ok=False, runner=RunnerId.cursor, message="cursor-runner не найден")
    cmd = [node, str(script), "login"]
    code, out, err = await run_cmd(cmd, timeout_s=300.0, env=clean_env(), cwd=script.parent)
    text = (out or err).strip()
    ok = code == 0 and ("\"ok\": true" in text.replace(" ", "") or '"phase":"done"' in text.replace(" ", ""))
    # soft parse
    try:
        for line in reversed(text.splitlines()):
            if line.strip().startswith("{"):
                data = json.loads(line)
                ok = bool(data.get("ok"))
                text = json.dumps(data, ensure_ascii=False)
                break
    except Exception:  # noqa: BLE001
        pass
    return RunnerLoginResult(
        ok=ok,
        runner=RunnerId.cursor,
        message=text[:800] or f"exit {code}",
        opened_browser_flow=True,
        command=cmd,
    )


async def run(prompt: str, workdir: Path, *, timeout_s: float = 600.0) -> RunnerExecResult:
    node = _node()
    script = _script_path()
    if not node or not script.exists():
        return RunnerExecResult(ok=False, runner=RunnerId.cursor, summary="cursor-runner не установлен")

    workdir.mkdir(parents=True, exist_ok=True)
    before = snapshot_files(workdir)
    cmd = [node, str(script), "run", "--cwd", str(workdir), "--prompt", "-"]
    code, out, err = await run_cmd(
        cmd,
        cwd=script.parent,
        timeout_s=timeout_s,
        env=clean_env(),
        input_text=prompt,
    )
    after = snapshot_files(workdir)
    files = changed_files(before, after)
    summary = ""
    try:
        for line in reversed(out.splitlines()):
            if line.strip().startswith("{"):
                data = json.loads(line)
                summary = str(data.get("summary") or data.get("error") or "")
                break
    except Exception:  # noqa: BLE001
        summary = out[-2000:]
    return RunnerExecResult(
        ok=code == 0,
        runner=RunnerId.cursor,
        summary=(summary or err or out)[:8000],
        stdout=out[-12000:],
        stderr=err[-4000:],
        exit_code=code,
        files_written=files,
        raw_payload={"command": cmd[:-1] + ["--prompt", "<stdin>"]},
    )


def _probe(cmd: list[str]) -> tuple[int, str, str]:
    import subprocess

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=clean_env(),
            cwd=str(_script_path().parent),
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)
