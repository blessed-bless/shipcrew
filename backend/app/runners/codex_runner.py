from __future__ import annotations

import json
import re
from pathlib import Path

from .process import changed_files, clean_env, run_cmd, snapshot_files, which
from .types import RunnerExecResult, RunnerId, RunnerLoginResult, RunnerStatus


NAME = "Codex (ChatGPT subscription)"


def status() -> RunnerStatus:
    binary = which("codex")
    logged_in = False
    auth_label = "not installed"
    detail = ""
    if binary:
        # `codex login status` prints "Logged in using ChatGPT" (may exit non-zero on some builds)
        code, out, err = _sync_probe([binary, "login", "status"])
        text = f"{out}\n{err}"
        detail = text.strip()[:500]
        lower = text.lower()
        logged_in = "logged in" in lower and "not logged" not in lower
        if "chatgpt" in lower:
            auth_label = "ChatGPT subscription"
        elif "api key" in lower or "api-key" in lower:
            auth_label = "API key"
            logged_in = True
        elif logged_in:
            auth_label = "logged in"
        else:
            auth_label = "logged out"
    return RunnerStatus(
        id=RunnerId.codex,
        name=NAME,
        binary=binary,
        installed=bool(binary),
        logged_in=logged_in,
        auth_label=auth_label,
        login_command="codex login",
        run_command_hint="codex exec -C <workdir> --json ...",
        notes="Официальный CLI. Подписка ChatGPT через браузерный `codex login`. Не читаем auth.json вручную.",
        detail=detail,
    )


async def login() -> RunnerLoginResult:
    binary = which("codex")
    if not binary:
        return RunnerLoginResult(ok=False, runner=RunnerId.codex, message="codex не найден в PATH")
    # Браузерный OAuth; процесс сам откроет браузер и дождётся callback.
    code, out, err = await run_cmd([binary, "login"], timeout_s=300.0, env=clean_env())
    ok = code == 0 or "logged in" in f"{out}\n{err}".lower()
    return RunnerLoginResult(
        ok=ok,
        runner=RunnerId.codex,
        message=(out or err or "login finished").strip()[:800],
        opened_browser_flow=True,
        command=[binary, "login"],
    )


async def run(prompt: str, workdir: Path, *, timeout_s: float = 600.0) -> RunnerExecResult:
    binary = which("codex")
    if not binary:
        return RunnerExecResult(ok=False, runner=RunnerId.codex, summary="codex не установлен")

    workdir.mkdir(parents=True, exist_ok=True)
    last_msg = workdir / ".shipcrew_codex_last.txt"
    before = snapshot_files(workdir)
    cmd = [
        binary,
        "exec",
        "-C",
        str(workdir),
        "--json",
        "-o",
        str(last_msg),
        prompt,
    ]
    code, out, err = await run_cmd(cmd, cwd=workdir, timeout_s=timeout_s, env=clean_env())
    after = snapshot_files(workdir)
    files = [p for p in changed_files(before, after) if not p.startswith(".shipcrew_")]
    summary = ""
    if last_msg.exists():
        summary = last_msg.read_text(encoding="utf-8", errors="replace").strip()
    if not summary:
        summary = _last_assistant_from_jsonl(out) or (out or err)[-2000:]
    return RunnerExecResult(
        ok=code == 0,
        runner=RunnerId.codex,
        summary=summary[:8000],
        stdout=out[-12000:],
        stderr=err[-4000:],
        exit_code=code,
        files_written=files,
        raw_payload={"command": cmd},
    )


def _last_assistant_from_jsonl(blob: str) -> str:
    lines = [ln for ln in blob.splitlines() if ln.strip().startswith("{")]
    for line in reversed(lines[-50:]):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        for key in ("text", "message", "content", "last_agent_message"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        msg = data.get("msg") or data.get("item")
        if isinstance(msg, dict):
            for key in ("text", "content"):
                val = msg.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    # fallback: plain text chunk
    m = re.search(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', blob)
    return m.group(1).encode("utf-8").decode("unicode_escape") if m else ""


def _sync_probe(cmd: list[str]) -> tuple[int, str, str]:
    import subprocess

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            env=clean_env(),
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)
