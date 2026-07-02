# InvoiceForge — генератор счетов и КП

Готовый к продаже продукт: веб‑приложение для выставления **счетов** и
**коммерческих предложений (КП)**, ведения клиентов и экспорта в **PDF**.
Работает локально (десктоп‑лицензия) или в облаке (SaaS). Без платных API.

- Технологии: Python + FastAPI + SQLite (файл, без отдельной БД)
- PDF: печать браузера → «Сохранить как PDF» (идеальная кириллица, любой ОС)
- Защита: лицензии на подписи **Ed25519** (см. раздел «Защита»)
- Языки интерфейса: RU / UK / EN

---

## Быстрый старт за 10–15 минут (локально)

### Требуется
- Python 3.10+ (скачать: python.org)

### Windows
1. Распакуйте папку `invoiceforge`.
2. Дважды кликните `run.bat`.
3. Откройте в браузере: `http://127.0.0.1:8000`
4. Пароль по умолчанию: `admin`

### Linux / macOS
```bash
cd invoiceforge
bash run.sh
# затем откройте http://127.0.0.1:8000
```

### Вручную (любая ОС)
```bash
cd invoiceforge
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Первый вход:
1. Пароль — `admin` (меняется в файле `.env`, см. `.env.example`).
2. Зайдите в **Настройки** → впишите свою компанию, реквизиты, валюту.
3. Добавьте клиента → создайте счёт → нажмите **Печать / PDF**.

---

## Запуск в облаке (SaaS)

Подходит любой хостинг с Python (Railway, Render, VPS).

### Вариант A: Render / Railway
- Repo → New Web Service
- Build command: `pip install -r invoiceforge/requirements.txt`
- Start command:
  `cd invoiceforge && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Переменные окружения: `INVOICEFORGE_PASSWORD`, `INVOICEFORGE_SECRET`

### Вариант B: свой VPS (Ubuntu)
```bash
sudo apt update && sudo apt install -y python3-venv
cd invoiceforge && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# запуск через systemd/pm2/screen:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Поставьте перед ним Nginx + HTTPS (Let's Encrypt) для домена.

---

## Настройка (файл `.env`)
Скопируйте `.env.example` → `.env` и задайте:
```
INVOICEFORGE_PASSWORD=ваш_пароль
INVOICEFORGE_SECRET=длинная_случайная_строка
INVOICEFORGE_PORT=8000
```

---

## Демо‑режим vs PRO
Без лицензии приложение работает в **ДЕМО**:
- до 3 клиентов и 5 документов;
- на PDF — водяной знак `DEMO`.

После активации лицензии ограничения снимаются.

---

## Защита от бесплатного распространения (кратко)
Лицензии подписываются приватным ключом (Ed25519), а приложение проверяет
подпись публичным ключом. Подделать ключ без вашего приватного ключа
невозможно. Подробнее и как выпускать ключи — в `SELLING.md`.

## Продажа, цены, тексты
См. `SELLING.md`: продающий текст, схемы монетизации (разовая покупка и
подписка) и полная инструкция по защите.
