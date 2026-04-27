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