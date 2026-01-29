# AI Chatbot

Сервер с AI-агентом в виде чата, встраиваемый в HTML через iframe. Реализация по [04-execution-spec.md](aichatbot_prompt/04-execution-spec.md).

- **Стек:** Python 3.11+, FastAPI, PostgreSQL, Docker/docker-compose, LLM DeepSeek (HTTP API).
- **API:** POST `/api/chat` (JSON: `user_id`, `message`, опционально `dialog_id`) → ответ SSE со стримом ответа LLM.
- **Конфигурация:** только из `.env` (см. `.env.example`). Промпт LLM — из файла (путь в `PROMPT_FILE_PATH`).

## Быстрый старт

1. Скопировать `.env.example` в `.env` и задать переменные (в т.ч. `LLM_API_KEY`, параметры PostgreSQL).
2. Запуск через Docker Compose:
   ```bash
   docker-compose up --build
   ```
   Приложение: http://localhost:8000  
   Страница чата для iframe: http://localhost:8000/static/index.html (или http://localhost:8000/ с редиректом).

3. Локально (без Docker):
   ```bash
   pip install -r requirements.txt
   # PostgreSQL должен быть запущен, переменные в .env
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

## Тесты

```bash
pip install -r requirements.txt
pytest tests -v
```

## Структура

- `app/` — FastAPI-приложение, маршруты, БД, клиент LLM.
- `prompts/system.txt` — системный промпт (путь настраивается в `.env`).
- `static/index.html` — страница чата для встраивания в iframe (форма + приём SSE).
- `alembic/` — миграции БД.
