# ShipCrew

ИИ-команда доводит задачу до prod-ready бандла: PM → Architect → Engineer → Reviewer → DevOps.

## Возможности

- Миссии с историей, отменой и удалением
- Лента агентов + просмотр артефактов
- Скачивание ship-бандла (`bundle.zip`)
- OpenRouter OAuth (браузер) и API-ключи
- Подписки через официальные CLI/SDK: Codex, Claude Code, Cursor Agent
- Demo mode без ключей для локальной проверки пайплайна

## Быстрый старт (Windows)

```powershell
.\scripts\dev.ps1
```

Или вручную:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

```bash
cd frontend
npm install
npm run dev
```

- UI: http://127.0.0.1:5173  
- API: http://127.0.0.1:8787/api/health  

## Подключения

1. Вкладка **Подключения** → OpenRouter (браузер) или API-ключ.
2. Для подписок: установи `codex` / `claude`, для Cursor — `cd tools/cursor-runner && npm install`, затем **Войти**.
3. В миссии выбери Engineer/Reviewer: `LLM` | `Codex` | `Claude` | `Cursor`.

Claude Code / Claude.ai subscription OAuth в сторонние приложения Anthropic запрещает. ShipCrew запускает официальный `claude` CLI или идёт через OpenRouter/API key.

## Env

Скопируй `.env.example` → `backend/.env` или корень:

| Переменная | Смысл |
|---|---|
| `SHIPCREW_DEMO_MODE` | `true` — демо без внешнего LLM |
| `SHIPCREW_LLM_*` | fallback OpenAI-compatible |
| `SHIPCREW_FRONTEND_URL` | куда вернуть после OAuth |
| `SHIPCREW_PUBLIC_BASE_URL` | callback origin бэкенда |

## Проверки

```bash
cd backend
pytest -q
```

```bash
cd frontend
npm run build
```

## Автор

Богдан Щербинин ([blessed-bless](https://github.com/blessed-bless))
