Раф
ruff check backend --fix
ruff format backend
ruff check backend
pytest


Запуск апи
python -m uvicorn app.main:app --reload --app-dir backend

Алембик
alembic history
alembic history --verbose

Посмотреть текущую применённую миграцию в БД (запустить бд вначале)
alembic current

Посмотреть последнюю доступную миграцию в коде
alembic heads


Применить все миграции до последней
alembic upgrade head

Откатить последнюю миграцию
alembic downgrade -1

Применить конкретную миграцию
alembic upgrade 20260428_0001

Проверить SQL, который будет выполнен, без применения
alembic upgrade head --sql

Сохранить в файл:
alembic upgrade head --sql > migration.sql

ДОКЕР:
запуск бд
docker compose -f infra/compose.local.yml up -d postgres
проверка
docker compose -f infra/compose.local.yml ps

alembic upgrade head
alembic current

остановить бд
docker compose -f infra/compose.local.yml down

удалить локальную бд и стоп:
docker compose -f infra/compose.local.yml down -v

Пользователь
  ↓
https://psihologpashkov.ru
  └─ текущий статический сайт на Hoster.ru
  └─ /lk/ — новый статический личный кабинет

https://api.psihologpashkov.ru
  ↓
Caddy/Nginx + TLS
  ↓
FastAPI
  ↓
PostgreSQL

backend/
  app/
    api/v1/
      auth.py
      users.py
      cabinet.py
      health.py
    core/
      config.py
      security.py
      jwt.py
    db/
      session.py
      models.py
      migrations/
    services/
      auth_service.py
      user_service.py
    schemas/
      auth.py
      user.py
  tests/
  Dockerfile
  docker-compose.yml