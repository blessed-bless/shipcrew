from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import AgentRole


class RolePlaybook(BaseModel):
    role: AgentRole
    title: str
    mission: str
    checklist: list[str] = Field(default_factory=list)
    output_schema: dict[str, str] = Field(default_factory=dict)
    anti_patterns: list[str] = Field(default_factory=list)


class CrewTemplate(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    default_stack: str = "Python FastAPI + React"
    recommended_engineer: str = "llm"
    recommended_reviewer: str = "llm"
    playbooks: list[RolePlaybook]
    starter_goals: list[str] = Field(default_factory=list)


def _pb(
    role: AgentRole,
    title: str,
    mission: str,
    checklist: list[str],
    schema: dict[str, str],
    anti: list[str],
) -> RolePlaybook:
    return RolePlaybook(
        role=role,
        title=title,
        mission=mission,
        checklist=checklist,
        output_schema=schema,
        anti_patterns=anti,
    )


CREW_TEMPLATES: list[CrewTemplate] = [
    CrewTemplate(
        id="greenfield-saas",
        name="Greenfield SaaS MVP",
        description="С нуля собрать маленький SaaS: API, UI shell, docker, ship checklist.",
        tags=["saas", "mvp", "fastapi", "react"],
        recommended_engineer="codex",
        recommended_reviewer="claude",
        starter_goals=[
            "Сделать сервис заметок с аккаунтами и docker-compose",
            "Собрать биллинг-заглушку + кабинет пользователя",
            "API очередей задач с health и миграциями",
        ],
        playbooks=[
            _pb(
                AgentRole.pm,
                "Product Manager",
                "Вырежи MVP до одного пользовательского сценария и проверяемых acceptance.",
                [
                    "1 primary user journey",
                    "3–5 acceptance checks",
                    "явный non-goals список",
                ],
                {
                    "summary": "string",
                    "milestones": "string[]",
                    "acceptance": "string[]",
                    "risks": "string[]",
                },
                ["раздувать scope", "прятать open questions"],
            ),
            _pb(
                AgentRole.architect,
                "Architect",
                "Минимальная структура модулей и контракты API без overengineering.",
                ["границы сервисов", "схема данных", "список файлов"],
                {
                    "summary": "string",
                    "components": "string[]",
                    "data_flow": "string",
                    "interfaces": "object",
                    "files": "string[]",
                },
                ["микросервисы без нужды", "абстракции ради абстракций"],
            ),
            _pb(
                AgentRole.engineer,
                "Engineer",
                "Напиши рабочие файлы MVP в workdir.",
                ["runnable entrypoint", "README с запуском", "минимум зависимостей"],
                {"summary": "string", "files": "object", "notes": "string[]"},
                ["оставлять TODO-заглушки", "ломать существующие артефакты"],
            ),
            _pb(
                AgentRole.reviewer,
                "Reviewer",
                "Ищи ship-blockers, не стиль ради стиля.",
                ["security basics", "run path", "missing docs"],
                {
                    "summary": "string",
                    "approved": "bool",
                    "findings": "object[]",
                    "required_fixes": "string[]",
                },
                ["nitpicks без blocker-уровня"],
            ),
            _pb(
                AgentRole.devops,
                "DevOps",
                "Упакуй в docker-compose + SHIP checklist.",
                ["Dockerfile", "compose", "env example"],
                {"summary": "string", "files": "object", "ship_notes": "string[]"},
                ["хардкод секретов", "лишние privileged режимы"],
            ),
        ],
    ),
    CrewTemplate(
        id="bugfix-hardening",
        name="Bugfix & Hardening",
        description="Разобрать баг/регресс, закрыть фиксом, прогнать ревью и ship notes.",
        tags=["bugfix", "hardening", "qa"],
        recommended_engineer="claude",
        recommended_reviewer="codex",
        starter_goals=[
            "Починить падение /api/missions при пустом title",
            "Убрать race в оркестраторе при cancel",
            "Закрыть XSS в превью артефактов",
        ],
        playbooks=[
            _pb(
                AgentRole.pm,
                "Triage Lead",
                "Сформулируй баг как repro + impact + definition of done.",
                ["repro steps", "severity", "done criteria"],
                {
                    "summary": "string",
                    "milestones": "string[]",
                    "acceptance": "string[]",
                    "risks": "string[]",
                },
                ["чинить всё подряд"],
            ),
            _pb(
                AgentRole.architect,
                "Systems Analyst",
                "Найди вероятный слой поломки и безопасный фикс-контур.",
                ["affected modules", "regression risk"],
                {
                    "summary": "string",
                    "components": "string[]",
                    "data_flow": "string",
                    "interfaces": "object",
                    "files": "string[]",
                },
                ["большой рефакторинг в hotfix"],
            ),
            _pb(
                AgentRole.engineer,
                "Fix Engineer",
                "Внеси минимальный патч и тест.",
                ["failing test first if possible", "patch", "notes"],
                {"summary": "string", "files": "object", "notes": "string[]"},
                ["silent behavior changes"],
            ),
            _pb(
                AgentRole.reviewer,
                "QA Reviewer",
                "Проверь, что баг закрыт и не открыл соседний.",
                ["repro closed", "edge cases"],
                {
                    "summary": "string",
                    "approved": "bool",
                    "findings": "object[]",
                    "required_fixes": "string[]",
                },
                ["approve без проверки acceptance"],
            ),
            _pb(
                AgentRole.devops,
                "Release Owner",
                "Опиши rollout/rollback заметки.",
                ["ship notes", "smoke commands"],
                {"summary": "string", "files": "object", "ship_notes": "string[]"},
                ["пропускать rollback plan"],
            ),
        ],
    ),
    CrewTemplate(
        id="docs-portal",
        name="Docs & Developer Portal",
        description="Собрать документацию, onboarding и примеры API для репозитория.",
        tags=["docs", "dx", "portal"],
        recommended_engineer="llm",
        recommended_reviewer="llm",
        starter_goals=[
            "Сделать docs portal с quickstart и API reference",
            "Написать onboarding для новых контрибьюторов",
            "Собрать cookbook по runners и OAuth",
        ],
        playbooks=[
            _pb(
                AgentRole.pm,
                "Docs PM",
                "Выбери audience и 3 must-read страницы.",
                ["audience", "nav map", "success metric"],
                {
                    "summary": "string",
                    "milestones": "string[]",
                    "acceptance": "string[]",
                    "risks": "string[]",
                },
                ["писать энциклопедию"],
            ),
            _pb(
                AgentRole.architect,
                "IA Architect",
                "Структура docs/ и перекрёстные ссылки.",
                ["tree", "page contracts"],
                {
                    "summary": "string",
                    "components": "string[]",
                    "data_flow": "string",
                    "interfaces": "object",
                    "files": "string[]",
                },
                ["дублировать README везде"],
            ),
            _pb(
                AgentRole.engineer,
                "Technical Writer-Dev",
                "Напиши markdown/страницы и примеры команд.",
                ["quickstart", "api", "cookbook"],
                {"summary": "string", "files": "object", "notes": "string[]"},
                ["выдуманные флаги CLI"],
            ),
            _pb(
                AgentRole.reviewer,
                "Docs Reviewer",
                "Проверь runnable инструкции.",
                ["commands work", "no secret leaks"],
                {
                    "summary": "string",
                    "approved": "bool",
                    "findings": "object[]",
                    "required_fixes": "string[]",
                },
                ["LGTM без прогона команд"],
            ),
            _pb(
                AgentRole.devops,
                "Docs Publisher",
                "Добавь publish/preview скрипт или compose для docs.",
                ["preview command", "SHIP notes"],
                {"summary": "string", "files": "object", "ship_notes": "string[]"},
                ["ломать app compose ради docs"],
            ),
        ],
    ),
    CrewTemplate(
        id="agent-platform",
        name="Agent Platform Slice",
        description="Расширить оркестрацию: шаблоны команд, blackboard, метрики миссий.",
        tags=["agents", "platform", "orchestration"],
        recommended_engineer="cursor",
        recommended_reviewer="codex",
        starter_goals=[
            "Добавить mission metrics dashboard API",
            "Сделать template picker в UI",
            "Blackboard digest в каждый agent prompt",
        ],
        playbooks=[
            _pb(
                AgentRole.pm,
                "Platform PM",
                "Выбери один platform capability и acceptance.",
                ["capability", "API surface", "UI surface"],
                {
                    "summary": "string",
                    "milestones": "string[]",
                    "acceptance": "string[]",
                    "risks": "string[]",
                },
                ["строить всю платформу сразу"],
            ),
            _pb(
                AgentRole.architect,
                "Platform Architect",
                "Впиши capability в текущие модули ShipCrew.",
                ["module map", "compat"],
                {
                    "summary": "string",
                    "components": "string[]",
                    "data_flow": "string",
                    "interfaces": "object",
                    "files": "string[]",
                },
                ["ломать public API без миграции"],
            ),
            _pb(
                AgentRole.engineer,
                "Platform Engineer",
                "Реализуй backend+UI кусок.",
                ["tests", "types", "docs snippet"],
                {"summary": "string", "files": "object", "notes": "string[]"},
                ["god-objects в main.py"],
            ),
            _pb(
                AgentRole.reviewer,
                "Platform Reviewer",
                "Проверь изоляцию модулей и тесты.",
                ["unit coverage", "contract stability"],
                {
                    "summary": "string",
                    "approved": "bool",
                    "findings": "object[]",
                    "required_fixes": "string[]",
                },
                ["игнор regression на demo mode"],
            ),
            _pb(
                AgentRole.devops,
                "Platform Ops",
                "Обнови compose/CI под новый кусок.",
                ["ci job", "health check"],
                {"summary": "string", "files": "object", "ship_notes": "string[]"},
                ["хрупкие sleep в CI"],
            ),
        ],
    ),
]


def get_template(template_id: str) -> CrewTemplate | None:
    for item in CREW_TEMPLATES:
        if item.id == template_id:
            return item
    return None


def list_templates() -> list[CrewTemplate]:
    return list(CREW_TEMPLATES)


def playbook_for(template_id: str | None, role: AgentRole) -> RolePlaybook | None:
    template = get_template(template_id) if template_id else None
    if template is None:
        return None
    for pb in template.playbooks:
        if pb.role == role:
            return pb
    return None
