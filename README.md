Раф
ruff check backend --fix
ruff format backend
ruff check backend
pytest




## Локальный запуск

ssh -i /home/alex/Downloads/id_rsa user1@89.232.176.127

Быстрый безопасный сброс локального окружения

Локальные данные удалятся, но это dev-среда:

cd ~/PycharmProjects/MySiteAuthhor/psihologpashkov-backend

docker compose -f infra/compose.full.local.yml down -v --remove-orphans
docker rm -f psihologpashkov-postgres-full-local psihologpashkov-api-local 2>/dev/null || true
docker volume prune -f

docker compose -f infra/compose.full.local.yml up -d postgres
docker compose -f infra/compose.full.local.yml logs -f postgres

Когда в логах будет что-то вроде:

database system is ready to accept connections

останови просмотр Ctrl+C и запусти API:

docker compose -f infra/compose.full.local.yml up -d api
docker compose -f infra/compose.full.local.yml exec api alembic upgrade head
curl -i http://127.0.0.1:8000/api/v1/healthz
Если Postgres всё равно unhealthy

Проверь, не занят ли порт 5432 локальным Postgres:

sudo ss -ltnp | grep ':5432'

Если занят, в файле:

infra/compose.full.local.yml

замени у postgres:

ports:
  - "5432:5432"

на:

ports:
  - "5433:5432"

Внутри Docker-сети API всё равно ходит на:

postgres:5432

поэтому DATABASE_URL менять не надо.

Потом:

docker compose -f infra/compose.full.local.yml down -v --remove-orphans
docker compose -f infra/compose.full.local.yml up -d --build
docker compose -f infra/compose.full.local.yml exec api alembic upgrade head

```bash
cd psihologpashkov-backend
source ../.venv/bin/activate

make install
make check
make run

http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/healthz

Docker local stack
make docker-up
docker compose -f infra/compose.full.local.yml exec api alembic upgrade head
curl -i http://127.0.0.1:8000/api/v1/healthz

играции

История:

alembic history

Создать миграцию:

alembic revision --autogenerate -m "migration name"

Применить:

alembic upgrade head

Откатить последнюю:

alembic downgrade -1
Проверки
make format
make check

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