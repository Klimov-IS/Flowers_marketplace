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

### Автоматический деплой (рекомендуется)

```bash
# 1. Подключиться к серверу
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236

# 2. Запустить скрипт деплоя
cd /opt/flower-market
./deploy.sh
```

Скрипт выполнит:
- `git pull` (если есть .git)
- Установку Python зависимостей
- Миграции БД (`alembic upgrade head`)
- Сборку frontend (`npm run build`)
- Перезапуск API сервиса
- Reload nginx

### Ручной деплой

```bash
# 1. Локально: создать архив
cd ~/Desktop/проекты/Маркетплейс
tar --exclude='venv' --exclude='node_modules' --exclude='.git' \
    --exclude='__pycache__' --exclude='frontend/dist' \
    -czvf /tmp/flower-market.tar.gz .

# 2. Загрузить на сервер
scp -i ~/.ssh/yandex-cloud-wb-reputation \
    /tmp/flower-market.tar.gz \
    ubuntu@158.160.217.236:/opt/flower-market/

# 3. На сервере: распаковать и развернуть
ssh -i ~/.ssh/yandex-cloud-wb-reputation ubuntu@158.160.217.236
cd /opt/flower-market

# Сохранить конфиги
cp .env .env.bak
cp docker-compose.db.yml docker-compose.db.yml.bak

# Распаковать
tar -xzf flower-market.tar.gz
rm flower-market.tar.gz

# Восстановить конфиги
mv .env.bak .env
mv docker-compose.db.yml.bak docker-compose.db.yml

# Установить зависимости
source venv/bin/activate
pip install -r requirements.txt

# Миграции
alembic upgrade head

# Собрать frontend
cd frontend
npm ci
VITE_BASE_PATH=/flower/ VITE_API_BASE_URL=/flower/api npm run build
cd ..

# Перезапустить сервисы
sudo systemctl restart flower-api
sudo systemctl reload nginx
```

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
