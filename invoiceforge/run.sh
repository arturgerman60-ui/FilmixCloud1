#!/usr/bin/env bash
# Запуск InvoiceForge на Linux/macOS.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Создаю виртуальное окружение..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Устанавливаю зависимости..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

PORT="${INVOICEFORGE_PORT:-8000}"
echo "Запускаю InvoiceForge на http://127.0.0.1:${PORT}"
python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
