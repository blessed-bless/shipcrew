from __future__ import annotations

import json
from pathlib import Path

from .process import changed_files, clean_env, run_cmd, snapshot_files, which
from .types import RunnerExecResult, RunnerId, RunnerLoginResult, RunnerStatus

NAME = "Claude Code (subscription)"


def status() -> RunnerStatus:
    binary = which("claude")
    logged_in = False
    auth_label = "not installed"
    detail = ""
    if binary:
        code, out, err = _probe([binary, "auth", "status"])
        text = f"{out}\n{err}".strip()
        detail = text[:500]
        try:
            data = json.loads(out.strip() or err.strip() or "{}")
            logged_in = bool(data.get("loggedIn"))
            method = data.get("authMethod") or "none"
            auth_label = str(method) if logged_in else "logged out"
        except json.JSONDecodeError:
            lower = text.lower()
            logged_in = "logged in" in lower or '"loggedin": true' in lower.replace(" ", "")
            auth_label = "logged in" if logged_in else "logged out"
    return RunnerStatus(
        id=RunnerId.claude,
        name=NAME,
        binary=binary,
        installed=bool(binary),
        logged_in=logged_in,
        auth_label=auth_label,
        login_command="claude auth login",
        run_command_hint="claude -p --output-format json ...",
        notes=(
            "Запускаем официальный `claude` CLI. Не копируем OAuth из ~/.claude в HTTP API. "
            "Логин — через собственный браузерный flow Anthropic."
        ),
        detail=detail,
    )


async def login() -> RunnerLoginResult:
    binary = which("claude")
    if not binary:
        return RunnerLoginResult(
            ok=False, runner=RunnerId.claude, message="claude не найден в PATH"
        )
    # Prefer auth login; fall back to /login-style if the CLI differs.
    for cmd in ([binary, "auth", "login"], [binary, "login"]):
        code, out, err = await run_cmd(cmd, timeout_s=300.0, env=clean_env())
        text = f"{out}\n{err}".strip()
        if code == 0 or "logged" in text.lower():
            return RunnerLoginResult(
                ok=True,
                runner=RunnerId.claude,
                message=text[:800] or "login ok",
                opened_browser_flow=True,
                command=cmd,
            )
        last = (text, cmd, code)
    text, cmd, code = last
    return RunnerLoginResult(
        ok=False,
        runner=RunnerId.claude,
        message=text[:800] or f"login failed ({code})",
        opened_browser_flow=True,
        command=cmd,
    )


async def run(prompt: str, workdir: Path, *, timeout_s: float = 600.0) -> RunnerExecResult:
    binary = which("claude")
    if not binary:
        return RunnerExecResult(ok=False, runner=RunnerId.claude, summary="claude не установлен")

    workdir.mkdir(parents=True, exist_ok=True)
    before = snapshot_files(workdir)
    cmd = [
        binary,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--add-dir",
        str(workdir),
    ]
    code, out, err = await run_cmd(cmd, cwd=workdir, timeout_s=timeout_s, env=clean_env())
    after = snapshot_files(workdir)
    files = changed_files(before, after)
    summary = _extract_text(out) or (out or err)[-2000:]
    return RunnerExecResult(
        ok=code == 0,
        runner=RunnerId.claude,
        summary=summary[:8000],
        stdout=out[-12000:],
        stderr=err[-4000:],
        exit_code=code,
        files_written=files,
        raw_payload={"command": cmd},
    )


def _extract_text(blob: str) -> str:
    blob = blob.strip()
    if not blob:
        return ""
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        # sometimes JSONL
        for line in reversed(blob.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
        else:
            return blob[-2000:]
    if isinstance(data, dict):
        for key in ("result", "text", "content", "message"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return json.dumps(data, ensure_ascii=False)[:2000]
    return str(data)[:2000]


def _probe(cmd: list[str]) -> tuple[int, str, str]:
    import subprocess

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20, env=clean_env(), check=False
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)
