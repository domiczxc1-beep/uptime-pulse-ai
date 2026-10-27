# 🚀 UptimePulse AI — Semantic Uptime & Business Logic Guardian

Классический мониторинг (Pingdom, UptimeRobot) проверяет только HTTP-код `200 OK`.
Но современный продакшн часто падает незаметно: база данных отвалилась, но фронтенд отдает `200` с текстом `Something went wrong`, либо сломался биллинг и корзина пустая.

**UptimePulse AI** отправляет запросы, парсит ответ и с помощью ультра-дешевой модели (`gpt-4o-mini`) проверяет **семантическую бизнес-логику**. При аномалиях отправляет мгновенный отчет в Telegram.

---

## 💰 Бизнес-модель (B2B Micro-SaaS)

- **Target Audience:** Indie-хакеры, E-commerce магазины (Shopify/WooCommerce), B2B SaaS.
- **Tier Free:** 3 эндпоинта, проверка раз в 15 минут.
- **Tier Pro ($19/мес):** 20 эндпоинтов, проверка каждую минуту, Telegram/Slack/Webhook оповещения, экспорт инцидентов.
- **Себестоимость:** Проверка через `gpt-4o-mini` стоит ~$0.00015 за запуск. При 100 проверках в сутки себестоимость AI-запросов на клиента < $0.50/мес.

---

## 🛠 Быстрый запуск

1. Клонируйте репозиторий и установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте переменные окружения:
```bash
cp .env.example .env
# Укажите OPENAI_API_KEY, TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
```

3. Запустите микросервис:
```bash
python main.py
```
Сервис доступен по адресу `http://localhost:8000`. Swagger-документация: `http://localhost:8000/docs`.

---

## 📡 API Endpoints
- `GET /` — Статус сервиса.
- `POST /targets` — Добавить новый монитор (URL + бизнес-условие на естественном языке).
- `POST /check-now/{target_id}` — Немедленная проверка эндпоинта вне очереди.
