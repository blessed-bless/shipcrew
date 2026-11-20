from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import Settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        force_live: bool = False,
    ) -> None:
        self.settings = settings
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.provider = provider or "openai"
        self.force_live = force_live

    @property
    def demo(self) -> bool:
        if self.force_live and self.api_key:
            return False
        return self.settings.demo_mode and not self.api_key

    async def complete(self, system: str, user: str, *, role_name: str = "agent") -> str:
        if self.demo:
            return self._demo_reply(role_name, user)
        if not self.api_key and self.provider != "ollama":
            raise LLMError(
                "Нет активного подключения к модели. Войди через браузер или добавь API-ключ."
            )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Anthropic Messages API shape differs; OpenRouter/OpenAI-compatible path covers most.
        if self.provider == "anthropic" and "anthropic.com" in self.base_url:
            return await self._complete_anthropic(system, user, headers)

        body = {
            "model": self.model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/blessed-bless/shipcrew"
            headers["X-Title"] = "ShipCrew"

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_s) as client:
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001 — surface provider failures as LLMError
            raise LLMError(f"LLM request failed: {exc}") from exc

    async def _complete_anthropic(self, system: str, user: str, headers: dict[str, str]) -> str:
        headers = {
            **headers,
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        headers.pop("Authorization", None)
        body = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        url = f"{self.base_url.rstrip('/')}/messages"
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_s) as client:
                resp = await client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                parts = data.get("content") or []
                texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
                text = "".join(texts).strip()
                if not text:
                    raise LLMError("Anthropic вернул пустой ответ")
                return text
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Anthropic request failed: {exc}") from exc

    def _demo_reply(self, role_name: str, user: str) -> str:
        goal = _extract(user, "GOAL") or "ship the requested product"
        title = _extract(user, "TITLE") or "Demo Mission"
        stack = _extract(user, "STACK") or "Python FastAPI + React"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "demo-app"

        if role_name == "pm":
            return json.dumps(
                {
                    "summary": f"Break down '{title}' into shippable milestones.",
                    "milestones": [
                        "Clarify MVP scope and acceptance checks",
                        "Define architecture and interfaces",
                        "Implement core backend and UI",
                        "Review, harden, package for prod",
                    ],
                    "acceptance": [
                        "API health endpoint responds",
                        "UI can create a mission and show agent feed",
                        "Ship bundle contains runnable artifacts",
                    ],
                    "risks": ["Unclear provider credentials", "Scope creep past MVP"],
                },
                ensure_ascii=False,
                indent=2,
            )

        if role_name == "architect":
            return json.dumps(
                {
                    "summary": f"Architecture for {title} on {stack}.",
                    "components": [
                        "API gateway / orchestrator",
                        "Agent workers with shared blackboard",
                        "Artifact store on disk",
                        "Web UI for mission control",
                    ],
                    "data_flow": "User goal → PM plan → Architect design → Engineer code → Reviewer gate → DevOps ship bundle",
                    "interfaces": {
                        "POST /missions": "create mission",
                        "POST /missions/{id}/run": "start crew",
                        "GET /missions/{id}": "status + messages + artifacts",
                    },
                    "files": [
                        f"apps/{slug}/README.md",
                        f"apps/{slug}/backend/main.py",
                        f"apps/{slug}/frontend/App.tsx",
                        f"apps/{slug}/docker-compose.yml",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )

        if role_name == "engineer":
            readme = (
                f"# {title}\n\nGoal: {goal}\n\nStack: {stack}\n\n"
                "## Run\n\n```bash\ndocker compose up --build\n```\n"
            )
            api = (
                "from fastapi import FastAPI\n\n"
                "app = FastAPI(title=__name__)\n\n"
                "@app.get('/health')\n"
                "def health():\n"
                "    return {'ok': True}\n"
            )
            ui = (
                "export default function App() {\n"
                "  return (\n"
                "    <main>\n"
                f"      <h1>{title}</h1>\n"
                "      <p>Crew-built MVP shell.</p>\n"
                "    </main>\n"
                "  );\n"
                "}\n"
            )
            return json.dumps(
                {
                    "summary": f"Implemented MVP skeleton for {title}.",
                    "files": {
                        f"apps/{slug}/README.md": readme,
                        f"apps/{slug}/backend/main.py": api,
                        f"apps/{slug}/frontend/App.tsx": ui,
                        f"apps/{slug}/requirements.txt": "fastapi\nuvicorn\n",
                    },
                    "notes": ["Keep scope to health API + shell UI for first ship."],
                },
                ensure_ascii=False,
                indent=2,
            )

        if role_name == "reviewer":
            return json.dumps(
                {
                    "summary": "Review pass completed.",
                    "approved": True,
                    "findings": [
                        {"severity": "low", "item": "Add auth before public expose"},
                        {"severity": "info", "item": "Document env vars in README"},
                    ],
                    "required_fixes": [],
                },
                ensure_ascii=False,
                indent=2,
            )

        if role_name == "devops":
            compose = (
                "services:\n"
                "  api:\n"
                "    image: python:3.12-slim\n"
                "    working_dir: /app\n"
                "    volumes:\n"
                "      - ./backend:/app\n"
                "    command: python -c \"print('shipcrew demo container ready')\"\n"
                "    ports:\n"
                "      - '8080:8080'\n"
            )
            dockerfile = (
                "FROM python:3.12-slim\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n"
                "COPY . .\n"
                'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]\n'
            )
            return json.dumps(
                {
                    "summary": f"Prepared production bundle for {title}.",
                    "files": {
                        f"apps/{slug}/docker-compose.yml": compose,
                        f"apps/{slug}/Dockerfile": dockerfile,
                        f"apps/{slug}/SHIP.md": (
                            f"# Ship checklist\n\n- [x] Artifacts written\n"
                            f"- [x] Compose present\n- [ ] Set real LLM keys\n"
                            f"- Goal: {goal}\n"
                        ),
                    },
                    "ship_notes": ["Bundle is ready for local prod-like run."],
                },
                ensure_ascii=False,
                indent=2,
            )

        return json.dumps(
            {"summary": f"{role_name} completed", "raw_goal": goal}, ensure_ascii=False
        )


def _extract(blob: str, key: str) -> str | None:
    m = re.search(rf"{key}:\s*(.+)", blob)
    return m.group(1).strip() if m else None


def parse_json_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"summary": text, "raw": text}
