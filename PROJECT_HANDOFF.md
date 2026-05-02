# Psiholog Pashkov Backend — handoff / продолжение работы

Дата фиксации состояния: 2026-05-01

Этот файл нужен, чтобы в новой сессии быстро продолжить работу над проектом без восстановления контекста из переписки.

смт
SMTP_HOST=mail-eu.smtp2go.com
SMTP_PORT=587
SMTP_USERNAME=doppsy.ru
SMTP_PASSWORD=EDKPVZeOzWFgSnIW
SMTP_FROM_EMAIL=admin@doppsy.ru
SMTP_FROM_NAME=Psiholog Pashkov
SMTP_USE_TLS=true
SMTP_USE_SSL=false

---

## 1. Краткое состояние проекта

Проект: backend и личный кабинет для статического сайта `psihologpashkov.ru`.

Основная идея:

- основной сайт остаётся на старом статическом хостинге;
- SEO-страницы не переносим;
- backend живёт отдельно на поддомене `api.psihologpashkov.ru`;
- личный кабинет `/lk/` — статический frontend, который ходит в API.

Текущий статус:

- FastAPI backend создан.
- Postgres подключён.
- JWT access/refresh авторизация работает.
- Refresh token работает через HttpOnly cookie.
- Личный кабинет работает на `/lk/`.
- Регистрация пользователя в production работает.
- Профиль, смена пароля, аватарки реализованы.
- HTTPS API работает.
- GitHub Actions автодеплой на VM работает, но SSH-соединение к VM иногда нестабильно.
- Cron backup на VM настроен.
- Backup Postgres и uploads вручную проверен.

---

## 2. Репозиторий и локальные пути

GitHub:

```text
https://github.com/pashkov-debug/MySiteAuthhor

Локальный проект:

/home/alex/PycharmProjects/MySiteAuthhor

Backend:

/home/alex/PycharmProjects/MySiteAuthhor/psihologpashkov-backend

SSH-ключ для VM на локальной машине:

/home/alex/Downloads/id_rsa

Важно: приватный ключ не отправлять в чат, не коммитить, не вставлять в файлы проекта.

3. Production VM

Провайдер: Cloud.ru.

VM:

IP: 89.232.176.127
User: user1
SSH: ssh -i /home/alex/Downloads/id_rsa user1@89.232.176.127

Проект на VM:

/opt/MySiteAuthhor

Backend на VM:

/opt/MySiteAuthhor/psihologpashkov-backend

Production secrets:

/opt/MySiteAuthhor/psihologpashkov-backend/.env.prod

Сертификаты Caddy:

/opt/psihologpashkov-certs/fullchain.pem
/opt/psihologpashkov-certs/privkey.pem

Backups:

/opt/psihologpashkov-backups/postgres
/opt/psihologpashkov-backups/uploads
/opt/psihologpashkov-backups/backup.log
4. DNS

Основной сайт:

psihologpashkov.ru → 31.28.24.244

API:

api.psihologpashkov.ru → 89.232.176.127

Важно: не менять A-запись корневого домена и www, чтобы не сломать основной сайт.

5. Production API

Base URL:

https://api.psihologpashkov.ru/api/v1

Healthcheck:

curl --noproxy '*' -i https://api.psihologpashkov.ru/api/v1/healthz

Ожидаемый ответ:

{"status":"ok"}
6. Docker stack на VM

Production compose:

/opt/MySiteAuthhor/psihologpashkov-backend/infra/compose.prod.yml

Сервисы:

postgres
api
caddy

Проверка:

cd /opt/MySiteAuthhor/psihologpashkov-backend
docker compose --env-file .env.prod -f infra/compose.prod.yml ps

Ожидаемо:

postgres   Up / healthy
api        Up / healthy
caddy      Up

Перезапуск без удаления данных:

docker compose --env-file .env.prod -f infra/compose.prod.yml up -d --no-build

Применение миграций:

docker compose --env-file .env.prod -f infra/compose.prod.yml exec -T api alembic upgrade head

Категорически нельзя на production без полного понимания:

docker compose down -v

Это удалит production volumes: БД и uploads.

7. HTTPS и сертификат

Автоматический выпуск сертификата через Caddy/Let’s Encrypt был нестабилен из-за сетевых проблем VM.

Текущая схема:

сертификат был выпущен вручную через DNS-01 challenge certbot;
Caddy использует готовые файлы сертификата с диска.

Caddyfile должен использовать:

tls /etc/caddy/certs/fullchain.pem /etc/caddy/certs/privkey.pem

Volume сертификатов в compose.prod.yml:

- /opt/psihologpashkov-certs:/etc/caddy/certs:ro

Риск: сертификат нужно будет обновлять вручную примерно через 60–80 дней, если не автоматизировать DNS-01.

8. GitHub Actions / автодеплой

Workflow:

.github/workflows/deploy.yml

Текущая схема деплоя:

push в master
  → GitHub Actions
  → docker build API image
  → docker save api-image.tar.gz
  → tar app.tar.gz
  → SSH/SCP на VM
  → docker load на VM
  → rsync проекта в /opt/MySiteAuthhor
  → docker compose up -d --no-build
  → alembic upgrade head
  → healthcheck

Secrets в GitHub repository MySiteAuthhor:

DEPLOY_HOST=89.232.176.127
DEPLOY_USER=user1
DEPLOY_PORT=22
DEPLOY_SSH_KEY=<полный приватный ключ>

Важно: secrets должны быть именно в репозитории:

pashkov-debug/MySiteAuthhor

Не в другом репозитории.

Известная проблема:

SSH/SCP из GitHub Actions к VM иногда падает по timeout;
обычно помогает Re-run jobs;
аналогичные timeout иногда бывают даже при локальном SSH к VM, значит проблема похожа на нестабильное соединение Cloud.ru/VM.

Пока решили:

workflow не переделывать на self-hosted runner;
при редком падении нажимать Re-run jobs;
если timeout станет постоянным — рассмотреть self-hosted runner или смену VM/провайдера.
9. Личный кабинет frontend

Папка:

psihologpashkov-backend/frontend-lk

Структура:

frontend-lk/
  index.html
  assets/
    config.js
    app.js
    styles.css

Production config:

window.LK_CONFIG = {
  API_BASE_URL: "https://api.psihologpashkov.ru/api/v1"
};

На сайте должно быть:

https://psihologpashkov.ru/lk/

Файлы на хостинге:

/lk/index.html
/lk/assets/config.js
/lk/assets/app.js
/lk/assets/styles.css

Если кабинет пишет:

Неожиданная ошибка. Проверьте подключение к API.

Проверить:

curl -s https://psihologpashkov.ru/lk/assets/config.js
curl --noproxy '*' -i https://api.psihologpashkov.ru/api/v1/healthz

Также проверить CORS в .env.prod:

CORS_ORIGINS=https://psihologpashkov.ru,https://www.psihologpashkov.ru
10. Реализованный backend-функционал

Основные endpoints:

GET    /api/v1/healthz

POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

GET    /api/v1/me
PATCH  /api/v1/me
PATCH  /api/v1/me/password

PATCH  /api/v1/me/avatar
DELETE /api/v1/me/avatar

GET    /uploads/...

Auth:

access token короткоживущий;
refresh token хранится в БД как refresh session;
refresh token отдаётся в JSON и HttpOnly cookie;
при смене пароля refresh-сессии отзываются.

User profile:

email;
full_name;
avatar_path;
password change.

Avatars:

хранятся в uploads volume;
в БД хранится только avatar_path;
поддерживаемые расширения: .jpg, .jpeg, .png, .webp;
лимит размера из .env.prod.
11. Backup

На VM настроен cron backup.

Проверить cron:

crontab -l

Ожидаемая строка:

30 3 * * * cd /opt/MySiteAuthhor/psihologpashkov-backend && bash infra/scripts/backup_all.sh >> /opt/psihologpashkov-backups/backup.log 2>&1

Ручной запуск:

cd /opt/MySiteAuthhor/psihologpashkov-backend
bash infra/scripts/backup_all.sh

Проверить файлы:

ls -lah /opt/psihologpashkov-backups/postgres
ls -lah /opt/psihologpashkov-backups/uploads

Скрипты:

infra/scripts/backup_postgres.sh
infra/scripts/backup_uploads.sh
infra/scripts/backup_all.sh

Важно:

backups вынесены за пределы директории автодеплоя;
раньше backups лежали внутри psihologpashkov-backend/backups, так делать нельзя из-за rsync --delete;
следующий улучшенный шаг — скачивание backup на локальную машину или во внешнее хранилище.
12. Локальная разработка

Активировать venv:

cd ~/PycharmProjects/MySiteAuthhor/psihologpashkov-backend
source ../.venv/bin/activate

Проверки:

ruff check backend --fix
ruff format backend
ruff check backend
pytest

Локальный запуск backend:

python -m uvicorn app.main:app --reload --app-dir backend

Docker full local stack:

docker compose -f infra/compose.full.local.yml up -d --build
docker compose -f infra/compose.full.local.yml exec api alembic upgrade head

Smoke local:

make smoke-local

Smoke production:

API_BASE_URL=https://api.psihologpashkov.ru/api/v1 make smoke-prod
13. Опасные команды

Не выполнять на production:

docker compose down -v
docker volume prune -f
docker system prune -af

Без точного понимания последствий они могут удалить:

production-БД;
avatars/uploads;
Docker volumes;
важные данные.
14. Известные проблемы
14.1. Cloud.ru VM нестабильно ходит наружу

Были проблемы с доступом VM к:

GitHub
Docker Hub
Let’s Encrypt

Из-за этого:

git clone на VM падал timeout;
Docker image pull падал timeout;
Caddy не смог сам выпустить сертификат;
GitHub Actions SSH иногда падает timeout.

Текущие обходы:

VM не делает git pull;
GitHub Actions собирает Docker image и заливает его на VM;
сертификат выпущен вручную через DNS-01;
при редком SSH timeout в GitHub Actions используется Re-run jobs.
14.2. Сертификат ручной

Нужно не забыть обновить сертификат до истечения.

Варианты улучшения:

автоматизировать DNS-01;
подключить DNS provider API, если возможно;
сменить схему TLS;
перенести API на провайдера с более стабильной сетью.
14.3. Backup пока на той же VM

Cron backup есть, но если потерять всю VM, backup тоже потеряется.

Следующий шаг:

скачивание backup на локальную машину
или внешний storage
15. Следующие рекомендуемые задачи
Приоритет 1 — скачать backups локально

Сделать скрипт:

infra/scripts/download_backups_local.sh

Или локальную команду:

rsync -avz -e "ssh -i /home/alex/Downloads/id_rsa" \
  user1@89.232.176.127:/opt/psihologpashkov-backups/ \
  ~/Backups/psihologpashkov/
Приоритет 2 — проверить restore

Нужно не только создавать backup, но и проверить восстановление на локальной/тестовой БД.

Приоритет 3 — роли и статусы пользователей

План:

users.role:
  user
  client
  admin

users.status:
  pending
  active
  blocked

Правила:

backend — источник истины по правам;
frontend только скрывает/показывает UI;
закрытые endpoints обязательно защищаются backend dependency.

Пример будущих endpoints:

GET   /api/v1/admin/users
PATCH /api/v1/admin/users/{user_id}

Dependency:

require_active_user
require_admin
require_role(...)
Приоритет 4 — админка

Минимальная админка нужна, чтобы менять роль/status пользователей без ручного доступа к БД.

Приоритет 5 — hardening
rate limit auth endpoints;
CSRF strategy для cookie refresh;
security headers;
логирование ошибок;
мониторинг свободного места на диске;
алерты по истечению сертификата;
очистка старых refresh sessions.
16. Проверка текущего production-состояния

Локально:

curl --noproxy '*' -i https://api.psihologpashkov.ru/api/v1/healthz
curl -s https://psihologpashkov.ru/lk/assets/config.js

На VM:

ssh -i /home/alex/Downloads/id_rsa user1@89.232.176.127

cd /opt/MySiteAuthhor/psihologpashkov-backend
docker compose --env-file .env.prod -f infra/compose.prod.yml ps
crontab -l
ls -lah /opt/psihologpashkov-backups/postgres
ls -lah /opt/psihologpashkov-backups/uploads

17. Критерии текущей готовности проекта

Проект считается текущим MVP-ready, если:

https://api.psihologpashkov.ru/api/v1/healthz возвращает 200.
/lk/ открывается на основном сайте.
Регистрация пользователя работает.
Login/logout работает.
Профиль сохраняется.
Аватар загружается и удаляется.
GitHub Actions deploy проходит зелёным, возможно после Re-run jobs.
Backup Postgres и uploads создаётся по cron.
Production volumes не удалялись.
.env.prod, private key, certs не попали в Git.
18. Границы ответственности

Что уже есть:

backend;
auth;
profile;
avatar;
HTTPS;
deploy;
backups.

Что ещё не сделано:

роли/status;
админка;
restore-проверка;
автоматическое скачивание backup;
автоматическое обновление сертификата;
полноценный мониторинг;
оплата/подписки;
расширенные закрытые разделы сайта.
19. Главное правило проекта

Публичный сайт не переносим и не ломаем.

Backend и личный кабинет расширяем рядом:

psihologpashkov.ru          → публичный статический сайт
psihologpashkov.ru/lk/      → статический личный кабинет
api.psihologpashkov.ru      → backend API на VM

---

# B) Действия

```bash
cd ~/PycharmProjects/MySiteAuthhor

nano psihologpashkov-backend/PROJECT_HANDOFF.md

Вставь файл выше.

Потом:

git add psihologpashkov-backend/PROJECT_HANDOFF.md
git commit -m "docs: add project handoff notes"
git push origin master

После push автодеплой может запуститься, потому что меняется файл внутри psihologpashkov-backend/**. Это нормально. Если GitHub Actions поймает SSH timeout — просто Re-run jobs.

C) Пояснение

Это делается, чтобы в новой сессии можно было начать с фразы: “Вот PROJECT_HANDOFF.md, продолжим проект”.

Интеграция с другими направлениями
DevOps: зафиксированы VM, deploy, certs, backup.
Backend: описаны реализованные endpoints и следующие backend-задачи.
Frontend: описан /lk/ и production API config.
Data: описаны Postgres, uploads, backup и риски volumes.
Критерии готовности
PROJECT_HANDOFF.md создан.
Файл закоммичен.
Файл запушен в master.
В новой сессии по этому файлу можно продолжить работу без восстановления всей переписки.
D) Риски

⚠️ Не добавляй в этот файл реальные значения .env.prod, приватные ключи, JWT secrets, пароли БД или содержимое сертификатов.