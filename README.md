# ShipCrew

ИИ-команда, которой даёшь задачу — агенты работают между собой и доводят до prod-ready бандла.

Роли: **PM → Architect → Engineer → Reviewer → DevOps**.

## Что умеет

- Принимает бриф (название, цель, ограничения)
- Гоняет пайплайн агентов с общей доской сообщений
- Пишет артефакты на диск (`backend/data/artifacts/<mission_id>/`)
- Собирает docker/ship checklist на финальном шаге
- UI показывает ленту агентов и статус миссии
- Подключения к моделям: **браузерный OAuth (OpenRouter)** и обычные **API-ключи**

### Вход через браузер (не токен вручную)

Кнопка **«Войти через OpenRouter»** → редирект на openrouter.ai → разрешение ShipCrew → ключ привязан к твоему аккаунту/кредитам.

Claude / GPT и другие модели можно брать через этот аккаунт.  
**Вход через Claude Code / Claude.ai subscription OAuth в сторонние приложения Anthropic запрещает** — для прямого Claude нужен API-ключ из Console, либо те же модели через OpenRouter.

API-ключи при этом не убраны: OpenAI / Anthropic / Ollama добавляются вручную.

### Подписки Codex / Claude / Cursor (без API-ключа)

ShipCrew не тащит subscription OAuth в чужой HTTP API. Вместо этого запускает **официальные клиенты**:

| Runner | Логин | Как попадает в команду |
|---|---|---|
| Codex | `codex login` (ChatGPT) | Engineer/Reviewer backend = `codex` |
| Claude Code | `claude auth login` | backend = `claude` |
| Cursor Agent | `node tools/cursor-runner/run.mjs login` | backend = `cursor` |

```bash
# Cursor SDK bridge (один раз)
cd tools/cursor-runner
npm install
```

В UI: блок «Подписки через официальные CLI/SDK» + выбор Engineer/Reviewer backend в форме миссии.

## Запуск

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

В другом терминале:

```bash
cd frontend
npm install
npm run dev
```

UI: http://127.0.0.1:5173  
API: http://127.0.0.1:8787/api/health

## Env

Скопируй `.env.example` → `.env`:

- `SHIPCREW_DEMO_MODE=true` — без внешнего LLM
- `SHIPCREW_LLM_API_KEY` + `SHIPCREW_LLM_BASE_URL` + `SHIPCREW_LLM_MODEL` — живой OpenAI-совместимый провайдер

## Проверки

```bash
cd backend
pytest -q
```

## Автор

Богдан Щербинин ([blessed-bless](https://github.com/blessed-bless))
