# Deployment Guide - Flower Market

## Сервер

| Параметр | Значение |
|----------|----------|
| **IP** | 158.160.217.236 |
| **Хостинг** | Yandex Cloud |
| **ОС** | Ubuntu 24.04 LTS |
| **Hostname** | wb-reputation-prod |

## SSH доступ

```bash
# Подключение к серверу
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236

# Ключ расположен в
~/.ssh/yandex-cloud-wb-reputation
```

## Проекты на сервере

На сервере развёрнуто **2 проекта**, они полностью изолированы:

| Проект | Путь | Порт | URL |
|--------|------|------|-----|
| **WB-Reputation** | /var/www/wb-reputation | 3000 (PM2) | http://158.160.217.236/ |
| **Flower Market** | /opt/flower-market | 8080 (systemd) | http://158.160.217.236/flower/ |

### Важно
- Проекты **НЕ влияют** друг на друга
- У каждого **своя база данных**
- Перезапуск одного **не затрагивает** другой

---

## Flower Market - Архитектура

```
/opt/flower-market/
├── apps/api/              # FastAPI backend
├── frontend/dist/         # Собранный React (Vite)
├── venv/                  # Python 3.12 виртуальное окружение
├── alembic/               # Миграции БД
├── packages/core/         # Бизнес-логика
├── .env                   # Конфигурация (НЕ в git!)
├── docker-compose.db.yml  # PostgreSQL контейнер
└── deploy.sh              # Скрипт деплоя
```

### Сервисы

| Сервис | Тип | Порт | Управление |
|--------|-----|------|------------|
| **API** | systemd | 8080 | `sudo systemctl {start|stop|restart} flower-api` |
| **PostgreSQL** | Docker | 5433 | `docker compose -f docker-compose.db.yml {up|down}` |
| **Nginx** | systemd | 80 | `sudo systemctl reload nginx` |

---

## Деплой / Обновление

### Автоматический деплой (РЕКОМЕНДУЕТСЯ)

**Одна команда для полного деплоя:**

```bash
# С локальной машины (Windows/Mac/Linux):
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236 "cd /opt/flower-market && ./deploy.sh"
```

**Полный процесс:**
```bash
# 1. Закоммитить и запушить изменения (локально)
git add <files>
git commit -m "feat(scope): description"
git push origin main

# 2. Деплой на сервер (одна команда!)
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236 "cd /opt/flower-market && ./deploy.sh"
```

Скрипт `deploy.sh` автоматически выполняет:
1. `git pull origin main` — получение последнего кода
2. `pip install -r requirements.txt` — установка Python зависимостей
3. `alembic upgrade head` — миграции БД
4. `npm run build` — сборка frontend с правильными путями
5. `systemctl restart flower-api` — перезапуск API
6. `nginx -t && systemctl reload nginx` — перезагрузка nginx

### Важные детали SSH подключения

| Параметр | Значение | Примечание |
|----------|----------|------------|
| **User** | `ubuntu` | ⚠️ НЕ root! |
| **Key** | `~/.ssh/yandex-cloud-wb-reputation` | Обязателен |
| **IP** | `158.160.217.236` | Yandex Cloud |
| **SCP Flag** | `-O` | Для Windows/старых клиентов |

⚠️ **Частые ошибки:**
- Использование `root@` вместо `ubuntu@` — доступ запрещён
- Забыли указать `-i ~/.ssh/...` — Permission denied
- SCP без `-O` флага — "message too long" на Windows

### Ручной деплой (только в крайних случаях)

Если git pull не работает, можно загрузить архив вручную:

```bash
# 1. Локально: создать архив (ВАЖНО: исключить лишнее!)
cd "c:\Users\79025\Desktop\проекты\Маркетплейс"
tar -czvf deploy.tar.gz apps packages infra frontend/dist --exclude='__pycache__' --exclude='*.pyc'

# 2. Загрузить на сервер (⚠️ флаг -O обязателен на Windows!)
scp -O -i ~/.ssh/yandex-cloud-wb-reputation deploy.tar.gz ubuntu@158.160.217.236:~/

# 3. На сервере: распаковать и перезапустить
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236 "
  sudo tar -xzf ~/deploy.tar.gz -C /opt/flower-market/
  sudo systemctl restart flower-api
  rm ~/deploy.tar.gz
"
```

**Когда использовать ручной деплой:**
- GitHub недоступен с сервера
- Нужно задеплоить незакоммиченные изменения
- Проблемы с git credentials

---

## Полезные команды

### Логи

```bash
# API логи (live)
sudo journalctl -u flower-api -f

# API логи (последние 100 строк)
sudo journalctl -u flower-api -n 100

# Nginx логи
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Статус сервисов

```bash
# API
sudo systemctl status flower-api

# PostgreSQL
sudo docker ps
sudo docker logs flower_postgres

# Nginx
sudo systemctl status nginx
```

### База данных

```bash
# Подключиться к PostgreSQL
sudo docker exec -it flower_postgres psql -U flower_user -d flower_market

# Проверить таблицы
\dt

# Выйти
\q
```

### Миграции

```bash
cd /opt/flower-market
source venv/bin/activate

# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Показать текущую версию
alembic current

# История миграций
alembic history
```

---

## Конфигурация

### .env (на сервере)

```bash
# Database
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=flower_market
DB_USER=flower_user
DB_PASSWORD=<generated>

# Application
APP_ENV=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8080

# JWT
JWT_SECRET_KEY=<generated>

# CORS
CORS_ORIGINS=http://158.160.217.236
```

### Nginx конфигурация

Файл: `/etc/nginx/sites-available/wb-reputation`

```nginx
# Flower Market блок
location /flower/api/ {
    proxy_pass http://127.0.0.1:8080/;
}

location /flower/assets/ {
    alias /opt/flower-market/frontend/dist/assets/;
    expires 1y;
}

location /flower/ {
    alias /opt/flower-market/frontend/dist/;
    try_files $uri $uri/ /flower/index.html;
}
```

---

## Troubleshooting

### SSH/SCP проблемы

**Permission denied (publickey)**
```bash
# Забыли указать ключ! Правильно:
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236
```

**Please login as user "NONE" rather than "root"**
```bash
# Yandex Cloud не разрешает root. Используйте ubuntu:
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236  # ✅
ssh -i ~/.ssh/yandex-cloud-wb-reputation root@158.160.217.236    # ❌
```

**SCP: Received message too long**
```bash
# На Windows добавьте флаг -O для legacy протокола:
scp -O -i ~/.ssh/yandex-cloud-wb-reputation file.tar.gz ubuntu@158.160.217.236:~/
```

**Could not open connection to authentication agent**
```bash
# SSH agent не запущен. Используйте -i напрямую:
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236
```

### API не запускается

```bash
# Проверить логи
sudo journalctl -u flower-api -n 50

# Частые проблемы:
# 1. Не установлен email-validator
pip install email-validator

# 2. Нет .env файла
cat /opt/flower-market/.env

# 3. PostgreSQL не запущен
sudo docker ps
sudo docker compose -f /opt/flower-market/docker-compose.db.yml up -d

# 4. AttributeError в моделях — проверить что код синхронизирован
cd /opt/flower-market && git status
```

### Frontend показывает 404

```bash
# Проверить, что dist существует
ls -la /opt/flower-market/frontend/dist/

# Пересобрать с правильным base path
cd /opt/flower-market/frontend
VITE_BASE_PATH=/flower/ VITE_API_BASE_URL=/flower/api npm run build
```

### 502 Bad Gateway

```bash
# API не запущен или упал
sudo systemctl status flower-api
sudo systemctl restart flower-api

# Проверить порт
curl http://127.0.0.1:8080/health
```

---

## URLs

| Ресурс | URL |
|--------|-----|
| **Frontend** | http://158.160.217.236/flower/ |
| **API** | http://158.160.217.236/flower/api/ |
| **API Docs (Swagger)** | http://158.160.217.236/flower/api/docs |
| **API Docs (ReDoc)** | http://158.160.217.236/flower/api/redoc |
| **Health Check** | http://158.160.217.236/flower/api/health |

---

## Контакты и ресурсы

- **Репозиторий**: (добавить ссылку на GitHub/GitLab)
- **Yandex Cloud Console**: https://console.yandex.cloud/
